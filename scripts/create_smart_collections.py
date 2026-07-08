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
    shop_value = clean(shop_value).strip('"')

    if not shop_value:
        raise RuntimeError("Missing SHOPIFY_SHOP in scripts/.env")

    if shop_value.startswith(("http://", "https://")):
        parsed = urlparse(shop_value)

        if parsed.netloc == "admin.shopify.com":
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[0] == "store":
                return parts[1]

        host = parsed.netloc
    else:
        host = shop_value

    host = host.replace(".myshopify.com", "").strip("/")

    if "." in host:
        raise RuntimeError(
            "SHOPIFY_SHOP must be your Shopify store handle, not the storefront custom domain. "
            "Use the value before .myshopify.com, or the value shown in admin.shopify.com/store/{shop}."
        )

    return host


SHOPIFY_SHOP = ""
SHOPIFY_API_VERSION = clean(os.getenv("SHOPIFY_API_VERSION", "2026-07")).strip('"')
SHOPIFY_ADMIN_TOKEN = clean(os.getenv("SHOPIFY_ADMIN_TOKEN")).strip('"')
SHOPIFY_CLIENT_ID = clean(os.getenv("SHOPIFY_CLIENT_ID")).strip('"')
SHOPIFY_CLIENT_SECRET = clean(os.getenv("SHOPIFY_CLIENT_SECRET")).strip('"')
ACCESS_TOKEN = ""


def get_access_token() -> str:
    if SHOPIFY_ADMIN_TOKEN:
        if SHOPIFY_ADMIN_TOKEN.startswith("shpat_") and len(SHOPIFY_ADMIN_TOKEN) < 30:
            if not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
                raise RuntimeError(
                    "SHOPIFY_ADMIN_TOKEN looks incomplete. "
                    "Paste the full token, or remove SHOPIFY_ADMIN_TOKEN to use client credentials."
                )

            print("SHOPIFY_ADMIN_TOKEN skipped because it looks incomplete.")
            print("Requesting a token with SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET instead.")
        else:
            return SHOPIFY_ADMIN_TOKEN

    if not SHOPIFY_CLIENT_ID or not SHOPIFY_CLIENT_SECRET:
        raise RuntimeError(
            "Missing token config. Provide SHOPIFY_ADMIN_TOKEN or "
            "SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET in scripts/.env."
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


def shopify_rest(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/{path}"
    response = requests.request(
        method,
        url,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Shopify-Access-Token": ACCESS_TOKEN,
        },
        json=payload,
        timeout=30,
    )

    if not response.ok:
        print("REST request failed")
        print("Method:", method)
        print("URL:", url)
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    if not response.text:
        return {}

    return response.json()


def shopify_graphql(query: str, variables: dict | None = None) -> dict:
    url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Shopify-Access-Token": ACCESS_TOKEN,
        },
        json={"query": query, "variables": variables or {}},
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
    data = shopify_graphql(query, {"query": f"handle:{handle}"})
    nodes = data["collections"]["nodes"]
    return nodes[0] if nodes else None


def load_collection_rows(json_path: str) -> list[dict]:
    if not os.path.exists(json_path):
        raise RuntimeError(f"JSON file not found: {json_path}")

    with open(json_path, encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, dict):
        payload = payload.get("collections")

    if not isinstance(payload, list):
        raise RuntimeError(
            "JSON must be an array of smart collection objects, or an object with a 'collections' array."
        )

    rows = []
    for index, row in enumerate(payload, start=1):
        if not isinstance(row, dict):
            raise RuntimeError(f"Collection item #{index} must be an object.")
        rows.append(row)

    return rows


def get_product_type_rules(row: dict) -> list[dict]:
    product_type = clean(row.get("product_type"))
    product_types = row.get("product_types")

    if product_type:
        return [{"column": "type", "relation": "equals", "condition": product_type}]

    if isinstance(product_types, list):
        rules = []
        for value in product_types:
            value = clean(str(value))
            if value:
                rules.append({"column": "type", "relation": "equals", "condition": value})
        return rules

    return []


