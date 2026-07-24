import os
import requests
from dotenv import load_dotenv
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.shopify", override=False)

SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP", "").strip().strip('"')
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "").strip().strip('"')
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04").strip().strip('"')

if not SHOPIFY_SHOP.endswith(".myshopify.com"):
    SHOPIFY_SHOP = f"{SHOPIFY_SHOP}.myshopify.com"

headers = {
    "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
    "Content-Type": "application/json",
}

def update_product_handle(product_id, handle):
    url = f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    mutation = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          handle
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    variables = {
        "input": {
            "id": product_id,
            "handle": handle
        }
    }
    response = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers)
    response.raise_for_status()
    data = response.json()
    errors = data.get("data", {}).get("productUpdate", {}).get("userErrors", [])
    if errors:
        print(f"Error updating {product_id}: {errors}")
    else:
        print(f"Updated {product_id} to handle '{handle}' (length: {len(handle)})")

updates = {
    "gid://shopify/Product/8355804676153": "natural-wood-corner-tree-branch-bookshelf-custom-design",
    "gid://shopify/Product/8355804610617": "handcrafted-wood-corner-tree-shelf-canyon-canopy-design",
    "gid://shopify/Product/8355804577849": "custom-handcrafted-natural-wood-corner-tree-bookshelf",
    "gid://shopify/Product/8355804545081": "live-edge-tree-branch-bookshelf-with-bench-11-tier",
    "gid://shopify/Product/8355804512313": "natural-wood-corner-tree-branch-shelf-sun-climbers-ladder",
    "gid://shopify/Product/8355782328377": "rustic-wood-tree-branch-floating-bookshelf-4-tier-decor",
    "gid://shopify/Product/8355782295609": "canyon-spirit-arbor-handcrafted-wood-tree-branch-shelf",
    "gid://shopify/Product/8355782262841": "the-mesa-drift-canopy-handcrafted-wood-tree-branch-shelf",
    "gid://shopify/Product/8355782230073": "handcrafted-5-tier-wood-tree-branch-floating-bookshelf",
    "gid://shopify/Product/8355782197305": "handcrafted-4-tier-wood-tree-branch-bookshelf-sequoia"
}

if __name__ == "__main__":
    for pid, handle in updates.items():
        if not (50 <= len(handle) <= 60):
            print(f"WARNING: Handle length is {len(handle)}: {handle}")
        update_product_handle(pid, handle)
