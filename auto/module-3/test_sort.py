import os, requests
from dotenv import load_dotenv
load_dotenv('.env')
SHOPIFY_SHOP = os.getenv('SHOPIFY_SHOP')
SHOPIFY_ADMIN_TOKEN = os.getenv('SHOPIFY_ADMIN_TOKEN')
url = f'https://{SHOPIFY_SHOP}.myshopify.com/admin/api/2024-04/graphql.json'
headers = {'X-Shopify-Access-Token': SHOPIFY_ADMIN_TOKEN, 'Content-Type': 'application/json'}
q = 'query getProducts($sortKey: ProductSortKeys, $reverse: Boolean, $query: String) { products(first: 2, sortKey: $sortKey, reverse: $reverse, query: $query) { edges { node { title createdAt } } } }'
variables = {'sortKey': 'CREATED_AT', 'reverse': True, 'query': 'tag:example'}
r = requests.post(url, json={'query': q, 'variables': variables}, headers=headers)
print(r.json())
