import requests
import json
import os
from dotenv import load_dotenv

load_dotenv('admin/.env')

url = f"https://{os.environ['SHOPIFY_SHOP']}/admin/api/{os.environ['SHOPIFY_API_VERSION']}/graphql.json"
headers = {
    'X-Shopify-Access-Token': os.environ['SHOPIFY_ADMIN_TOKEN'],
    'Content-Type': 'application/json'
}

query_str = """
query {
  taxonomy {
    categories(search: "bookcases", first: 5) {
      edges {
        node {
          id
          name
          fullName
        }
      }
    }
  }
}
"""

r = requests.post(url, headers=headers, json={'query': query_str})
print(json.dumps(r.json(), indent=2))
