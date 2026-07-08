import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.shopify", override=False)


def clean(value: str | None) -> str:
    return (value or "").strip()


def is_public_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_shop(shop_value: str) -> str:
    """
    Accepts:
    - 236qm8-w7
    - 236qm8-w7.myshopify.com
    - https://236qm8-w7.myshopify.com
    - https://admin.shopify.com/store/236qm8-w7/apps/...
    Returns:
    - 236qm8-w7
    """
    shop_value = clean(shop_value).strip('"')

    if not shop_value:
        raise RuntimeError("Missing SHOPIFY_SHOP in scripts/.env")

    if shop_value.startswith("http://") or shop_value.startswith("https://"):
        parsed = urlparse(shop_value)

        if parsed.netloc == "admin.shopify.com":
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[0] == "store":
                return parts[1]

        host = parsed.netloc
    else:
        host = shop_value

    host = host.replace(".myshopify.com", "")
    host = host.strip("/")

    if "." in host:
        raise RuntimeError(
            "SHOPIFY_SHOP must be your Shopify store handle, not the storefront custom domain. "
            "Use the value before .myshopify.com, or the value shown in admin.shopify.com/store/{shop}. "
            "For example: SHOPIFY_SHOP=236qm8-w7"
        )

    return host


SHOPIFY_SHOP = ""
SHOPIFY_API_VERSION = clean(os.getenv("SHOPIFY_API_VERSION", "2026-07")).strip('"')

SHOPIFY_ADMIN_TOKEN = clean(os.getenv("SHOPIFY_ADMIN_TOKEN")).strip('"')
SHOPIFY_CLIENT_ID = clean(os.getenv("SHOPIFY_CLIENT_ID")).strip('"')
SHOPIFY_CLIENT_SECRET = clean(os.getenv("SHOPIFY_CLIENT_SECRET")).strip('"')

GRAPHQL_URL = ""
ACCESS_TOKEN = ""


def get_access_token() -> str:
    """
    Priority:
    1. Use SHOPIFY_ADMIN_TOKEN if available.
    2. Otherwise request token using SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET.
    """
    if SHOPIFY_ADMIN_TOKEN:
        if SHOPIFY_ADMIN_TOKEN.startswith("shpat_") and len(SHOPIFY_ADMIN_TOKEN) < 30:
            if not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
                raise RuntimeError(
                    "SHOPIFY_ADMIN_TOKEN looks incomplete. "
                    "Paste the full token, or remove SHOPIFY_ADMIN_TOKEN to use SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET."
                )

            print("SHOPIFY_ADMIN_TOKEN skipped because it looks incomplete.")
            print("Requesting a token with SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET instead.")
        else:
            return SHOPIFY_ADMIN_TOKEN

    if not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
        raise RuntimeError(
            "Missing token config. Provide SHOPIFY_ADMIN_TOKEN or "
            "SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET in .env"
        )

    url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/oauth/access_token"

    response = requests.post(
        url,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        data={
            "grant_type": "client_credentials",
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
        },
        timeout=30,
    )

    if not response.ok:
        print("Failed to get access token")
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    payload = response.json()
    token = payload.get("access_token")

    if not token:
        raise RuntimeError(f"No access_token in response: {payload}")

    print("Access token acquired.")
    print("Scope:", payload.get("scope"))
    print("Expires in:", payload.get("expires_in"))

    return token


def shopify_graphql(query: str, variables: dict | None = None) -> dict:
    response = requests.post(
        GRAPHQL_URL,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": ACCESS_TOKEN,
        },
        json={
            "query": query,
            "variables": variables or {},
        },
        timeout=30,
    )

    if not response.ok:
        print("GraphQL request failed")
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    payload = response.json()

    if "errors" in payload:
        raise RuntimeError(payload["errors"])

    return payload["data"]


def get_collection_by_handle(handle: str) -> dict | None:
    query = """
    query GetCollectionByHandle($query: String!) {
      collections(first: 1, query: $query) {
        nodes {
          id
          title
          handle
        }
      }
    }
    """

    data = shopify_graphql(
        query,
        {
            "query": f"handle:{handle}",
        },
    )

    nodes = data["collections"]["nodes"]
    return nodes[0] if nodes else None


