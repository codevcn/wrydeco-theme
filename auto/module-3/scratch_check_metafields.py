import os
import requests
from dotenv import load_dotenv

load_dotenv()
SHOPIFY_SHOP = os.getenv('SHOPIFY_SHOP')
SHOPIFY_ADMIN_TOKEN = os.getenv('SHOPIFY_ADMIN_TOKEN')
GRAPHQL_URL = f'https://{SHOPIFY_SHOP}.myshopify.com/admin/api/2024-04/graphql.json'
HEADERS = {'X-Shopify-Access-Token': SHOPIFY_ADMIN_TOKEN, 'Content-Type': 'application/json'}

query = """
{
  products(first: 5) {
    edges {
      node {
        title
        metafields(first: 20) {
          edges {
            node {
              namespace
              key
              value
            }
          }
        }
      }
    }
  }
}
"""
res = requests.post(GRAPHQL_URL, json={'query': query}, headers=HEADERS)
print(res.json())
