from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import requests

from .errors import ManifestError, ShopifyError
from .io_utils import load_env, update_env_value
from .manifest import extract_asin


def gid(kind: str, identifier: str) -> str:
    return identifier if identifier.startswith("gid://") else f"gid://shopify/{kind}/{identifier}"


@dataclass
class ShopifyConfig:
    store: str
    token: str
    client_id: str
    client_secret: str
    api_version: str
    ready_timeout: int
    env_path: Path

    @classmethod
    def from_env(cls, path: Path) -> "ShopifyConfig":
        env = load_env(path)
        store = (env.get("SHOPIFY_STORE_DOMAIN") or env.get("SHOPIFY_SHOP") or "").strip()
        store = store.removeprefix("https://").removeprefix("http://").rstrip("/")
        if store and "." not in store:
            store += ".myshopify.com"
        token = env.get("STORE_ADMIN_ACCESS_TOKEN", "").strip()
        client_id = (env.get("STORE_ADMIN_CLIENT_ID") or env.get("SHOPIFY_CLIENT_ID") or "").strip()
        secret = (env.get("STORE_ADMIN_CLIENT_SECRET") or env.get("SHOPIFY_CLIENT_SECRET") or "").strip()
        if not store or not token:
            raise ShopifyError(f"Missing Shopify store/token in {path}.")
        return cls(store, token, client_id, secret, env.get("SHOPIFY_API_VERSION", "2026-01"),
                   int(env.get("SHOPIFY_FILE_READY_TIMEOUT_SECONDS", "180")), path)


