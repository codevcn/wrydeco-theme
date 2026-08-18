
import os, requests, json
from dotenv import load_dotenv

load_dotenv('/home/vmadmin/shopify-admin-app/.env')
SHOPIFY_SHOP = os.getenv('SHOPIFY_SHOP', 'wrydeco')
SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2024-04')
token = os.getenv('SHOPIFY_ADMIN_TOKEN')
url = f'https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json'
headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}

query1 = '''
query {
  __type(name: "ArticleSortKeys") {
    name
    enumValues {
      name
    }
  }
}
'''
res = requests.post(url, json={'query': query1}, headers=headers)
print(json.dumps(res.json(), indent=2))
