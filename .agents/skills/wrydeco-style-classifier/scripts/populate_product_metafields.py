import os
import re
import csv
import sys
import json
import time
from pathlib import Path
from collections import defaultdict, Counter
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"d:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-app")
load_dotenv(BASE_DIR / "admin" / ".env")
load_dotenv(BASE_DIR / ".env.shopify", override=False)

SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP", "wrydeco.myshopify.com").strip().strip('"')
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "").strip().strip('"')
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-07").strip().strip('"')
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "").strip().strip('"')
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "").strip().strip('"')

VALID_ROOMS = [
    "Living Room",
    "Bedroom",
    "Kitchen & Dining",
    "Home Office & Library",
    "Nursery & Kids' Room",
    "Entryway & Hallway",
    "Bathroom",
]

TYPE_TO_COLL = {
    'bathroom-vanities': 'bathroom-vanities',
    'bed-frame-with-headboard': 'bed-frame-with-headboard',
    'bedside-table': 'bedside-table',
    'bookshelf-modern': 'bookshelf-modern',
    'bookshelf-rustic': 'bookshelf-rustic',
    'cat-tree': 'cat-tree',
    'coat-rack': 'coat-rack',
    'coffee-tables': 'coffee-tables',
    'console-table': 'console-table',
    'corner-bookshelf': 'corner-bookshelf',
    'custom-engraving': 'signature-pieces',
    'end-table': 'end-table',
    'entryway-shoe-bench-rack': 'entryway-shoe-bench-rack',
    'fireplace-mantel-shelf': 'fireplace-mantel-shelf',
    'floating-bookshelf': 'floating-bookshelf',
    'floating-shelves': 'floating-shelves',
    'jewelry-tree-organizer-stand': 'jewelry-tree-organizer-stand',
    'media-consoles-turntable-stands': 'tv-stands',
    'mirror': 'mirror',
    'parrot-tree': 'parrot-tree',
    'round-wall-art': 'round-wall-art',
    'standing-bookshelf': 'standing-bookshelf',
    'storage-cabinet': 'storage-cabinet',
    'tree-bookshelves': 'tree-bookshelves',
    'tree-coat-rack': 'tree-coat-rack',
    'tree-wine-rack': 'tree-wine-rack',
    'tv-stands': 'tv-stands',
    'wall-decorative-sculpture': 'wall-decorative-sculpture',
    'wall-mounted-tree-bookshelves': 'wall-mounted-tree-bookshelves',
    'wall-mounted-wine-rack': 'wall-mounted-wine-rack',
    'wall-shelf-gothic': 'wall-shelf-gothic',
    'wine-racks': 'wine-racks',
    'wood-floor-lamp-base': 'wood-floor-lamp-base',
    'wooden-floor-sculpture': 'wooden-floor-sculpture',
    'wooden-fruit-bowl': 'wooden-fruit-bowl',
    'wooden-lamp-base': 'wooden-lamp-base',
    'wooden-plant-stands': 'wooden-plant-stand',
}


def normalize_shop_domain(shop: str) -> str:
    parsed = urlparse(shop if "://" in shop else f"https://{shop}")
    host = parsed.netloc or parsed.path
    host = host.replace("/admin", "").strip("/")
    if host == "admin.shopify.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "store":
            return f"{parts[1]}.myshopify.com"
    if host.endswith(".myshopify.com"):
        return host
    return f"{host}.myshopify.com"


