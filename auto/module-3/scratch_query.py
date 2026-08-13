import requests, os
from dotenv import load_dotenv
load_dotenv('.env')
url = 'https://' + os.environ['SHOPIFY_SHOP'] + '.myshopify.com/admin/api/2024-04/graphql.json'
headers = {'X-Shopify-Access-Token': os.environ['SHOPIFY_ADMIN_TOKEN'], 'Content-Type': 'application/json'}
query = """{
  __type(name: "ProductOptionUpdateVariantStrategy") {
    enumValues {
      name
      description
    }
  }
}"""
r = requests.post(url, json={'query': query}, headers=headers)
print(r.json())