def build_collection_input(row: dict, collection_id: str) -> dict:
    title = clean(row.get("title"))
    description_html = clean(row.get("description_html"))
    new_handle = clean(row.get("new_handle"))
    seo_title = clean(row.get("seo_title"))
    seo_description = clean(row.get("seo_description"))
    image_src = clean(row.get("image_src"))
    image_alt = clean(row.get("image_alt"))

    collection_input = {
        "id": collection_id,
    }

    if title:
        collection_input["title"] = title

    if description_html:
        collection_input["descriptionHtml"] = description_html

    if new_handle:
        collection_input["handle"] = new_handle
        collection_input["redirectNewHandle"] = True

    if seo_title or seo_description:
        collection_input["seo"] = {}

        if seo_title:
            collection_input["seo"]["title"] = seo_title

        if seo_description:
            collection_input["seo"]["description"] = seo_description

    if image_src and is_public_url(image_src):
        collection_input["image"] = {
            "src": image_src,
            "altText": image_alt or title or new_handle,
        }
    elif image_src:
        print(
            "Image skipped:",
            f"'{image_src}' is not a public URL. Upload it to Shopify Files/CDN first, then use the HTTPS URL.",
        )

    return collection_input


def update_collection(collection_input: dict) -> dict:
    mutation = """
    mutation CollectionUpdate($collection: CollectionUpdateInput!) {
      collectionUpdate(collection: $collection) {
        collection {
          id
          title
          handle
          descriptionHtml
          image {
            url
            altText
          }
          seo {
            title
            description
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    data = shopify_graphql(
        mutation,
        {
            "collection": collection_input,
        },
    )

    result = data["collectionUpdate"]

    if result["userErrors"]:
        raise RuntimeError(result["userErrors"])

    return result["collection"]


def load_collection_rows(json_path: str) -> list[dict]:
    if not os.path.exists(json_path):
        raise RuntimeError(f"JSON file not found: {json_path}")

    with open(json_path, encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, dict):
        payload = payload.get("collections")

    if not isinstance(payload, list):
        raise RuntimeError(
            "JSON must be an array of collection objects, or an object with a 'collections' array."
        )

    rows = []

    for index, row in enumerate(payload, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"Collection item #{index} must be an object.")

        rows.append(row)

    return rows


def process_json(json_path: str, dry_run: bool) -> None:
    rows = load_collection_rows(json_path)

    if not rows:
        print("No collections found in JSON.")
        return

    for index, row in enumerate(rows, start=1):
        current_handle = clean(row.get("current_handle"))

        if not current_handle:
            print(f"Item #{index}: skipped because current_handle is empty")
            continue

        print()
        print(f"Finding collection: {current_handle}")

        collection = get_collection_by_handle(current_handle)

        if not collection:
            print(f"Not found: {current_handle}")
            continue

        collection_input = build_collection_input(row, collection["id"])

        if dry_run:
            print("[DRY RUN] Would update:")
            print(json.dumps(collection_input, ensure_ascii=False, indent=2))
            continue

        updated = update_collection(collection_input)

        print("Updated:")
        print(f"- Title: {updated.get('title')}")
        print(f"- Handle: {updated.get('handle')}")

        seo = updated.get("seo") or {}
        print(f"- SEO title: {seo.get('title')}")
        print(f"- SEO description: {seo.get('description')}")

        image = updated.get("image") or {}
        print(f"- Image URL: {image.get('url')}")
        print(f"- Image alt: {image.get('altText')}")


def main():
    global GRAPHQL_URL
    global SHOPIFY_SHOP
    global ACCESS_TOKEN

    parser = argparse.ArgumentParser(
        description="Update Shopify collections from JSON."
    )

    parser.add_argument(
        "--json",
        default=str(SCRIPT_DIR / "collections.json"),
        help="Path to collections JSON file. Default: scripts/collections.json",
    )

    parser.add_argument(
        "--run",
        action="store_true",
        help="Actually update Shopify. Without this flag, script runs in dry-run mode.",
    )

    args = parser.parse_args()

    dry_run = not args.run
    SHOPIFY_SHOP = normalize_shop(os.getenv("SHOPIFY_SHOP", ""))
    GRAPHQL_URL = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    ACCESS_TOKEN = get_access_token()

    print("Shop:", f"{SHOPIFY_SHOP}.myshopify.com")
    print("API version:", SHOPIFY_API_VERSION)
    print("JSON:", args.json)
    print("Mode:", "UPDATE REAL STORE" if args.run else "DRY RUN")

    process_json(args.json, dry_run=dry_run)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print()
        print("ERROR:", error)
        sys.exit(1)
