import os
import requests
from dotenv import load_dotenv

load_dotenv()
SHOPIFY_SHOP = os.getenv('SHOPIFY_SHOP')
SHOPIFY_ADMIN_TOKEN = os.getenv('SHOPIFY_ADMIN_TOKEN')
GRAPHQL_URL = f'https://{SHOPIFY_SHOP}.myshopify.com/admin/api/2024-04/graphql.json'
HEADERS = {'X-Shopify-Access-Token': SHOPIFY_ADMIN_TOKEN, 'Content-Type': 'application/json'}

def test_query(q):
    query = """
    query getProducts($query: String) {
      products(first: 5, query: $query) {
        edges {
          node {
            id
            title
            totalInventory
            tracksInventory
          }
        }
      }
    }
    """
    res = requests.post(GRAPHQL_URL, json={'query': query, 'variables': {'query': q}}, headers=HEADERS)
    print(f'Query: {q}')
    print(res.json())

test_query('inventory_total:>0')
test_query('inventory_total:<=0')
test_query('inventory_management:none')
test_query('inventory_management:not_managed')
test_query('-inventory_management:shopify')