def get_valid_token(shop_domain: str) -> str:
    if SHOPIFY_ADMIN_TOKEN:
        r = requests.get(
            f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/shop.json",
            headers={"X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN, "Accept": "application/json"},
            timeout=30,
        )
        if r.ok:
            return SHOPIFY_ADMIN_TOKEN
    r = requests.post(
        f"https://{shop_domain}/admin/oauth/access_token",
        data={
            "grant_type": "client_credentials",
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def graphql_query(shop_domain: str, api_ver: str, token: str, query: str, variables=None):
    url = f"https://{shop_domain}/admin/api/{api_ver}/graphql.json"
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        },
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def load_collection_to_rooms() -> dict[str, list[str]]:
    doc_path = BASE_DIR / "doc" / "rooms" / "all-rooms.md"
    text = doc_path.read_text(encoding="utf-8")
    sections = re.findall(r'##\s+\d+\.\s+([^\n]+)([\s\S]*?)(?=##|\Z)', text)
    coll_to_rooms = defaultdict(list)
    for raw_title, content in sections:
        room_name = raw_title.strip()
        if room_name not in VALID_ROOMS:
            continue
        handles = re.findall(r'-\s+`([a-zA-Z0-9\-_]+)`', content)
        for h in handles:
            if room_name not in coll_to_rooms[h]:
                coll_to_rooms[h].append(room_name)
    return coll_to_rooms


def load_handle_to_styles() -> dict[str, list[str]]:
    csv_path = BASE_DIR / "temp" / "fix-room" / "product_style_mapping.csv"
    handle_to_styles = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            h = row["Handle"].strip()
            styles = [s.strip() for s in row["Assigned_Styles"].split(";") if s.strip()]
            handle_to_styles[h] = styles
    return handle_to_styles


def fetch_all_products(shop: str, api_ver: str, token: str) -> list[dict]:
    products = []
    cursor = None
    query = """
    query GetProducts($cursor: String) {
      products(first: 250, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          handle
          title
          productType
          tags
          collections(first: 30) {
            nodes {
              handle
            }
          }
        }
      }
    }
    """
    while True:
        res = graphql_query(shop, api_ver, token, query, {"cursor": cursor})
        data = res.get("data", {}).get("products", {})
        nodes = data.get("nodes", [])
        products.extend(nodes)
        page_info = data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    return products


def main():
    shop = normalize_shop_domain(SHOPIFY_SHOP)
    api_ver = SHOPIFY_API_VERSION
    token = get_valid_token(shop)
    print(f"Connected to {shop} (API {api_ver})")

    coll_to_rooms = load_collection_to_rooms()
    handle_to_styles = load_handle_to_styles()
    print(f"Loaded room map for {len(coll_to_rooms)} collections and style map for {len(handle_to_styles)} products.")

    products = fetch_all_products(shop, api_ver, token)
    print(f"Fetched {len(products)} total products from Shopify.")

    metafield_inputs = []
    room_counter = Counter()
    style_counter = Counter()

    for p in products:
        pid = p["id"]
        handle = p["handle"]
        ptype = p.get("productType", "")
        tags = p.get("tags", [])
        coll_nodes = p.get("collections", {}).get("nodes", [])

        coll_handles = {c["handle"] for c in coll_nodes}
        mapped_coll = TYPE_TO_COLL.get(ptype)
        if mapped_coll:
            coll_handles.add(mapped_coll)
        for t in tags:
            if t in coll_to_rooms:
                coll_handles.add(t)

        matched_rooms_set = set()
        for ch in coll_handles:
            for r in coll_to_rooms.get(ch, []):
                matched_rooms_set.add(r)

        # Preserve canonical room order
        rooms = [r for r in VALID_ROOMS if r in matched_rooms_set]
        if not rooms:
            # Fallback for custom-engraving or cross-room items
            rooms = ["Living Room", "Home Office & Library", "Bedroom"]

        for r in rooms:
            room_counter[r] += 1

        styles = handle_to_styles.get(handle)
        if not styles:
            styles = ["Japandi", "Mid-Century", "Organic Modern"]

        for s in styles:
            style_counter[s] += 1

        metafield_inputs.append({
            "ownerId": pid,
            "namespace": "custom",
            "key": "room_type",
            "type": "list.single_line_text_field",
            "value": json.dumps(rooms)
        })
        metafield_inputs.append({
            "ownerId": pid,
            "namespace": "custom",
            "key": "interior_style",
            "type": "list.single_line_text_field",
            "value": json.dumps(styles)
        })

    print(f"Prepared {len(metafield_inputs)} metafield entries across {len(products)} products.")

    set_mutation = """
    mutation SetProductMetafields($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields {
          id
          namespace
          key
          value
        }
        userErrors {
          field
          message
          code
        }
      }
    }
    """

    batch_size = 24  # 12 products * 2 metafields = 24 (max allowed per call is 25)
    total_batches = (len(metafield_inputs) + batch_size - 1) // batch_size
    success_count = 0

    for idx in range(0, len(metafield_inputs), batch_size):
        batch = metafield_inputs[idx:idx + batch_size]
        batch_num = (idx // batch_size) + 1
        out = graphql_query(shop, api_ver, token, set_mutation, {"metafields": batch})
        if "errors" in out:
            print(f"[ERROR] Batch {batch_num}/{total_batches} top-level errors: {json.dumps(out['errors'], indent=2)}")
            sys.exit(1)

        payload = out.get("data", {}).get("metafieldsSet", {})
        user_errors = payload.get("userErrors", [])
        if user_errors:
            print(f"[ERROR] Batch {batch_num}/{total_batches} userErrors: {json.dumps(user_errors, indent=2)}")
            sys.exit(1)

        created_mfs = payload.get("metafields", [])
        success_count += len(created_mfs)
        if batch_num % 5 == 0 or batch_num == total_batches:
            print(f"  Batch {batch_num}/{total_batches} completed ({success_count}/{len(metafield_inputs)} metafields set)")
        time.sleep(0.15)

    print("\n=== SUMMARY ===")
    print(f"Total Products Updated: {len(products)}")
    print(f"Total Metafields Set: {success_count}")
    print("\nRoom Type Distribution (products per room):")
    for r in VALID_ROOMS:
        print(f"  - {r}: {room_counter[r]} products")
    print("\nInterior Style Distribution (products per style):")
    for s in ["Rustic", "Japandi", "Mid-Century", "Organic Modern"]:
        print(f"  - {s}: {style_counter[s]} products")


if __name__ == "__main__":
    main()
