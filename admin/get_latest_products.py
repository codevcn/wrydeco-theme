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

def get_latest_products():
    url = f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    query = """
    query {
      products(first: 10, sortKey: CREATED_AT, reverse: true) {
        edges {
          node {
            id
            title
            createdAt
          }
        }
      }
    }
    """
    response = requests.post(url, json={"query": query}, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    if "errors" in data:
        print("GraphQL Errors:", data["errors"])
        return []
        
    products = [edge["node"] for edge in data["data"]["products"]["edges"]]
    return products

if __name__ == "__main__":
    products = get_latest_products()
    for i, prod in enumerate(products, 1):
        print(f"{i}. {prod['title']} (Created at: {prod['createdAt']})")
