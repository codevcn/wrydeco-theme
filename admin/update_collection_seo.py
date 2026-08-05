import os
import requests
import json
from dotenv import load_dotenv

# Load env
load_dotenv('D:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/admin/.env')

SHOP = os.getenv('SHOPIFY_SHOP')
API_VERSION = os.getenv('SHOPIFY_API_VERSION')
TOKEN = os.getenv('SHOPIFY_ADMIN_TOKEN')

GRAPHQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"

headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": TOKEN
}

# 1. Get collection by handle
get_query = """
query {
  collectionByHandle(handle: "bookshelf-corner-living-room") {
    id
    title
    handle
  }
}
"""

response = requests.post(GRAPHQL_URL, headers=headers, json={'query': get_query})
data = response.json()

collection = data.get('data', {}).get('collectionByHandle')

if not collection:
    print("Collection 'bookshelf-corner-living-room' not found. It might have already been updated to the new handle or doesn't exist.")
    # Try finding by the new handle just in case it was already run
    get_query_new = """
    query {
      collectionByHandle(handle: "corner-bookshelves-living-room") {
        id
        title
        handle
      }
    }
    """
    resp_new = requests.post(GRAPHQL_URL, headers=headers, json={'query': get_query_new})
    data_new = resp_new.json()
    collection = data_new.get('data', {}).get('collectionByHandle')
    
    if not collection:
        print("Not found by new handle either.")
        exit(1)
    else:
        print("Found collection by new handle.")
else:
    print(f"Found collection: {collection['title']} ({collection['id']})")

collection_id = collection['id']

# 2. Update collection
update_mutation = """
mutation collectionUpdate($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection {
      id
      title
      handle
      seo {
        title
        description
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

description_html = "<p>Discover corner bookshelves designed to transform unused living room spaces into warm, functional displays. This collection features sculptural wooden shelving inspired by natural branches, organic forms and the character of solid wood.</p><p>Ideal for displaying books, plants, framed photographs and decorative objects, each bookshelf adds visual interest without making the room feel crowded. The natural wood tones pair beautifully with modern, rustic, farmhouse and nature-inspired interiors.</p><p>Explore the collection to find a distinctive bookshelf that brings storage, craftsmanship and natural beauty to your living room corner.</p>"

variables = {
    "input": {
        "id": collection_id,
        "title": "Corner Bookshelves for Living Rooms",
        "descriptionHtml": description_html,
        "handle": "corner-bookshelves-living-room",
        "seo": {
            "title": "Corner Bookshelves for Living Rooms | Wrydeco",
            "description": "Shop sculptural corner bookshelves for living rooms, crafted with natural wood forms to add storage, warmth and character to unused spaces."
        }
    }
}

update_response = requests.post(GRAPHQL_URL, headers=headers, json={'query': update_mutation, 'variables': variables})
update_data = update_response.json()

user_errors = update_data.get('data', {}).get('collectionUpdate', {}).get('userErrors', [])
if user_errors:
    print(f"Error updating collection: {user_errors}")
else:
    updated_col = update_data.get('data', {}).get('collectionUpdate', {}).get('collection', {})
    print("Collection successfully updated!")
    print(json.dumps(updated_col, indent=2))
