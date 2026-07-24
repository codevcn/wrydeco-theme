import os
import sys
import requests
from dotenv import load_dotenv
from pathlib import Path
import re

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.shopify", override=False)

SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP", "").strip().strip('"')
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "").strip().strip('"')
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04").strip().strip('"')

if not SHOPIFY_SHOP.endswith(".myshopify.com"):
    SHOPIFY_SHOP = f"{SHOPIFY_SHOP}.myshopify.com"

headers = {
    "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
    "Content-Type": "application/json",
}

def get_collections():
    url = f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    collections = []
    has_next_page = True
    cursor = None
    
    while has_next_page:
        query = """
        query($cursor: String) {
          collections(first: 250, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
              }
            }
          }
        }
        """
        variables = {"cursor": cursor} if cursor else {}
        response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        collections_data = data["data"]["collections"]
        for edge in collections_data["edges"]:
            collections.append(edge["node"])
            
        has_next_page = collections_data["pageInfo"]["hasNextPage"]
        cursor = collections_data["pageInfo"]["endCursor"]
        
    return collections

def update_collection(collection_id, new_title):
    url = f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    mutation = """
    mutation collectionUpdate($input: CollectionInput!) {
      collectionUpdate(input: $input) {
        collection {
          id
          title
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    variables = {
        "input": {
            "id": collection_id,
            "title": new_title
        }
    }
    response = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers)
    response.raise_for_status()
    data = response.json()
    errors = data.get("data", {}).get("collectionUpdate", {}).get("userErrors", [])
    if errors:
        print(f"Error updating {collection_id}: {errors}")
    else:
        print(f"Updated {collection_id} to '{new_title}'")

def main():
    print("Fetching collections...")
    collections = get_collections()
    print(f"Found {len(collections)} collections.")
    
    for collection in collections:
        title = collection["title"]
        if re.search(r'\bwooden\b', title, re.IGNORECASE):
            new_title = re.sub(r'\bwooden\b', '', title, flags=re.IGNORECASE)
            new_title = " ".join(new_title.split())
            print(f"Renaming '{title}' -> '{new_title}'")
            update_collection(collection["id"], new_title)

if __name__ == "__main__":
    main()