def build_smart_collection(row: dict) -> dict:
    title = clean(row.get("title"))
    handle = clean(row.get("handle"))
    description_html = clean(row.get("description_html"))
    seo_title = clean(row.get("seo_title"))
    seo_description = clean(row.get("seo_description"))
    image_src = clean(row.get("image_src"))
    image_alt = clean(row.get("image_alt"))
    sort_order = clean(row.get("sort_order")) or "best-selling"
    template_suffix = clean(row.get("template_suffix"))
    published_scope = clean(row.get("published_scope")) or "web"
    published = row.get("published", True)
    disjunctive = row.get("disjunctive", False)
    rules = get_product_type_rules(row)

    if not title:
        raise RuntimeError("Missing title.")

    if not handle:
        raise RuntimeError(f"Missing handle for '{title}'.")

    if not rules:
        raise RuntimeError(f"Missing product_type or product_types for '{title}'.")

    smart_collection = {
        "title": title,
        "handle": handle,
        "rules": rules,
        "disjunctive": bool(disjunctive),
        "sort_order": sort_order,
        "published": bool(published),
        "published_scope": published_scope,
    }

    if description_html:
        smart_collection["body_html"] = description_html

    if seo_title:
        smart_collection["metafields_global_title_tag"] = seo_title

    if seo_description:
        smart_collection["metafields_global_description_tag"] = seo_description

    if template_suffix:
        smart_collection["template_suffix"] = template_suffix

    if image_src and is_public_url(image_src):
        smart_collection["image"] = {"src": image_src, "alt": image_alt or title}
    elif image_src:
        print(
            "Image skipped:",
            f"'{image_src}' is not a public URL. Upload it to Shopify Files/CDN first, then use the HTTPS URL.",
        )

    return smart_collection


def create_smart_collection(smart_collection: dict) -> dict:
    payload = {"smart_collection": smart_collection}
    data = shopify_rest("POST", "smart_collections.json", payload)
    return data["smart_collection"]


def process_json(json_path: str, dry_run: bool, skip_existing: bool) -> None:
    rows = load_collection_rows(json_path)
    skipped = 0
    existing_count = 0
    planned = 0
    created_count = 0
    failed_count = 0

    if not rows:
        print("No smart collections found in JSON.")
        return

    for index, row in enumerate(rows, start=1):
        if row.get("enabled") is False:
            print(f"Item #{index}: skipped because enabled is false")
            skipped += 1
            continue

        try:
            smart_collection = build_smart_collection(row)
            handle = smart_collection["handle"]
            print()
            print(f"Checking collection: {handle}")

            existing = get_collection_by_handle(handle)
            if existing and skip_existing:
                print(f"Skipped existing collection: {existing['title']} ({existing['handle']})")
                existing_count += 1
                continue

            if existing and not skip_existing:
                raise RuntimeError(
                    f"Collection already exists: {existing['title']} ({existing['handle']}). "
                    "Use a new handle or delete/rename the existing collection first."
                )

            if dry_run:
                product_type_rules = [
                    rule for rule in smart_collection["rules"]
                    if rule.get("column") == "type"
                ]
                if len(product_type_rules) == 1:
                    condition = product_type_rules[0].get("condition")
                    if condition == handle:
                        print(
                            "Warning:",
                            "product_type is the same as handle. Make sure this exactly matches Shopify Product type.",
                        )

                print("[DRY RUN] Would create smart collection:")
                print(json.dumps({"smart_collection": smart_collection}, ensure_ascii=False, indent=2))
                planned += 1
                continue

            created = create_smart_collection(smart_collection)
            print("Created:")
            print(f"- ID: {created.get('id')}")
            print(f"- Title: {created.get('title')}")
            print(f"- Handle: {created.get('handle')}")
            print(f"- Rules: {created.get('rules')}")
            created_count += 1
        except Exception as error:
            failed_count += 1
            print()
            print(f"Item #{index} failed:", error)
            if not dry_run:
                raise

    print("")
    print("Summary:")
    print(f"- Skipped disabled: {skipped}")
    print(f"- Skipped existing: {existing_count}")
    print(f"- Planned creates: {planned}")
    print(f"- Created: {created_count}")
    print(f"- Failed: {failed_count}")


def main() -> None:
    global ACCESS_TOKEN
    global SHOPIFY_SHOP

    parser = argparse.ArgumentParser(
        description="Create Shopify smart collections from JSON using Product Type rules."
    )
    parser.add_argument(
        "--json",
        default=str(SCRIPT_DIR / "smart_collections.json"),
        help="Path to smart collections JSON file. Default: scripts/smart_collections.json",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Actually create smart collections. Without this flag, script runs in dry-run mode.",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Fail when a collection handle already exists instead of skipping it.",
    )

    args = parser.parse_args()

    SHOPIFY_SHOP = normalize_shop(os.getenv("SHOPIFY_SHOP", ""))
    ACCESS_TOKEN = get_access_token()

    print("Shop:", f"{SHOPIFY_SHOP}.myshopify.com")
    print("API version:", SHOPIFY_API_VERSION)
    print("JSON:", args.json)
    print("Mode:", "CREATE SMART COLLECTIONS" if args.run else "DRY RUN")
    if not args.run:
        print("Nothing will be created. Add --run to create collections on the real store.")

    process_json(
        args.json,
        dry_run=not args.run,
        skip_existing=not args.no_skip_existing,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print()
        print("ERROR:", error)
        sys.exit(1)
