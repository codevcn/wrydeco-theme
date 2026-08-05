import os
import requests
import json
from dotenv import load_dotenv

load_dotenv('D:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/admin/.env')

SHOP = os.getenv('SHOPIFY_SHOP')
API_VERSION = os.getenv('SHOPIFY_API_VERSION')
TOKEN = os.getenv('SHOPIFY_ADMIN_TOKEN')

GRAPHQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"

headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": TOKEN
}

query = """
query {
  collections(first: 50) {
    edges {
      node {
        id
        title
        handle
      }
    }
  }
}
"""

response = requests.post(GRAPHQL_URL, headers=headers, json={'query': query})
data = response.json()

print(json.dumps(data, indent=2))
