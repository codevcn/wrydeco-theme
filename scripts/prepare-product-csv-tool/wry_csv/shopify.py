from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import unquote, urlparse

from dotenv import dotenv_values
import requests

from .common import ROOT, SHOP, Invalid, require, sha256, write_json
from .media import fetch_image, public_url, verify_urls


class Admin:
    """Admin credentials never enter logs, checkpoints or public image sessions."""
    def __init__(self, root: Path = ROOT):
        config = {**dotenv_values(root / ".env.shopify"), **dotenv_values(root / "admin/.env"), **os.environ}
        shop = urlparse("https://" + str(config.get("SHOPIFY_SHOP", "")).removeprefix("https://").rstrip("/"))
        require(shop.hostname == SHOP and shop.path in {"", "/"} and not shop.username, "Refusing credentials for a shop other than WRYDECO")
        version = config.get("SHOPIFY_API_VERSION", "2026-04")
        require(bool(re.fullmatch(r"20\d{2}-(?:01|04|07|10)", version)), "Invalid Shopify API version")
        self.config = config
        self.endpoint = f"https://{SHOP}/admin/api/{version}/graphql.json"
        self.token = config.get("SHOPIFY_ADMIN_TOKEN", "")
        self.renewed = False

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        if not self.token:
            self.renew()
        for attempt in range(4):
            try:
                response = requests.post(self.endpoint, json={"query": query, "variables": variables or {}},
                                         headers={"X-Shopify-Access-Token": self.token}, timeout=(10, 45), allow_redirects=False)
            except requests.RequestException as exc:
                raise Invalid("Shopify request failed; a mutation outcome may need checkpoint reconciliation") from exc
            if response.status_code == 401 and not self.renewed:
                self.renew()
                continue
            if response.status_code == 429:
                time.sleep(min(5, 1 + attempt))
                continue
            require(response.status_code == 200, f"Shopify HTTP {response.status_code}")
            data = response.json()
            if data.get("errors"):
                if all(e.get("extensions", {}).get("code") == "THROTTLED" for e in data["errors"]):
                    time.sleep(2 + attempt)
                    continue
                messages = "; ".join(str(e.get("message", "GraphQL error")) for e in data["errors"])
                raise Invalid("Shopify GraphQL: " + messages.replace(self.token, "[redacted]"))
            require(isinstance(data.get("data"), dict), "Missing Shopify GraphQL data")
            return data["data"]
        raise Invalid("Shopify throttling/auth retry limit reached")

    def renew(self):
        require(not self.renewed, "Token renewal already attempted")
        self.renewed = True
        require(self.config.get("SHOPIFY_CLIENT_ID") and self.config.get("SHOPIFY_CLIENT_SECRET"), "Missing Shopify renewal credentials")
        try:
            response = requests.post(f"https://{SHOP}/admin/oauth/access_token", data={
                "grant_type": "client_credentials", "client_id": self.config["SHOPIFY_CLIENT_ID"],
                "client_secret": self.config["SHOPIFY_CLIENT_SECRET"]}, timeout=30, allow_redirects=False)
            require(response.status_code == 200, f"Shopify token renewal HTTP {response.status_code}")
            self.token = response.json().get("access_token")
            require(self.token, "Token renewal returned no token")
        except requests.RequestException as exc:
            raise Invalid("Shopify token renewal failed") from exc

    def pages(self, field: str, selection: str, arguments: str = "", variables: dict | None = None):
        cursor, seen = None, set()
        while True:
            query = f'query($after:String) {{ {field}(first:100, after:$after {arguments}) {{ nodes {{ {selection} }} pageInfo {{hasNextPage endCursor}} }} }}'
            result = self.graphql(query, {"after": cursor, **(variables or {})})[field]
            yield from result["nodes"]
            if not result["pageInfo"]["hasNextPage"]:
                break
            cursor = result["pageInfo"]["endCursor"]
            require(cursor and cursor not in seen, f"Invalid/repeated pagination cursor for {field}")
            seen.add(cursor)

    def snapshot(self, manifest: dict) -> dict:
        shop = self.graphql("query { shop {myshopifyDomain currencyCode} }")["shop"]
        require(shop["myshopifyDomain"] == SHOP, "Wrong store returned by Admin API")
        definitions = {}
        for d in self.pages("metafieldDefinitions", "key type {name} validations {name value}", ', ownerType:PRODUCT, namespace:"custom"'):
            values = {v["name"]: v["value"] for v in d["validations"]}
            definitions[d["key"]] = {"type": d["type"]["name"], "choices": json.loads(values["choices"]) if "choices" in values else []}
        categories = {}
        for breadcrumb in dict.fromkeys(p["category"] for p in manifest["products"]):
            cursor, seen = None, set()
            while True:
                response = self.graphql("""query($after:String,$search:String!) {taxonomy {categories(first:100,after:$after,search:$search) {
                    nodes {id fullName} pageInfo {hasNextPage endCursor}}}}""",
                    {"after": cursor, "search": breadcrumb.rsplit(" > ", 1)[-1]})["taxonomy"]["categories"]
                categories.update({n["fullName"]: n["id"] for n in response["nodes"] if n["fullName"] == breadcrumb})
                if not response["pageInfo"]["hasNextPage"]:
                    break
                cursor = response["pageInfo"]["endCursor"]
                require(cursor and cursor not in seen, "Invalid taxonomy cursor")
                seen.add(cursor)
            require(breadcrumb in categories, f"Category does not match Shopify taxonomy: {breadcrumb}")
        return {"version": 1, "shop": SHOP, "currency": shop["currencyCode"],
                "collected_at": datetime.now(timezone.utc).isoformat(), "definitions": definitions,
                "authors": list(self.pages("metaobjects", "id handle displayName", ', type:"product_author"')),
                "collections": list(self.pages("collections", "id handle title ruleSet {appliedDisjunctively rules {column relation condition}}")),
                "occupied_handles": [p["handle"] for p in self.pages("products", "handle")],
                "occupied_skus": [v["sku"] for v in self.pages("productVariants", "sku") if v.get("sku")],
                "categories": categories}

    def wait_file(self, file_id: str) -> dict:
        for _ in range(40):
            node = self.graphql("query($id:ID!){node(id:$id){... on MediaImage {id fileStatus image {url}}}}", {"id": file_id})["node"]
            require(node, "Checkpoint file no longer exists on Shopify")
            require(node["fileStatus"] != "FAILED", "Shopify file processing failed")
            if node["fileStatus"] == "READY" and (node.get("image") or {}).get("url"):
                return {"id": file_id, "url": node["image"]["url"]}
            time.sleep(1.5)
        raise Invalid("File not READY yet; checkpoint saved, resume stage later")

    def find_file(self, filename: str) -> list[dict]:
        result = self.graphql("""query($query:String!){files(first:100,query:$query){nodes {
          ... on MediaImage {id fileStatus image {url} originalSource {url}} } pageInfo {hasNextPage}}}""", {"query": 'filename:"' + filename + '"'})["files"]
        require(not result["pageInfo"]["hasNextPage"], "Ambiguous file reconciliation search")
        return [n for n in result["nodes"] if n.get("id") and any(
            unquote(urlparse((n.get(key) or {}).get("url", "")).path).rsplit("/", 1)[-1] == filename for key in ("image", "originalSource"))]


