#!/usr/bin/env python3
"""Append product-gallery images to an existing Shopify product.

Configure the four variables below, then run the script. It reads every
``assets.product_media_gallery.images[*].source_url`` from a crawl JSON file and
adds those URLs as media on the product identified by ``PRODUCT_ID`` through the
Shopify Admin GraphQL API. Existing product images are kept; the URLs are
appended.

    python update_product_photos.py
    python update_product_photos.py --dry-run   # list the URLs without calling Shopify

Dependencies:

    pip install requests
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Configuration - edit these four variables.
# --------------------------------------------------------------------------- #

# The Shopify product to update. Accepts a numeric id ("8345739722809") or a
# full GID ("gid://shopify/Product/8345739722809").
PRODUCT_ID = "8346020282425"

# Path to the crawl JSON whose gallery source_url values become the new images.
JSON_FILE_CONTAINS_SOURCE_URLS = "D:\\D-Jobs\\ae-B6\\Shopify\\stores\\main\\wrydeco\\wrydeco-app\\auto\\data\\B0H6FGCCVP.json"

# Path to the .env file that stores the Admin API access token.
ENV_FILE_CONTAINS_ACCESS_TOKEN = "D:\\D-Jobs\\ae-B6\\Shopify\\stores\\main\\wrydeco\\wrydeco-app\\auto\\.env"

# The key inside the .env file that holds the Admin API access token.
STORE_ADMIN_ACCESS_TOKEN_KEY = "IMPORT_STORE_ADMIN_ACCESS_TOKEN"

# --------------------------------------------------------------------------- #

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

import requests


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_API_VERSION = "2026-07"
DEFAULT_TIMEOUT_SECONDS = 60
MEDIA_BATCH_SIZE = 50

# .env keys tried, in order, to find the destination store domain. The first
# non-empty value wins. A prefix on the token key (e.g. "IMPORT_") is honoured
# first so this helper can target the same store as the matching importer.
STORE_DOMAIN_KEYS = (
    "SHOPIFY_STORE_DOMAIN",
    "STORE_DOMAIN",
    "SHOP_DOMAIN",
)


class AppError(RuntimeError):
    """Raised for a user-actionable error."""


def resolve_path(raw_path: str) -> Path:
    """Resolve a configured path against the CWD, this folder, then auto/."""
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    candidates = [
        Path.cwd() / path,
        SCRIPT_DIR / path,
        SCRIPT_DIR.parent / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def load_env_file(path: Path) -> dict[str, str]:
    """Load a KEY=VALUE .env file without an extra dependency."""
    if not path.exists():
        raise AppError(f".env file not found: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def resolve_store_domain(env_values: Mapping[str, str], token_key: str) -> str:
    """Find the destination store domain in the .env file."""
    # Prefer a domain key that shares the token key's prefix (IMPORT_, etc.).
    prefix = ""
    if "_" in token_key:
        candidate_prefix = token_key.split("_", 1)[0] + "_"
        if candidate_prefix != token_key:
            prefix = candidate_prefix

    ordered_keys: list[str] = []
    if prefix:
        ordered_keys.extend(f"{prefix}{key}" for key in STORE_DOMAIN_KEYS)
    ordered_keys.extend(STORE_DOMAIN_KEYS)

    for key in ordered_keys:
        value = (env_values.get(key) or "").strip()
        if value:
            return normalize_store_domain(value)

    raise AppError(
        "Could not find a store domain in the .env file. Add one of: "
        + ", ".join(ordered_keys)
    )


def normalize_store_domain(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    domain = (parsed.netloc or parsed.path).strip().strip("/").lower()
    if not domain:
        raise AppError(f"Invalid Shopify store domain: {value!r}")
    return domain


def to_product_gid(value: Any) -> str:
    """Return a Shopify product GID from a numeric id or an existing GID."""
    text = str(value).strip()
    if not text:
        raise AppError("PRODUCT_ID is empty; set it to a product id or GID.")
    if text.startswith("gid://"):
        return text
    digits = text.rsplit("/", 1)[-1]
    if not digits.isdigit():
        raise AppError(
            f"PRODUCT_ID must be a numeric id or a gid://shopify/Product/... value: {value!r}"
        )
    return f"gid://shopify/Product/{digits}"


def load_gallery_images(json_path: Path) -> list[dict[str, str]]:
    """Return ordered, de-duplicated {url, alt} records from the gallery."""
    if not json_path.is_file():
        raise AppError(f"JSON file not found: {json_path}")
    try:
        data = json.loads(json_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AppError(f"Invalid JSON in {json_path}: {exc}") from exc

    try:
        images = data["assets"]["product_media_gallery"]["images"]
    except (KeyError, TypeError) as exc:
        raise AppError(
            "JSON is missing assets.product_media_gallery.images."
        ) from exc
    if not isinstance(images, list):
        raise AppError("assets.product_media_gallery.images must be an array.")

    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, image in enumerate(images, start=1):
        if not isinstance(image, Mapping):
            continue
        url = image.get("source_url")
        if not isinstance(url, str) or not url.strip():
            continue
        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise AppError(f"Gallery image {index} has a non-HTTP source_url: {url!r}")
        if url in seen:
            continue
        seen.add(url)
        alt = image.get("alt_text")
        records.append({"url": url, "alt": alt.strip() if isinstance(alt, str) else ""})

    if not records:
        raise AppError(
            "No usable source_url values were found in "
            "assets.product_media_gallery.images."
        )
    return records


class ShopifyClient:
    PRODUCT_QUERY = """
    query product($id: ID!) {
      product(id: $id) {
        id
        title
        media(first: 1) { pageInfo { hasNextPage } }
      }
    }
    """

    PRODUCT_CREATE_MEDIA_MUTATION = """
    mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $productId, media: $media) {
        media {
          id
          status
          ... on MediaImage { image { url } }
        }
        mediaUserErrors { field message code }
      }
    }
    """

    def __init__(self, store_domain: str, access_token: str, api_version: str) -> None:
        self.access_token = access_token
        self.endpoint = (
            f"https://{store_domain}/admin/api/{api_version}/graphql.json"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "wrydeco-update-product-photos/1.0", "Accept": "application/json"}
        )

    def graphql(self, query: str, variables: Mapping[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            self.endpoint,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.access_token,
            },
            json={"query": query, "variables": variables},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise AppError(
                f"Shopify returned a non-JSON response: {response.text[:500]}"
            ) from exc
        if payload.get("errors"):
            raise AppError(
                "Shopify GraphQL error: " + json.dumps(payload["errors"], ensure_ascii=False)
            )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise AppError("Shopify GraphQL response does not contain a data object.")
        return data

    def get_product_title(self, product_gid: str) -> str:
        data = self.graphql(self.PRODUCT_QUERY, {"id": product_gid})
        product = data.get("product")
        if not isinstance(product, dict) or not product.get("id"):
            raise AppError(f"No product was found for id {product_gid}.")
        return str(product.get("title") or "")

    def add_media(
        self, product_gid: str, media_records: Sequence[Mapping[str, str]]
    ) -> int:
        added = 0
        for start in range(0, len(media_records), MEDIA_BATCH_SIZE):
            batch = media_records[start : start + MEDIA_BATCH_SIZE]
            media_input = [
                {
                    "originalSource": record["url"],
                    "alt": record.get("alt") or "",
                    "mediaContentType": "IMAGE",
                }
                for record in batch
            ]
            data = self.graphql(
                self.PRODUCT_CREATE_MEDIA_MUTATION,
                {"productId": product_gid, "media": media_input},
            )
            result = data.get("productCreateMedia") or {}
            errors = result.get("mediaUserErrors") or []
            if errors:
                raise AppError(
                    "productCreateMedia failed: "
                    + json.dumps(errors, ensure_ascii=False)
                )
            added += len(result.get("media") or [])
        return added


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append gallery source_url images to a Shopify product."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the images that would be added without calling Shopify.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        product_gid = to_product_gid(PRODUCT_ID)
        json_path = resolve_path(JSON_FILE_CONTAINS_SOURCE_URLS)
        images = load_gallery_images(json_path)

        print(f"Product: {product_gid}")
        print(f"JSON: {json_path}")
        print(f"Images to add: {len(images)}")
        for index, record in enumerate(images, start=1):
            print(f"  {index:02d}. {record['url']}")

        if args.dry_run:
            print("Dry run: no Shopify calls were made.")
            return 0

        env_path = resolve_path(ENV_FILE_CONTAINS_ACCESS_TOKEN)
        env_values = load_env_file(env_path)
        access_token = (env_values.get(STORE_ADMIN_ACCESS_TOKEN_KEY) or "").strip()
        if not access_token:
            raise AppError(
                f"Access token key {STORE_ADMIN_ACCESS_TOKEN_KEY!r} is missing or "
                f"empty in {env_path}."
            )
        store_domain = resolve_store_domain(env_values, STORE_ADMIN_ACCESS_TOKEN_KEY)
        print(f"Store: {store_domain}")

        client = ShopifyClient(store_domain, access_token, DEFAULT_API_VERSION)
        title = client.get_product_title(product_gid)
        print(f"Found product: {title!r}")

        added = client.add_media(product_gid, images)
        print(f"Done. Added {added} image(s) to the product.")
        return 0
    except AppError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"ERROR: network error talking to Shopify: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
