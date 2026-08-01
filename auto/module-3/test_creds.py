import requests
import os
from dotenv import load_dotenv

load_dotenv()

SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP")
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION")

print(f"SHOP: {SHOPIFY_SHOP}")
print(f"TOKEN: {SHOPIFY_ADMIN_TOKEN}")
print(f"VERSION: {SHOPIFY_API_VERSION}")

# Test 1: with current version
GRAPHQL_URL = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
    "Content-Type": "application/json"
}

query = "{ shop { name } }"
response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
print("TEST 1 STATUS:", response.status_code)
print("TEST 1 BODY:", response.text)

# Test 2: with 2024-04
GRAPHQL_URL = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/2024-04/graphql.json"
response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
print("TEST 2 STATUS:", response.status_code)
print("TEST 2 BODY:", response.text)