def checked(payload: dict, key: str) -> dict:
    result = payload[key]
    require(not result.get("userErrors"), f"Shopify {key} rejected file operation: " + "; ".join(str(e.get("message")) for e in result.get("userErrors", [])))
    return result


def stage(products: list[dict], checkpoint: dict, path: Path, admin: Admin, fetcher=fetch_image) -> dict:
    require(checkpoint.get("shop", SHOP) == SHOP, "Checkpoint shop mismatch")
    checkpoint.update(version=1, shop=SHOP)
    files = checkpoint.setdefault("files", {})
    external = verify_urls([image["url"] for product in products for image in product["images"]
                            if image.get("url") and image["local"]["sha256"] not in files], fetcher=fetcher)
    require(not external["errors"], "Existing public image URL failed verification; no new Files uploads started")
    for product in products:
        for index, image in enumerate(product["images"], 1):
            if image.get("url") and image["local"]["sha256"] not in files:
                continue
            info = image["local"]
            fingerprint = info["sha256"]
            record = files.get(fingerprint)
            if record is None:
                filename = f'{product["handle"][:60]}-{index:02d}-{fingerprint[:16]}.{info["extension"]}'
                record = files[fingerprint] = {"shop": SHOP, "sha256": fingerprint, "filename": filename, "state": "new"}
            if record.get("id"):
                ready = admin.wait_file(record["id"])
            elif record["state"] == "creating":
                matches = admin.find_file(record["filename"])
                require(len(matches) == 1, "Uncertain fileCreate outcome; reconcile checkpoint filename before retrying (no new file was created)")
                record["id"] = matches[0]["id"]
                write_json(path, checkpoint)
                ready = admin.wait_file(record["id"])
            else:
                target = checked(admin.graphql("""mutation($input:[StagedUploadInput!]!){stagedUploadsCreate(input:$input){
                    stagedTargets {url resourceUrl parameters {name value}} userErrors {message}}}""", {"input": [{
                    "filename": record["filename"], "mimeType": info["mime"], "resource": "IMAGE", "httpMethod": "POST"}]}), "stagedUploadsCreate")["stagedTargets"]
                require(len(target) == 1, "Expected exactly one staged upload target")
                target = target[0]
                public_url(target["url"])
                data = Path(info["path"]).read_bytes()
                require(sha256(data) == fingerprint, "Local image changed after validation")
                try:
                    upload = requests.post(target["url"], data={p["name"]: p["value"] for p in target["parameters"]},
                                           files={"file": (record["filename"], data, info["mime"])}, timeout=(10, 90), allow_redirects=False)
                    require(upload.status_code in {200, 201, 204}, f"Staged image upload HTTP {upload.status_code}")
                except requests.RequestException as exc:
                    raise Invalid("Staged image upload failed") from exc
                # Save intent BEFORE fileCreate; never blindly repeat a possibly successful mutation.
                record["state"] = "creating"
                write_json(path, checkpoint)
                created = checked(admin.graphql("""mutation($files:[FileCreateInput!]!){fileCreate(files:$files){
                    files {id} userErrors {message}}}""", {"files": [{"filename": record["filename"], "contentType": "IMAGE",
                    "originalSource": target["resourceUrl"], "alt": image["alt"], "duplicateResolutionMode": "RAISE_ERROR"}]}), "fileCreate")["files"]
                require(len(created) == 1 and created[0].get("id"), "fileCreate returned no unique ID; reconcile checkpoint")
                record["id"] = created[0]["id"]
                write_json(path, checkpoint)
                ready = admin.wait_file(record["id"])
            verification = fetcher(ready["url"])
            record.update(ready, state="ready", public_verification=verification)
            write_json(path, checkpoint)
    return checkpoint
