import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
ADMIN_DIR = ROOT_DIR / "admin"

load_dotenv(ADMIN_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.shopify", override=False)

SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP", "wrydeco.myshopify.com").strip().strip('"')
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "").strip().strip('"')
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-07").strip().strip('"')

if not SHOPIFY_SHOP.endswith(".myshopify.com"):
    SHOPIFY_SHOP = f"{SHOPIFY_SHOP}.myshopify.com"

policy_file = ROOT_DIR / "doc" / "policy" / "public" / "Modify and cancel order policy.html"
if not policy_file.exists():
    print(f"Error: Policy file not found at {policy_file}")
    sys.exit(1)

with open(policy_file, "r", encoding="utf-8") as f:
    new_html = f.read()

print(f"Read updated policy HTML ({len(new_html)} bytes)")

headers = {
    "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# 1. First verify page exists
get_url = f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/pages.json?handle=modify-cancel-order"
resp = requests.get(get_url, headers=headers, timeout=30)
if not resp.ok:
    print(f"Failed to find page: {resp.status_code} - {resp.text}")
    sys.exit(1)

pages = resp.json().get("pages", [])
if not pages:
    print("Page with handle 'modify-cancel-order' not found.")
    sys.exit(1)

page = pages[0]
page_id = page["id"]
print(f"Found page: ID={page_id}, Title='{page['title']}', Handle='{page['handle']}'")

# 2. Update via GraphQL mutation (preferred standard)
graphql_url = f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
mutation = """
mutation UpdatePage($id: ID!, $page: PageUpdateInput!) {
  pageUpdate(id: $id, page: $page) {
    page {
      id
      title
      handle
      updatedAt
    }
    userErrors {
      field
      message
    }
  }
}
"""

variables = {
    "id": f"gid://shopify/Page/{page_id}",
    "page": {
        "body": new_html
    }
}

gql_resp = requests.post(graphql_url, json={"query": mutation, "variables": variables}, headers=headers, timeout=30)
if gql_resp.ok:
    result = gql_resp.json()
    errors = result.get("data", {}).get("pageUpdate", {}).get("userErrors", [])
    if errors:
        print(f"GraphQL userErrors: {errors}")
        print("Falling back to REST API...")
        rest_url = f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/pages/{page_id}.json"
        put_resp = requests.put(rest_url, json={"page": {"id": page_id, "body_html": new_html}}, headers=headers, timeout=30)
        print("REST status:", put_resp.status_code)
        if not put_resp.ok:
            print("REST error:", put_resp.text)
            sys.exit(1)
        print("REST update successful!")
    else:
        updated_info = result.get("data", {}).get("pageUpdate", {}).get("page", {})
        print(f"GraphQL update successful! Page: {updated_info}")
else:
    print(f"GraphQL request failed: {gql_resp.status_code}, falling back to REST API...")
    rest_url = f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/pages/{page_id}.json"
    put_resp = requests.put(rest_url, json={"page": {"id": page_id, "body_html": new_html}}, headers=headers, timeout=30)
    print("REST status:", put_resp.status_code)
    if not put_resp.ok:
        print("REST error:", put_resp.text)
        sys.exit(1)
    print("REST update successful!")

print("All done successfully!")