class ShopifyClient:
    def __init__(self, config: ShopifyConfig, session: requests.Session | None = None):
        self.config = config
        self.session = session or requests.Session()
        self.endpoint = f"https://{config.store}/admin/api/{config.api_version}/graphql.json"

    def _refresh_token(self) -> None:
        if not self.config.client_id or not self.config.client_secret:
            raise ShopifyError("Shopify returned 401 and client credentials are unavailable for token refresh.")
        response = self.session.post(
            f"https://{self.config.store}/admin/oauth/access_token",
            json={"grant_type": "client_credentials", "client_id": self.config.client_id,
                  "client_secret": self.config.client_secret}, timeout=30,
        )
        if response.status_code >= 400:
            raise ShopifyError(f"Shopify token refresh failed with HTTP {response.status_code}.")
        token = str(response.json().get("access_token", "")).strip()
        if not token:
            raise ShopifyError("Shopify token refresh returned no access_token.")
        self.config.token = token
        update_env_value(self.config.env_path, "STORE_ADMIN_ACCESS_TOKEN", token)

    def graphql(self, query: str, variables: Mapping[str, Any] | None = None, *, refresh: bool = True) -> dict[str, Any]:
        response = self.session.post(self.endpoint, headers={"X-Shopify-Access-Token": self.config.token},
                                     json={"query": query, "variables": variables or {}}, timeout=60)
        if response.status_code == 401 and refresh:
            self._refresh_token()
            return self.graphql(query, variables, refresh=False)
        if response.status_code >= 400:
            raise ShopifyError(f"Shopify HTTP {response.status_code}: {response.text[:500]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ShopifyError("Shopify returned a non-JSON response.") from exc
        if payload.get("errors"):
            raise ShopifyError("Shopify GraphQL error: " + json.dumps(payload["errors"], ensure_ascii=False))
        if not isinstance(payload.get("data"), dict):
            raise ShopifyError("Shopify response has no data object.")
        return payload["data"]

    @staticmethod
    def _checked(data: dict[str, Any], field: str) -> dict[str, Any]:
        result = data.get(field) or {}
        errors = result.get("userErrors") or []
        if errors:
            raise ShopifyError(f"{field} failed: {json.dumps(errors, ensure_ascii=False)}")
        return result

    def snapshot_product(self, product_id: str) -> dict[str, Any]:
        query = """
        query Snapshot($id: ID!) {
          product(id: $id) {
            id title handle descriptionHtml status productType vendor tags seo { title description }
            options { id name position optionValues { id name } }
          }
        }"""
        product = self.graphql(query, {"id": gid("Product", product_id)}).get("product")
        if not product:
            raise ShopifyError(f"Shopify product {product_id} was not found.")
        product["variants"] = {"nodes": self._snapshot_connection(product_id, "variants", """
          id title price sku selectedOptions { name value } inventoryItem { id tracked }
        """)}
        product["media"] = {"nodes": self._snapshot_connection(product_id, "media", """
          id alt mediaContentType status ... on MediaImage { image { url } }
        """)}
        product["metafields"] = {"nodes": self._snapshot_connection(product_id, "metafields", """
          id namespace key type value
        """)}
        product["resourcePublicationsV2"] = {"nodes": self._snapshot_connection(product_id, "resourcePublicationsV2", """
          publication { id name } isPublished
        """)}
        return product

    def product_metafield_definitions(self) -> dict[tuple[str, str], str]:
        query = """query ProductMetafieldDefinitions {
          metafieldDefinitions(first: 250, ownerType: PRODUCT) {
            nodes { namespace key type { name } }
          }
        }"""
        nodes = ((self.graphql(query).get("metafieldDefinitions") or {}).get("nodes") or [])
        return {
            (str(item.get("namespace", "")), str(item.get("key", ""))):
                str((item.get("type") or {}).get("name", ""))
            for item in nodes
            if item.get("namespace") and item.get("key") and (item.get("type") or {}).get("name")
        }

    def products_by_amazon_asins(self, asins: set[str]) -> dict[str, list[dict[str, str]]]:
        """Return Shopify products whose custom.amazon_link contains a requested ASIN.

        The comparison intentionally uses the normalized ASIN rather than the full URL,
        so harmless Amazon query strings and path suffixes do not affect matching.
        """
        requested = {str(asin).strip().upper() for asin in asins if str(asin).strip()}
        matches: dict[str, list[dict[str, str]]] = {asin: [] for asin in requested}
        if not requested:
            return matches
        query = """
        query ProductsByAmazonLink($after: String) {
          products(first: 250, after: $after) {
            nodes {
              id title handle
              amazonLink: metafield(namespace: "custom", key: "amazon_link") { value }
            }
            pageInfo { hasNextPage endCursor }
          }
        }"""
        cursor: str | None = None
        while True:
            connection = self.graphql(query, {"after": cursor}).get("products") or {}
            for product in connection.get("nodes") or []:
                amazon_url = str((product.get("amazonLink") or {}).get("value") or "").strip()
                if not amazon_url:
                    continue
                try:
                    asin = extract_asin(amazon_url)
                except ManifestError:
                    # A malformed legacy metafield must not make the whole catalog
                    # preflight unusable; it simply cannot match a normalized ASIN.
                    continue
                if asin not in requested:
                    continue
                product_gid = str(product.get("id") or "")
                matches[asin].append({
                    "shopify_product_id": product_gid.rsplit("/", 1)[-1],
                    "title": str(product.get("title") or ""),
                    "handle": str(product.get("handle") or ""),
                    "amazon_url": amazon_url,
                })
            page_info = connection.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                return matches
            cursor = page_info.get("endCursor")
            if not cursor:
                raise ShopifyError("Shopify products pagination hasNextPage without an endCursor.")

    def _snapshot_connection(self, product_id: str, field: str, selection: str) -> list[dict[str, Any]]:
        if field not in {"variants", "media", "metafields", "resourcePublicationsV2"}:
            raise ValueError(f"Unsupported snapshot connection: {field}")
        query = f"""query SnapshotPage($id: ID!, $after: String) {{
          product(id: $id) {{ {field}(first: 250, after: $after) {{
            nodes {{ {selection} }} pageInfo {{ hasNextPage endCursor }}
          }} }}
        }}"""
        nodes: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            product = self.graphql(query, {"id": gid("Product", product_id), "after": cursor}).get("product") or {}
            connection = product.get(field) or {}
            nodes.extend(connection.get("nodes") or [])
            page_info = connection.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                return nodes
            cursor = page_info.get("endCursor")
            if not cursor:
                raise ShopifyError(f"Shopify {field} pagination hasNextPage without an endCursor.")

    def stage_image(self, content: bytes, filename: str, mime_type: str, alt: str) -> dict[str, str]:
        mutation = """
        mutation Stage($input: [StagedUploadInput!]!) { stagedUploadsCreate(input: $input) {
          stagedTargets { url resourceUrl parameters { name value } } userErrors { field message }
        }}"""
        result = self._checked(self.graphql(mutation, {"input": [{"filename": filename, "mimeType": mime_type,
                                                                    "httpMethod": "POST", "resource": "IMAGE"}]}),
                               "stagedUploadsCreate")
        targets = result.get("stagedTargets") or []
        if len(targets) != 1:
            raise ShopifyError("Shopify did not return exactly one staged upload target.")
        target = targets[0]
        fields = {item["name"]: item["value"] for item in target.get("parameters", [])}
        upload = self.session.post(target["url"], data=fields, files={"file": (filename, content, mime_type)}, timeout=120)
        if upload.status_code not in {200, 201, 204}:
            raise ShopifyError(f"Staged upload failed with HTTP {upload.status_code}.")
        create = """
        mutation Create($files: [FileCreateInput!]!) { fileCreate(files: $files) {
          files { id fileStatus alt ... on MediaImage { image { url } } } userErrors { field message code }
        }}"""
        created = self._checked(self.graphql(create, {"files": [{"alt": alt, "contentType": "IMAGE",
                                                                   "originalSource": target["resourceUrl"], "filename": filename}]}),
                                "fileCreate").get("files") or []
        if len(created) != 1 or not created[0].get("id"):
            raise ShopifyError("fileCreate did not return a file ID.")
        return self._wait_file(created[0]["id"])

    def _wait_file(self, file_id: str) -> dict[str, str]:
        query = """query File($id: ID!) { node(id: $id) { ... on MediaImage { id fileStatus image { url } } } }"""
        deadline = time.monotonic() + self.config.ready_timeout
        while time.monotonic() < deadline:
            node = self.graphql(query, {"id": file_id}).get("node") or {}
            if node.get("fileStatus") == "READY" and (node.get("image") or {}).get("url"):
                return {"id": file_id, "url": node["image"]["url"]}
            if node.get("fileStatus") == "FAILED":
                raise ShopifyError(f"Shopify failed to process file {file_id}.")
            time.sleep(1.5)
        raise ShopifyError(f"Timed out waiting for Shopify file {file_id}.")

    def product_set(self, product_id: str, content: Mapping[str, str], option_names: list[str], variants: list[dict[str, Any]],
                    settings: Mapping[str, Any]) -> dict[str, Any]:
        options = []
        for name in option_names:
            values = []
            seen = set()
            for variant in variants:
                value = next(item["value"] for item in variant["options"] if item["name"] == name)
                if value not in seen:
                    seen.add(value)
                    values.append({"name": value})
            options.append({"name": name, "values": values})
        variant_inputs = [{
            "optionValues": [{"optionName": item["name"], "name": item["value"]} for item in variant["options"]],
            "price": str(variant["price"]),
            "inventoryItem": {"tracked": False},
        } for variant in variants]
        product_input = {
            "title": content["title"], "handle": content["handle"],
            "descriptionHtml": content["description_html"], "seo": {"title": content["seo_title"],
                                                                        "description": content["seo_description"]},
            "status": str(settings.get("status", "ACTIVE")).upper(),
            "productType": str(settings.get("product_type", "")), "vendor": str(settings.get("vendor", "Wrydeco")),
            "tags": settings.get("tags", ["source_amazon"]), "productOptions": options, "variants": variant_inputs,
        }
        mutation = """mutation Set($input: ProductSetInput!, $identifier: ProductSetIdentifiers) {
          productSet(input: $input, identifier: $identifier, synchronous: true) {
          product { id title handle variants(first: 250) { nodes { id price selectedOptions { name value } inventoryItem { id tracked } } } }
          userErrors { field message code }
        }}"""
        return self._checked(self.graphql(mutation, {"input": product_input,
                                                       "identifier": {"id": gid("Product", product_id)}}), "productSet")["product"]

    def set_metafields(self, product_id: str, metafields: list[dict[str, Any]]) -> None:
        if not metafields:
            return
        inputs = [{**item, "ownerId": gid("Product", product_id)} for item in metafields]
        mutation = """mutation Metafields($metafields: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $metafields) {
          metafields { id namespace key } userErrors { field message code }
        }}"""
        self._checked(self.graphql(mutation, {"metafields": inputs}), "metafieldsSet")

    def attach_media(self, product_id: str, files: list[dict[str, str]], existing_ids: list[str] | None = None) -> list[str]:
        if not files:
            return []
        mutation = """mutation Media($product: ProductUpdateInput!, $media: [CreateMediaInput!]!) {
          productUpdate(product: $product, media: $media) {
            product { id } userErrors { field message }
        }}"""
        result = self.graphql(mutation, {"product": {"id": gid("Product", product_id)}, "media": [
            {"mediaContentType": "IMAGE", "originalSource": item["url"], "alt": item.get("alt", "")} for item in files
        ]}).get("productUpdate") or {}
        errors = result.get("userErrors") or []
        if errors:
            raise ShopifyError("productUpdate media failed: " + json.dumps(errors, ensure_ascii=False))
        existing = set(existing_ids or [])
        nodes = self._snapshot_connection(product_id, "media", "id status")
        ids = [item["id"] for item in nodes if item.get("id") and item["id"] not in existing]
        if len(ids) != len(files):
            raise ShopifyError("Shopify did not return every newly attached media item.")
        return ids

    def verify_media(self, product_id: str, media_ids: list[str]) -> None:
        deadline = time.monotonic() + self.config.ready_timeout
        query = """query ProductMedia($ids: [ID!]!) { nodes(ids: $ids) {
          ... on MediaImage { id status }
          ... on Video { id status }
          ... on Model3d { id status }
          ... on ExternalVideo { id status }
        } }"""
        while time.monotonic() < deadline:
            nodes = self.graphql(query, {"ids": media_ids}).get("nodes") or []
            statuses = {item["id"]: item.get("status") for item in nodes}
            if all(statuses.get(item) == "READY" for item in media_ids):
                return
            if any(statuses.get(item) == "FAILED" for item in media_ids):
                raise ShopifyError("At least one new product media item failed processing.")
            time.sleep(2)
        raise ShopifyError("Timed out verifying replacement product media.")

    def delete_media(self, product_id: str, media_ids: list[str]) -> None:
        if not media_ids:
            return
        mutation = """mutation DeleteMedia($productId: ID!, $mediaIds: [ID!]!) { productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
          deletedMediaIds deletedProductImageIds mediaUserErrors { field message code }
        }}"""
        result = self.graphql(mutation, {"productId": gid("Product", product_id), "mediaIds": media_ids}).get("productDeleteMedia") or {}
        if result.get("mediaUserErrors"):
            raise ShopifyError("productDeleteMedia failed: " + json.dumps(result["mediaUserErrors"], ensure_ascii=False))

    def publish(self, product_id: str, publication_ids: list[str]) -> None:
        if not publication_ids:
            return
        mutation = """mutation Publish($id: ID!, $input: [PublicationInput!]!) { publishablePublish(id: $id, input: $input) {
          userErrors { field message } }
        }"""
        self._checked(self.graphql(mutation, {"id": gid("Product", product_id),
                                               "input": [{"publicationId": item} for item in publication_ids]}), "publishablePublish")

    def sync_publications(self, product_id: str, desired: list[str]) -> None:
        query = """query Publications($id: ID!) {
          publications(first: 250) { nodes { id name } }
          product(id: $id) { resourcePublicationsV2(first: 250) {
            nodes { isPublished publication { id name } }
          } }
        }"""
        data = self.graphql(query, {"id": gid("Product", product_id)})
        publications = (data.get("publications") or {}).get("nodes") or []
        by_name = {str(item.get("name", "")).casefold(): item["id"] for item in publications}
        desired_ids: set[str] = set()
        missing: list[str] = []
        for item in desired:
            if str(item).startswith("gid://"):
                desired_ids.add(str(item))
            elif str(item).casefold() in by_name:
                desired_ids.add(by_name[str(item).casefold()])
            else:
                missing.append(str(item))
        if missing:
            raise ShopifyError("Unknown Shopify publication/channel: " + ", ".join(missing))
        nodes = ((((data.get("product") or {}).get("resourcePublicationsV2")) or {}).get("nodes") or [])
        current_ids = {item["publication"]["id"] for item in nodes if item.get("isPublished") and item.get("publication")}
        self.publish(product_id, sorted(desired_ids - current_ids))
        to_remove = sorted(current_ids - desired_ids)
        if to_remove:
            mutation = """mutation Unpublish($id: ID!, $input: [PublicationInput!]!) {
              publishableUnpublish(id: $id, input: $input) { userErrors { field message } }
            }"""
            self._checked(self.graphql(mutation, {"id": gid("Product", product_id),
                                                   "input": [{"publicationId": item} for item in to_remove]}),
                          "publishableUnpublish")

