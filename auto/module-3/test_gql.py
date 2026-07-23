import os
import requests
from dotenv import load_dotenv

load_dotenv()
SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP")
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04")
GRAPHQL_URL = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
    "Content-Type": "application/json"
}

def test_query(q):
    query = """
    query test($query: String, $sortKey: CollectionSortKeys, $reverse: Boolean) {
      collections(first: 5, query: $query, sortKey: $sortKey, reverse: $reverse) {
        edges {
          node {
            title
            productsCount { count }
          }
        }
      }
    }
    """
    response = requests.post(GRAPHQL_URL, json={"query": query, "variables": q}, headers=HEADERS)
    print(q, response.json())

test_query({"query": "products_count:>0", "sortKey": "TITLE", "reverse": False})
test_query({"query": "products_count:0"})
test_query({"sortKey": "PRODUCTS_COUNT"}) # This might error
