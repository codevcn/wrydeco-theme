import os, requests
from dotenv import load_dotenv
load_dotenv('.env')
SHOPIFY_SHOP = os.getenv('SHOPIFY_SHOP')
SHOPIFY_ADMIN_TOKEN = os.getenv('SHOPIFY_ADMIN_TOKEN')
url = f'https://{SHOPIFY_SHOP}.myshopify.com/admin/api/2024-04/graphql.json'
headers = {'X-Shopify-Access-Token': SHOPIFY_ADMIN_TOKEN, 'Content-Type': 'application/json'}
q = 'query { products(first: 5, query: "description:*a*") { edges { node { title } } } }'
r = requests.post(url, json={'query': q}, headers=headers)
print('description:', r.json())
q2 = 'query { products(first: 5, query: "body:*a*") { edges { node { title } } } }'
r2 = requests.post(url, json={'query': q2}, headers=headers)
print('body:', r2.json())
q3 = 'query { products(first: 5, query: "product_type:*a*") { edges { node { title } } } }'
r3 = requests.post(url, json={'query': q3}, headers=headers)
print('product_type:', r3.json())
