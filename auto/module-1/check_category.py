import requests
import json
import os

with open('../../admin/.env', 'r') as f:
    env_content = f.read()

token = None
for line in env_content.splitlines():
    if line.startswith('SHOPIFY_ADMIN_TOKEN='):
        token = line.split('=')[1].strip("'\"")

SHOP = 'wrydeco.myshopify.com'
TOKEN = token
API_VERSION = '2026-07'

def graphql_query(query, variables=None):
    url = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"
    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def main():
    query = """
    query($cursor: String) {
      products(first: 250, after: $cursor) {
        edges {
          node {
            id
            title
            productCategory {
              productTaxonomyNode {
                name
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    
    has_next = True
    cursor = None
    no_category = []
    
    while has_next:
        variables = {"cursor": cursor}
        res = graphql_query(query, variables)
        
        if 'errors' in res:
            print(res)
            break
            
        products = res['data']['products']['edges']
        for p in products:
            node = p['node']
            if not node.get('productCategory'):
                no_category.append(node)
                
        page_info = res['data']['products']['pageInfo']
        has_next = page_info['hasNextPage']
        cursor = page_info['endCursor']
        
    print(f"Total products missing category: {len(no_category)}")
    for p in no_category:
        print(f"- {p['id']}: {p['title']}")

if __name__ == "__main__":
    main()
