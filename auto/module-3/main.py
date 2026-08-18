import os
import re
import time
import uuid
import csv
import io
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import requests

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP")
SHOPIFY_ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04") # Fallback to 2024-04 if not set

GRAPHQL_URL = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
    "Content-Type": "application/json"
}

def get_products(first=50, after=None, before=None, last=None, filter_query=None, sort_key="CREATED_AT", reverse=True):
    query = """
    query getProducts($first: Int, $last: Int, $after: String, $before: String, $query: String, $sortKey: ProductSortKeys, $reverse: Boolean) {
      productsCount(query: $query) {
        count
      }
      products(first: $first, last: $last, after: $after, before: $before, query: $query, sortKey: $sortKey, reverse: $reverse) {
        pageInfo {
          hasNextPage
          endCursor
          hasPreviousPage
          startCursor
        }
        edges {
          cursor
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            totalInventory
            tracksInventory
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            amazon_link: metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    variables = {}
    if after:
        variables = {"first": first, "after": after, "sortKey": sort_key, "reverse": reverse}
    elif before:
        variables = {"last": first, "before": before, "sortKey": sort_key, "reverse": reverse}
    else:
        variables = {"first": first, "sortKey": sort_key, "reverse": reverse}

    if filter_query:
        variables["query"] = filter_query

    response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        print("GraphQL Errors:", data["errors"])
        return {"products": {"edges": [], "pageInfo": {}}, "productsCount": {"count": 0}}
    return data["data"]

def get_products_by_metafield_amazon_link(keyword, sort_by="created_desc"):
    query = """
    query getProducts($after: String) {
      products(first: 25, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_matched_edges = []
    has_next = True
    cursor = None
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        for edge in products_data["edges"]:
            mf = edge["node"].get("metafield")
            if mf and mf.get("value") and keyword.lower() in mf["value"].lower():
                all_matched_edges.append(edge)
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_metafield_amazon_link_list(keywords_str, sort_by="created_desc"):
    query = """
    query getProducts($after: String) {
      products(first: 25, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_matched_edges = []
    has_next = True
    cursor = None
    keyword_list = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        for edge in products_data["edges"]:
            mf = edge["node"].get("metafield")
            if mf and mf.get("value"):
                mf_val = mf["value"].lower()
                if any(k in mf_val for k in keyword_list):
                    all_matched_edges.append(edge)
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_metafield_rich_description(keyword, sort_by="created_desc"):
    query = """
    query getProducts($after: String) {
      products(first: 25, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            metafield(namespace: "custom", key: "rich_description") {
              value
            }
            amazon_link: metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_matched_edges = []
    has_next = True
    cursor = None
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        for edge in products_data["edges"]:
            mf = edge["node"].get("metafield")
            if mf and mf.get("value") and keyword.lower() in mf["value"].lower():
                all_matched_edges.append(edge)
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_description(keyword, sort_by="created_desc"):
    query = """
    query getProducts($after: String) {
      products(first: 25, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            amazon_link: metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_matched_edges = []
    has_next = True
    cursor = None
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        for edge in products_data["edges"]:
            desc = edge["node"].get("descriptionHtml")
            if desc and keyword.lower() in desc.lower():
                all_matched_edges.append(edge)
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_category(keyword, sort_by="created_desc"):
    query = """
    query getProducts($after: String) {
      products(first: 25, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            amazon_link: metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_matched_edges = []
    has_next = True
    cursor = None
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        for edge in products_data["edges"]:
            cat_node = edge["node"].get("category")
            if cat_node and cat_node.get("name") and keyword.lower() in cat_node["name"].lower():
                all_matched_edges.append(edge)
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_variant_option(keyword, sort_by="created_desc", exclude=False):
    query = """
    query getProducts($after: String) {
      products(first: 25, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
              values
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            amazon_link: metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_matched_edges = []
    has_next = True
    cursor = None
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        for edge in products_data["edges"]:
            options = edge["node"].get("options", [])
            matched = False
            for opt in options:
                if keyword.lower() in opt.get("name", "").lower():
                    matched = True
                    break
                for val in opt.get("values", []):
                    if keyword.lower() in str(val).lower():
                        matched = True
                        break
                if matched:
                    break
            if exclude:
                if not matched:
                    all_matched_edges.append(edge)
            else:
                if matched:
                    all_matched_edges.append(edge)
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_collection(handle, sort_by="created_desc", after=None, before=None):
    query = """
    query getCollectionProducts($handle: String!, $first: Int, $last: Int, $after: String, $before: String, $sortKey: ProductCollectionSortKeys, $reverse: Boolean) {
      collectionByHandle(handle: $handle) {
        productsCount { count }
        products(first: $first, last: $last, after: $after, before: $before, sortKey: $sortKey, reverse: $reverse) {
          pageInfo {
            hasNextPage
            hasPreviousPage
            endCursor
            startCursor
          }
          edges {
            node {
              id
              handle
              title
              descriptionHtml
              createdAt
              productType
              category {
                name
              }
              priceRangeV2 {
                minVariantPrice {
                  amount
                }
              }
              options {
                name
              }
              collections(first: 20) {
                edges {
                  node {
                    title
                  }
                }
              }
              amazon_link: metafield(namespace: "custom", key: "amazon_link") {
                value
              }
              media(first: 50) {
                edges {
                  node {
                    ... on MediaImage {
                      id
                      image {
                        url
                      }
                    }
                    ... on Video {
                      id
                      preview {
                        image {
                          url
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    sort_key_map = {
        "price_asc": ("PRICE", False),
        "price_desc": ("PRICE", True),
        "created_asc": ("CREATED", False),
        "created_desc": ("CREATED", True)
    }
    sort_key, reverse = sort_key_map.get(sort_by, ("CREATED", True))
    
    variables = {"handle": handle, "sortKey": sort_key, "reverse": reverse}
    if after:
        variables["first"] = 50
        variables["after"] = after
    elif before:
        variables["last"] = 50
        variables["before"] = before
    else:
        variables["first"] = 50
        
    res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        print("GraphQL Errors:", data["errors"])
        return {"products": {"edges": [], "pageInfo": {}}, "productsCount": {"count": 0}}
        
    collection_data = data.get("data", {}).get("collectionByHandle")
    if not collection_data:
        return {"products": {"edges": [], "pageInfo": {}}, "productsCount": {"count": 0}}
        
    return {
        "products": collection_data.get("products", {}),
        "productsCount": collection_data.get("productsCount", {})
    }

def get_products_by_special_filter(special_filter, sort_by="created_desc"):
    query = """
    query getProducts($after: String) {
      products(first: 50, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            totalInventory
            tracksInventory
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            amazon_link: metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_matched_edges = []
    has_next = True
    cursor = None
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        for edge in products_data["edges"]:
            node = edge["node"]
            tracks_inventory = node.get("tracksInventory", False)
            total_inventory = node.get("totalInventory", 0) or 0
            
            matched = False
            if special_filter == "out_of_stock":
                matched = tracks_inventory and total_inventory <= 0
            elif special_filter == "in_stock":
                matched = tracks_inventory and total_inventory > 0
            elif special_filter == "not_tracked":
                matched = not tracks_inventory
                
            if matched:
                all_matched_edges.append(edge)
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_review_status(has_reviews: bool, sort_by="created_desc"):
    import json
    query = """
    query getProducts($after: String) {
      products(first: 50, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            amazon_link: metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            reviews_count: metafield(namespace: "reviews", key: "rating_count") {
              value
            }
            loox_reviews: metafield(namespace: "loox", key: "num_reviews") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_matched_edges = []
    has_next = True
    cursor = None
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        for edge in products_data["edges"]:
            node = edge["node"]
            count = 0
            
            rc = node.get("reviews_count")
            if rc and rc.get("value"):
                try:
                    count = int(rc["value"])
                except:
                    pass
                    
            if count == 0:
                loox = node.get("loox_reviews")
                if loox and loox.get("value"):
                    try:
                        count = int(loox["value"])
                    except:
                        pass
                        
            matched = (count > 0) if has_reviews else (count == 0)
            if matched:
                all_matched_edges.append(edge)
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_rich_description_status(has_rich: bool, sort_by="created_desc"):
    query = """
    query getProducts($after: String) {
      products(first: 50, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            rich_description: metafield(namespace: "custom", key: "rich_description") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_matched_edges = []
    has_next = True
    cursor = None
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        for edge in products_data["edges"]:
            node = edge["node"]
            rich_desc_field = node.get("rich_description")
            
            has_rich_desc = False
            if rich_desc_field and rich_desc_field.get("value"):
                val = rich_desc_field.get("value")
                match = re.search(r'<div\s+[^>]*class=["\'][^"\']*description-root[^"\']*["\'][^>]*>(.*?)</div>', val, re.IGNORECASE | re.DOTALL)
                if match:
                    inner_html = match.group(1)
                    if re.search(r'<[a-zA-Z]+', inner_html):
                        has_rich_desc = True
            
            matched = has_rich_desc if has_rich else not has_rich_desc
            if matched:
                all_matched_edges.append(edge)
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    all_matched_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_duplicate_asin(sort_by="created_desc"):
    query = """
    query getProducts($after: String) {
      products(first: 50, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            handle
            title
            descriptionHtml
            createdAt
            productType
            category {
              name
            }
            priceRangeV2 {
              minVariantPrice {
                amount
              }
            }
            options {
              name
            }
            collections(first: 20) {
              edges {
                node {
                  title
                }
              }
            }
            amazon_link: metafield(namespace: "custom", key: "amazon_link") {
              value
            }
            media(first: 50) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                  ... on Video {
                    id
                    preview {
                      image {
                        url
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    all_edges = []
    has_next = True
    cursor = None
    
    while has_next:
        variables = {}
        if cursor:
            variables["after"] = cursor
            
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        products_data = data["data"]["products"]
        all_edges.extend(products_data["edges"])
                
        page_info = products_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    asin_counts = {}
    for edge in all_edges:
        mf = edge["node"].get("amazon_link")
        if mf and mf.get("value"):
            val = mf["value"]
            asin = val.strip().upper()
            match = re.search(r'(?:/dp/|/gp/product/)([a-zA-Z0-9]+)', val)
            if match:
                asin = match.group(1).upper()
            if asin:
                asin_counts[asin] = asin_counts.get(asin, 0) + 1
                
    duplicate_edges = []
    for edge in all_edges:
        mf = edge["node"].get("amazon_link")
        if mf and mf.get("value"):
            val = mf["value"]
            asin = val.strip().upper()
            match = re.search(r'(?:/dp/|/gp/product/)([a-zA-Z0-9]+)', val)
            if match:
                asin = match.group(1).upper()
            if asin and asin_counts.get(asin, 0) > 1:
                duplicate_edges.append(edge)

    def get_sort_key(edge):
        if sort_by in ["price_asc", "price_desc"]:
            price_data = edge["node"].get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                return float(price_data["minVariantPrice"].get("amount", 0))
            return 0.0
        return edge["node"].get("createdAt", "")
        
    reverse_sort = sort_by in ["created_desc", "price_desc"]
    duplicate_edges.sort(key=get_sort_key, reverse=reverse_sort)
        
    return {
        "products": {
            "edges": duplicate_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(duplicate_edges)}
    }

@app.post("/update-token")
async def update_token(request: Request, access_token: str = Form(...)):
    global SHOPIFY_ADMIN_TOKEN, HEADERS
    new_token = access_token.strip()
    if new_token:
        SHOPIFY_ADMIN_TOKEN = new_token
        HEADERS["X-Shopify-Access-Token"] = new_token
        
        env_file = ".env"
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            token_found = False
            for i, line in enumerate(lines):
                if line.startswith("SHOPIFY_ADMIN_TOKEN="):
                    lines[i] = f"SHOPIFY_ADMIN_TOKEN={new_token}\n"
                    token_found = True
                    break
            
            if not token_found:
                lines.append(f"SHOPIFY_ADMIN_TOKEN={new_token}\n")
                
            with open(env_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
        else:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(f"SHOPIFY_ADMIN_TOKEN={new_token}\n")

    return RedirectResponse(url="/", status_code=303)

@app.get("/reviews", response_class=HTMLResponse)
async def get_reviews(request: Request):
    return templates.TemplateResponse(request=request, name="reviews.html", context={"request": request})

@app.get("/notes", response_class=HTMLResponse)
async def get_notes(request: Request):
    note_content = ""
    try:
        if os.path.exists("notes.txt"):
            with open("notes.txt", "r", encoding="utf-8") as f:
                note_content = f.read()
    except Exception as e:
        print(f"Error reading notes: {e}")
        
    return templates.TemplateResponse(request=request, name="notes.html", context={"request": request, "note_content": note_content})

@app.post("/notes")
async def save_notes(request: Request, note_content: str = Form(default="")):
    try:
        with open("notes.txt", "w", encoding="utf-8") as f:
            f.write(note_content)
        return {"status": "success", "message": "Đã lưu ghi chú thành công!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, after: str = None, before: str = None, filter_type: str = "handle_list", filter_value: str = None, sort_by: str = "created_desc", special_filter: str = ""):
    try:
        filter_query = None
        data = None
        
        reverse = True
        sort_key_graphql = "CREATED_AT"
        if sort_by == "price_asc":
            sort_key_graphql = "PRICE"
            reverse = False
        elif sort_by == "price_desc":
            sort_key_graphql = "PRICE"
            reverse = True
        elif sort_by == "created_asc":
            sort_key_graphql = "CREATED_AT"
            reverse = False
            
        if special_filter and special_filter in ["out_of_stock", "in_stock", "not_tracked"]:
            data = get_products_by_special_filter(special_filter, sort_by=sort_by)
        elif special_filter and special_filter in ["has_reviews", "no_reviews"]:
            data = get_products_by_review_status(special_filter == "has_reviews", sort_by=sort_by)
        elif special_filter and special_filter in ["has_rich", "no_rich"]:
            data = get_products_by_rich_description_status(special_filter == "has_rich", sort_by=sort_by)
        elif special_filter and special_filter == "duplicate_asin":
            data = get_products_by_duplicate_asin(sort_by=sort_by)
        elif filter_value and filter_type == "metafield_amazon_link":
            data = get_products_by_metafield_amazon_link(filter_value, sort_by=sort_by)
        elif filter_value and filter_type == "metafield_amazon_link_list":
            data = get_products_by_metafield_amazon_link_list(filter_value, sort_by=sort_by)
        elif filter_value and filter_type == "metafield_rich_description":
            data = get_products_by_metafield_rich_description(filter_value, sort_by=sort_by)
        elif filter_value and filter_type == "description":
            data = get_products_by_description(filter_value, sort_by=sort_by)
        elif filter_value and filter_type == "category":
            data = get_products_by_category(filter_value, sort_by=sort_by)
        elif filter_value and filter_type == "variant_option":
            data = get_products_by_variant_option(filter_value, sort_by=sort_by, exclude=False)
        elif filter_value and filter_type == "not_variant_option":
            data = get_products_by_variant_option(filter_value, sort_by=sort_by, exclude=True)
        elif filter_value and filter_type == "collection":
            data = get_products_by_collection(filter_value, sort_by=sort_by, after=after, before=before)
        else:
            if filter_value:
                if filter_type == "tag_list":
                    tags = [t.strip() for t in filter_value.split(",") if t.strip()]
                    if tags:
                        filter_query = " OR ".join([f"tag:{t}" for t in tags])
                elif filter_type == "title":
                    filter_query = f"title:*{filter_value}*"
                elif filter_type == "id":
                    filter_query = f"id:{filter_value}"
                elif filter_type == "id_list":
                    ids = [i.strip() for i in filter_value.split(",") if i.strip()]
                    if ids:
                        filter_query = " OR ".join([f"id:{i}" for i in ids])
                elif filter_type == "handle":
                    filter_query = f"handle:{filter_value}"
                elif filter_type == "handle_list":
                    handles = [h.strip() for h in filter_value.split(",") if h.strip()]
                    if handles:
                        filter_query = " OR ".join([f"handle:{h}" for h in handles])
                elif filter_type == "not_handle_list":
                    handles = [h.strip() for h in filter_value.split(",") if h.strip()]
                    if handles:
                        filter_query = " ".join([f"-handle:{h}" for h in handles])
                elif filter_type == "product_type":
                    filter_query = f"product_type:'{filter_value}'"
                    
            data = get_products(first=50, after=after, before=before, filter_query=filter_query, sort_key=sort_key_graphql, reverse=reverse)
            
        products_data = data.get("products", {})
        total_count = data.get("productsCount", {}).get("count", 0)
        
        products = []
        for edge in products_data.get("edges", []):
            node = edge["node"]
            media_urls = []
            for media_edge in node.get("media", {}).get("edges", []):
                media_node = media_edge["node"]
                if "image" in media_node and media_node["image"]:
                    media_urls.append(media_node["image"]["url"])
                elif "preview" in media_node and media_node["preview"] and media_node["preview"]["image"]:
                    media_urls.append(media_node["preview"]["image"]["url"])
            options = [opt["name"] for opt in node.get("options", [])]
            collections = [col_edge["node"]["title"] for col_edge in node.get("collections", {}).get("edges", [])]
            
            price = 0
            price_data = node.get("priceRangeV2")
            if price_data and price_data.get("minVariantPrice"):
                price = float(price_data["minVariantPrice"].get("amount", 0))
                
            asin = ""
            amz_link_node = node.get("amazon_link")
            if not amz_link_node and filter_type in ["metafield_amazon_link", "metafield_amazon_link_list"]:
                amz_link_node = node.get("metafield")
                
            if amz_link_node and amz_link_node.get("value"):
                match = re.search(r'(?:/dp/|/gp/product/)([a-zA-Z0-9]+)', amz_link_node.get("value"))
                if match:
                    asin = match.group(1)
                
            created_at_raw = node.get("createdAt", "")
            created_at_fmt = created_at_raw
            if created_at_raw:
                try:
                    # Parse format like 2026-07-24T09:16:24Z
                    dt = datetime.strptime(created_at_raw, "%Y-%m-%dT%H:%M:%SZ")
                    created_at_fmt = dt.strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    pass
                except Exception as e:
                    print(f"Error parsing date {created_at_raw}: {e}")
                
            category_name = node.get("category", {}).get("name", "") if node.get("category") else ""
            products.append({
                "id": node["id"].split("/")[-1],
                "handle": node["handle"],
                "title": node["title"],
                "productType": node.get("productType", ""),
                "category": category_name,
                "price": price,
                "description": node.get("descriptionHtml", ""),
                "createdAt": created_at_fmt,
                "options": options,
                "collections": collections,
                "media": media_urls,
                "asin": asin
            })
            
        page_info = products_data.get("pageInfo", {})
        
        return templates.TemplateResponse(request=request, name="index.html", context={
            "request": request, 
            "products": products,
            "total_count": total_count,
            "page_info": page_info,
            "filter_type": filter_type,
            "filter_value": filter_value or "",
            "sort_by": sort_by,
            "special_filter": special_filter,
            "error": None
        })
    except Exception as e:
        return templates.TemplateResponse(request=request, name="index.html", context={
            "request": request,
            "products": [],
            "total_count": 0,
            "page_info": {},
            "filter_type": filter_type,
            "filter_value": filter_value or "",
            "sort_by": sort_by,
            "special_filter": special_filter,
            "error": str(e)
        })

def get_product_by_handle(handle: str):
    query = """
    query getProductByHandle($handle: String!) {
      productByHandle(handle: $handle) {
        id
        title
        handle
        createdAt
        productType
        tags
        category {
          name
        }
        descriptionHtml
        seo {
          title
          description
        }
        options {
          name
          values
        }
        media(first: 50) {
          edges {
            node {
              ... on MediaImage {
                id
                image {
                  url
                }
              }
              ... on Video {
                id
                preview {
                  image {
                    url
                  }
                }
              }
            }
          }
        }
        metafields(first: 50) {
          edges {
            node {
              namespace
              key
              value
              type
            }
          }
        }
        variants(first: 250) {
          edges {
            node {
              title
              price
              compareAtPrice
            }
          }
        }
        productPublications(first: 20) {
          edges {
            node {
              channel {
                id
                name
              }
              isPublished
            }
          }
        }
      }
    }
    """
    
    variables = {"handle": handle}
    response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        print("GraphQL Errors:", data["errors"])
        return None
    return data["data"]["productByHandle"]

@app.get("/products/{product_handle}", response_class=HTMLResponse)
async def read_product(request: Request, product_handle: str):
    try:
        product_data = get_product_by_handle(product_handle)
        
        if not product_data:
            return templates.TemplateResponse(request=request, name="404.html", context={"request": request}, status_code=404)
            
        media_list = []
        for media_edge in product_data.get("media", {}).get("edges", []):
            media_node = media_edge["node"]
            media_id = media_node.get("id")
            if "image" in media_node and media_node["image"]:
                media_list.append({"id": media_id, "url": media_node["image"]["url"]})
            elif "preview" in media_node and media_node["preview"] and media_node["preview"]["image"]:
                media_list.append({"id": media_id, "url": media_node["preview"]["image"]["url"]})
                
        # Extract unique prices
        prices = set()
        for variant_edge in product_data.get("variants", {}).get("edges", []):
            price = variant_edge["node"].get("price")
            if price:
                prices.add(price)
        sorted_prices = sorted(list(prices), key=lambda x: float(x))
                
        # Extract metafields
        metafields = []
        for mf_edge in product_data.get("metafields", {}).get("edges", []):
            metafields.append(mf_edge["node"])
            
        created_at_raw = product_data.get("createdAt", "")
        created_at_fmt = created_at_raw
        if created_at_raw:
            try:
                dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                created_at_fmt = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass
                
        # Extract publications
        publications = []
        for pub_edge in product_data.get("productPublications", {}).get("edges", []):
            pub_node = pub_edge["node"]
            publications.append({
                "channel_id": pub_node.get("channel", {}).get("id"),
                "channel_name": pub_node.get("channel", {}).get("name"),
                "is_published": pub_node.get("isPublished", False)
            })
            
        product = {
            "id": product_data["id"].split("/")[-1],
            "title": product_data["title"],
            "handle": product_data["handle"],
            "created_at": created_at_fmt,
            "product_type": product_data.get("productType", ""),
            "category": product_data.get("category", {}).get("name", "") if product_data.get("category") else None,
            "tags": product_data.get("tags", []),
            "description": product_data.get("descriptionHtml", ""),
            "seo": product_data.get("seo", {}),
            "options": product_data.get("options", []),
            "media": media_list,
            "prices": sorted_prices,
            "metafields": metafields,
            "publications": publications
        }
        
        return templates.TemplateResponse(request=request, name="product.html", context={
            "request": request, 
            "product": product,
            "error": None
        })
    except Exception as e:
        return templates.TemplateResponse(request=request, name="product.html", context={
            "request": request,
            "product": None,
            "error": str(e)
        })

def get_all_collections():
    all_collections = []
    has_next_page = True
    cursor = None
    
    while has_next_page:
        query = """
        query getCollections($first: Int, $after: String) {
          collections(first: $first, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
                handle
                descriptionHtml
                image {
                  url
                }
                productsCount {
                  count
                }
              }
            }
          }
        }
        """
        variables = {"first": 100}
        if cursor:
            variables["after"] = cursor
            
        response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            print("GraphQL Errors:", data["errors"])
            break
            
        collections_data = data["data"]["collections"]
        for edge in collections_data.get("edges", []):
            node = edge["node"]
            all_collections.append({
                "id": node["id"].split("/")[-1],
                "handle": node["handle"],
                "title": node["title"],
                "description": node.get("descriptionHtml", ""),
                "image": node.get("image", {}).get("url") if node.get("image") else None,
                "products_count": node.get("productsCount", {}).get("count", 0) if node.get("productsCount") else 0
            })
            
        page_info = collections_data.get("pageInfo", {})
        has_next_page = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    return all_collections

@app.get("/collections", response_class=HTMLResponse)
async def read_collections(request: Request, 
                           sort_by: str = "count_desc", 
                           filter_mode: str = "all"):
    try:
        collections = get_all_collections()
        total_collections_count = len(collections)
        
        # 1. Filter
        if filter_mode == "empty":
            collections = [c for c in collections if c["products_count"] == 0]
        elif filter_mode == "not_empty":
            collections = [c for c in collections if c["products_count"] > 0]
            
        # 2. Sort
        if sort_by == "title_asc":
            collections.sort(key=lambda x: x["title"].lower())
        elif sort_by == "title_desc":
            collections.sort(key=lambda x: x["title"].lower(), reverse=True)
        elif sort_by == "count_asc":
            collections.sort(key=lambda x: x["products_count"])
        elif sort_by == "count_desc":
            collections.sort(key=lambda x: x["products_count"], reverse=True)
            
        return templates.TemplateResponse(request=request, name="collections.html", context={
            "request": request, 
            "collections": collections,
            "total_count": total_collections_count,
            "sort_by": sort_by,
            "filter_mode": filter_mode,
            "error": None
        })
    except Exception as e:
        return templates.TemplateResponse(request=request, name="collections.html", context={
            "request": request,
            "collections": [],
            "total_count": 0,
            "sort_by": sort_by,
            "filter_mode": filter_mode,
            "error": str(e)
        })

@app.get("/create", response_class=HTMLResponse)
async def create_product_form(request: Request):
    return templates.TemplateResponse(request=request, name="create_product.html", context={
        "request": request,
        "error": None,
        "success_message": None
    })

@app.post("/create", response_class=HTMLResponse)
async def create_product_submit(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    quantity: int = Form(1)
):
    try:
        if quantity < 1 or quantity > 50:
            raise ValueError("Số lượng phải từ 1 đến 50.")
            
        success_count = 0
        timestamp = int(time.time())
        
        for i in range(quantity):
            random_uuid = str(uuid.uuid4())
            handle = f"placeholder-handle-{timestamp}-{random_uuid}"
            
            mutation = """
            mutation productCreate($input: ProductInput!) {
              productCreate(input: $input) {
                product {
                  id
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
                    "title": title,
                    "handle": handle,
                    "descriptionHtml": description
                }
            }
            
            response = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                raise Exception(f"GraphQL Error: {data['errors']}")
                
            user_errors = data.get("data", {}).get("productCreate", {}).get("userErrors", [])
            if user_errors:
                raise Exception(f"Shopify Error: {user_errors[0]['message']}")
                
            success_count += 1
            
        return templates.TemplateResponse(request=request, name="create_product.html", context={
            "request": request,
            "error": None,
            "success_message": f"Đã tạo thành công {success_count} sản phẩm!"
        })
        
    except Exception as e:
        return templates.TemplateResponse(request=request, name="create_product.html", context={
            "request": request,
            "error": str(e),
            "success_message": None
        })

def resolve_product_id(identifier: str, id_types: list) -> str:
    ident = identifier.strip()
    if not ident:
        return None
    if ident.startswith("gid://shopify/Product/"):
        return ident
    if "id" in id_types and "handle" not in id_types:
        return f"gid://shopify/Product/{ident}"
    if "handle" in id_types and "id" not in id_types:
        prod = get_product_by_handle(ident)
        return prod["id"] if prod else None
    if ident.isdigit():
        return f"gid://shopify/Product/{ident}"
    prod = get_product_by_handle(ident)
    if prod:
        return prod["id"]
    return f"gid://shopify/Product/{ident}"

def get_product_options_by_id(product_id: str):
    query = """
    query getProductOptions($id: ID!) {
      product(id: $id) {
        id
        title
        options {
          id
          name
          values
          optionValues {
            id
            name
          }
        }
      }
    }
    """
    res = requests.post(GRAPHQL_URL, json={"query": query, "variables": {"id": product_id}}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if "errors" in data or not data.get("data", {}).get("product"):
        return None
    return data["data"]["product"]


def create_new_variant_options_for_product(product_id: str, option_pairs: list):
    product = get_product_options_by_id(product_id)
    if not product:
        return False, "Không tìm thấy sản phẩm trên Shopify"
    existing_opts = product.get("options", [])
    existing_names = [o["name"].lower() for o in existing_opts]
    
    options_to_create = []
    for opt_name, opt_values in option_pairs:
        if opt_name.lower() in existing_names:
            return False, f"Variant option '{opt_name}' đã tồn tại"
        
        options_to_create.append({
            "name": opt_name,
            "values": [{"name": v} for v in opt_values]
        })
        
    if not options_to_create:
        return True, "Không có option nào hợp lệ để tạo"
        
    mutation = '''
    mutation productOptionsCreate($productId: ID!, $options: [OptionCreateInput!]!) {
      productOptionsCreate(productId: $productId, options: $options, variantStrategy: CREATE) {
        product {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    '''
    variables = {
        "productId": product_id,
        "options": options_to_create
    }
    res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        return False, f"GraphQL Error: {data['errors'][0]['message']}"
    user_errs = data.get("data", {}).get("productOptionsCreate", {}).get("userErrors", [])
    if user_errs:
        return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
        
    return True, f"Đã thêm mới thành công {len(options_to_create)} option"

def add_variant_options_to_product(product_id: str, option_pairs: list, append: bool = False):
    product = get_product_options_by_id(product_id)
    if not product:
        return False, "Không tìm thấy sản phẩm trên Shopify"
    existing_opts = product.get("options", [])
    for opt_name, opt_values in option_pairs:
        existing_opt = next((o for o in existing_opts if o["name"].lower() == opt_name.lower()), None)
        if existing_opt is None:
            return False, f"Không tìm thấy variant option '{opt_name}' trên sản phẩm"
        else:
            existing_vals_map = {v["name"]: v["id"] for v in existing_opt.get("optionValues", [])}
            new_vals = [v for v in opt_values if v not in existing_vals_map]
            if append:
                vals_to_delete = []
            else:
                vals_to_delete = [v_id for v_name, v_id in existing_vals_map.items() if v_name not in opt_values]
            
            if new_vals or vals_to_delete:
                mutation = """
                mutation productOptionUpdate($productId: ID!, $option: OptionUpdateInput!, $optionValuesToAdd: [OptionValueCreateInput!], $optionValuesToDelete: [ID!]) {
                  productOptionUpdate(productId: $productId, option: $option, optionValuesToAdd: $optionValuesToAdd, optionValuesToDelete: $optionValuesToDelete, variantStrategy: MANAGE) {
                    product {
                      id
                      options { id name values }
                    }
                    userErrors { field message }
                  }
                }
                """
                variables = {
                    "productId": product_id,
                    "option": {"id": existing_opt["id"], "name": existing_opt["name"]},
                }
                if new_vals:
                    variables["optionValuesToAdd"] = [{"name": v} for v in new_vals]
                if vals_to_delete:
                    variables["optionValuesToDelete"] = vals_to_delete
                    
                res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
                res.raise_for_status()
                data = res.json()
                if "errors" in data:
                    return False, f"GraphQL Error: {data['errors'][0]['message']}"
                user_errs = data.get("data", {}).get("productOptionUpdate", {}).get("userErrors", [])
                if user_errs:
                    return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
                if data.get("data", {}).get("productOptionUpdate", {}).get("product"):
                    existing_opts = data["data"]["productOptionUpdate"]["product"].get("options", [])
    
    # Đảm bảo tạo đầy đủ tổ hợp các variant
    import itertools
    ensure_success, ensure_msg = ensure_full_variant_combinations(product_id)
    if not ensure_success:
        return False, f"Đã thêm Option nhưng lỗi tạo Variant: {ensure_msg}"
        
    return True, f"Đã thêm/cập nhật thành công {len(option_pairs)} variant options cho '{product.get('title', product_id)}'"

def ensure_full_variant_combinations(product_id: str):
    import itertools
    query = """
    query getProductOptionsAndVariants($id: ID!) {
      product(id: $id) {
        options {
          name
          optionValues {
            name
          }
        }
        variants(first: 250) {
          edges {
            node {
              id
              selectedOptions {
                name
                value
              }
            }
          }
        }
      }
    }
    """
    res = requests.post(GRAPHQL_URL, json={"query": query, "variables": {"id": product_id}}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if "errors" in data or not data.get("data", {}).get("product"):
        return False, "Lỗi khi lấy thông tin sản phẩm"
    
    product = data["data"]["product"]
    options = product.get("options", [])
    
    option_names = []
    option_values_lists = []
    for opt in options:
        opt_name = opt["name"]
        vals = [v["name"] for v in opt.get("optionValues", [])]
        if vals:
            option_names.append(opt_name)
            option_values_lists.append(vals)
            
    if not option_values_lists:
        return True, "Không có option values nào"
        
    all_combinations = list(itertools.product(*option_values_lists))
    
    variants = product.get("variants", {}).get("edges", [])
    existing_combinations = set()
    for edge in variants:
        node = edge["node"]
        sel_opts = node.get("selectedOptions", [])
        val_dict = {o["name"]: o["value"] for o in sel_opts}
        comb = tuple(val_dict.get(n, "") for n in option_names)
        existing_combinations.add(comb)
        
    missing_combinations = [c for c in all_combinations if c not in existing_combinations]
    
    if not missing_combinations:
        return True, "Không có biến thể nào thiếu"
        
    def chunker(seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))
        
    for chunk in chunker(missing_combinations, 250):
        variants_input = []
        for comb in chunk:
            opt_vals = []
            for i, opt_name in enumerate(option_names):
                opt_vals.append({"optionName": opt_name, "name": comb[i]})
            # Handle option value properly
            variants_input.append({"optionValues": opt_vals})
            
        mutation = """
        mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkCreate(productId: $productId, variants: $variants) {
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "productId": product_id,
            "variants": variants_input
        }
        res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        user_errs = data.get("data", {}).get("productVariantsBulkCreate", {}).get("userErrors", [])
        if user_errs:
            return False, f"Lỗi tạo biến thể: {user_errs[0]['message']}"
            
    return True, f"Đã tạo thêm {len(missing_combinations)} biến thể."

def delete_option_value_from_product(product_id: str, option_name: str, option_value: str):
    product = get_product_options_by_id(product_id)
    if not product:
        return False, "Không tìm thấy sản phẩm trên Shopify"
        
    options = product.get("options", [])
    target_option = next((o for o in options if o["name"] == option_name), None)
    if not target_option:
        return False, f"Không tìm thấy option '{option_name}'"
        
    target_value = next((v for v in target_option.get("optionValues", []) if v["name"] == option_value), None)
    if not target_value:
        return False, f"Không tìm thấy giá trị '{option_value}' trong option '{option_name}'"
        
    mutation = """
    mutation productOptionUpdate($productId: ID!, $option: OptionUpdateInput!, $optionValuesToDelete: [ID!]) {
      productOptionUpdate(productId: $productId, option: $option, optionValuesToDelete: $optionValuesToDelete, variantStrategy: MANAGE) {
        product {
          id
          options { name values }
        }
        userErrors { field message }
      }
    }
    """
    variables = {
        "productId": product_id,
        "option": {"id": target_option["id"], "name": target_option["name"]},
        "optionValuesToDelete": [target_value["id"]]
    }
    res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        return False, f"GraphQL Error: {data['errors'][0]['message']}"
    user_errs = data.get("data", {}).get("productOptionUpdate", {}).get("userErrors", [])
    if user_errs:
        return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
    return True, f"Đã xóa giá trị '{option_value}' khỏi '{option_name}' cho '{product.get('title', product_id)}'"


def update_product_type(product_id: str, new_type: str):
    mutation = '''
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          productType
        }
        userErrors {
          field
          message
        }
      }
    }
    '''
    variables = {
        "input": {
            "id": product_id,
            "productType": new_type
        }
    }
    res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        return False, f"GraphQL Error: {data['errors'][0]['message']}"
    user_errs = data.get("data", {}).get("productUpdate", {}).get("userErrors", [])
    if user_errs:
        return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
    return True, "Cập nhật Product Type thành công"

def delete_option_from_product(product_id: str, option_name: str):
    product = get_product_options_by_id(product_id)
    if not product:
        return False, "Không tìm thấy sản phẩm trên Shopify"
        
    options = product.get("options", [])
    target_option = next((o for o in options if o["name"] == option_name), None)
    if not target_option:
        return False, f"Không tìm thấy option '{option_name}'"
        
    mutation = """
    mutation productOptionsDelete($productId: ID!, $options: [ID!]!) {
      productOptionsDelete(productId: $productId, options: $options, strategy: POSITION) {
        product {
          id
          options { name }
        }
        userErrors { field message }
      }
    }
    """
    variables = {
        "productId": product_id,
        "options": [target_option["id"]]
    }
    res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        return False, f"GraphQL Error: {data['errors'][0]['message']}"
    user_errs = data.get("data", {}).get("productOptionsDelete", {}).get("userErrors", [])
    if user_errs:
        return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
    return True, f"Đã xóa thành công option '{option_name}' cho '{product.get('title', product_id)}'"

def rename_option_in_product(product_id: str, old_name: str, new_name: str):
    product = get_product_options_by_id(product_id)
    if not product:
        return False, "Không tìm thấy sản phẩm trên Shopify"
        
    options = product.get("options", [])
    target_option = next((o for o in options if o["name"].lower() == old_name.lower()), None)
    if not target_option:
        return False, f"Không tìm thấy option '{old_name}'"
        
    mutation = """
    mutation productOptionUpdate($productId: ID!, $option: OptionUpdateInput!) {
      productOptionUpdate(productId: $productId, option: $option, variantStrategy: MANAGE) {
        product {
          id
          options { name }
        }
        userErrors { field message }
      }
    }
    """
    variables = {
        "productId": product_id,
        "option": {"id": target_option["id"], "name": new_name}
    }
    res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        return False, f"GraphQL Error: {data['errors'][0]['message']}"
    user_errs = data.get("data", {}).get("productOptionUpdate", {}).get("userErrors", [])
    if user_errs:
        return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
    return True, f"Đã đổi tên '{old_name}' thành '{new_name}' cho '{product.get('title', product_id)}'"

def is_ajax_request(request: Request) -> bool:
    accept = request.headers.get("accept", "").lower()
    x_req = request.headers.get("x-requested-with", "").lower()
    sec_dest = request.headers.get("sec-fetch-dest", "").lower()
    return "application/json" in accept or x_req == "xmlhttprequest" or sec_dest == "empty"

@app.get("/edit-variants", response_class=HTMLResponse)
async def edit_variants_form(request: Request):
    return templates.TemplateResponse(request=request, name="edit_variants.html", context={
        "request": request,
        "error": None,
        "success_message": None
    })

@app.post("/edit-variants")
async def edit_variants_submit(request: Request):
    try:
        form = await request.form()
        identifiers_raw = form.get("identifiers", "")
        id_types = form.getlist("id_type")
        option_names = form.getlist("option_names[]")
        option_values = form.getlist("option_values[]")
        new_option_names = form.getlist("new_option_names[]")
        new_option_values = form.getlist("new_option_values[]")
        delete_option_name = form.get("delete_option_name", "").strip()
        rename_old_option = form.get("rename_old_option", "").strip()
        rename_new_option = form.get("rename_new_option", "").strip()

        raw_list = re.split(r'[\r\n,]+', identifiers_raw)
        identifiers = [i.strip() for i in raw_list if i.strip()]
        if not identifiers:
            msg = "Danh sách sản phẩm trống hoặc không hợp lệ"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})

        action_type = form.get("action_type", "add")

        option_pairs = []
        if action_type in ("add", "add_new"):
            delete_option_name = ""
            names_to_use = new_option_names if action_type == "add_new" else option_names
            values_to_use = new_option_values if action_type == "add_new" else option_values
            for name, vals_str in zip(names_to_use, values_to_use):
                name_clean = name.strip()
                if not name_clean:
                    continue
                vals_raw = re.split(r'[,;]', vals_str)
                vals_clean = [v.strip() for v in vals_raw if v.strip()]
                if not vals_clean:
                    continue
                option_pairs.append((name_clean, vals_clean))
        elif action_type == "delete":
            option_pairs = []

        if action_type in ("add", "add_new") and not option_pairs:
            msg = "Vui lòng nhập option cần thêm"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})
            
        if action_type == "delete" and not delete_option_name:
            msg = "Vui lòng nhập option cần xóa"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})
            
        if action_type == "rename" and (not rename_old_option or not rename_new_option):
            msg = "Vui lòng nhập đầy đủ tên Option cũ và mới"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})

        success_count = 0
        details = []

        for ident in identifiers:
            prod_id = resolve_product_id(ident, id_types)
            if not prod_id:
                details.append({"identifier": ident, "status": "FAIL", "message": "Không tìm thấy định danh hoặc handle hợp lệ"})
                continue

            msgs = []
            has_error = False

            if action_type == "delete" and delete_option_name:
                del_success, del_msg = delete_option_from_product(prod_id, delete_option_name)
                msgs.append(del_msg)
                if not del_success:
                    has_error = True


            if action_type == "add_new" and option_pairs:
                add_new_success, add_new_msg = create_new_variant_options_for_product(prod_id, option_pairs)
                msgs.append(add_new_msg)
                if not add_new_success:
                    has_error = True

            if action_type == "add" and option_pairs:
                add_success, add_msg = add_variant_options_to_product(prod_id, option_pairs)
                msgs.append(add_msg)
                if not add_success:
                    has_error = True
                    
            if action_type == "rename" and rename_old_option and rename_new_option:
                rename_success, rename_msg = rename_option_in_product(prod_id, rename_old_option, rename_new_option)
                msgs.append(rename_msg)
                if not rename_success:
                    has_error = True

            if has_error:
                details.append({"identifier": ident, "status": "FAIL", "message": " | ".join(msgs)})
            else:
                success_count += 1
                details.append({"identifier": ident, "status": "OK", "message": " | ".join(msgs)})

        msg_summary = f"Đã thực thi xong: Thành công {success_count}/{len(identifiers)} sản phẩm."
        if is_ajax_request(request):
            import json
            res_data = {
                "success": success_count > 0,
                "message": msg_summary,
                "details": details
            }
            return HTMLResponse(content=json.dumps(res_data, ensure_ascii=False), media_type="application/json")
            
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={
            "request": request,
            "error": None if success_count > 0 else msg_summary,
            "success_message": msg_summary if success_count > 0 else None
        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": str(e), "success_message": None})

@app.post("/add-option-value")
async def add_option_value_submit(request: Request):
    try:
        form = await request.form()
        identifiers_raw = form.get("identifiers", "")
        id_types = form.getlist("id_type")
        option_name = form.get("add_option_name", "").strip()
        option_values_raw = form.get("add_option_values", "")

        raw_list = re.split(r'[\r\n,]+', identifiers_raw)
        identifiers = [i.strip() for i in raw_list if i.strip()]
        
        option_values = [v.strip() for v in option_values_raw.split(";") if v.strip()]

        if not identifiers:
            msg = "Danh sách sản phẩm trống"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})
            
        if not option_name or not option_values:
            msg = "Vui lòng nhập Tên Option và Các Giá trị cần thêm"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})

        success_count = 0
        details = []

        for ident in identifiers:
            prod_id = resolve_product_id(ident, id_types)
            if not prod_id:
                details.append({"identifier": ident, "status": "FAIL", "message": "Không tìm thấy định danh hoặc handle hợp lệ"})
                continue

            success, msg = add_variant_options_to_product(prod_id, [(option_name, option_values)], append=True)
            if success:
                success_count += 1
                details.append({"identifier": ident, "status": "OK", "message": msg})
            else:
                details.append({"identifier": ident, "status": "FAIL", "message": msg})

        msg_summary = f"Đã thực thi xong: Thành công {success_count}/{len(identifiers)} sản phẩm."
        if is_ajax_request(request):
            import json
            res_data = {
                "success": success_count > 0,
                "message": msg_summary,
                "details": details
            }
            return HTMLResponse(content=json.dumps(res_data, ensure_ascii=False), media_type="application/json")
            
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={
            "request": request,
            "error": None if success_count > 0 else msg_summary,
            "success_message": msg_summary if success_count > 0 else None
        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": str(e), "success_message": None})

@app.post("/delete-option-value")
async def delete_option_value_submit(request: Request):
    try:
        form = await request.form()
        identifiers_raw = form.get("identifiers", "")
        id_types = form.getlist("id_type")
        option_name = form.get("option_name", "").strip()
        option_value = form.get("option_value", "").strip()

        raw_list = re.split(r'[\r\n,]+', identifiers_raw)
        identifiers = [i.strip() for i in raw_list if i.strip()]
        
        if not identifiers:
            msg = "Danh sách sản phẩm trống"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})
            
        if not option_name or not option_value:
            msg = "Vui lòng nhập Tên Option và Giá trị cần xóa"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})

        success_count = 0
        details = []

        for ident in identifiers:
            prod_id = resolve_product_id(ident, id_types)
            if not prod_id:
                details.append({"identifier": ident, "status": "FAIL", "message": "Không tìm thấy định danh hoặc handle hợp lệ"})
                continue

            success, msg = delete_option_value_from_product(prod_id, option_name, option_value)
            if success:
                success_count += 1
                details.append({"identifier": ident, "status": "OK", "message": msg})
            else:
                details.append({"identifier": ident, "status": "FAIL", "message": msg})

        msg_summary = f"Đã thực thi xong: Thành công {success_count}/{len(identifiers)} sản phẩm."
        if is_ajax_request(request):
            import json
            res_data = {
                "success": success_count > 0,
                "message": msg_summary,
                "details": details
            }
            return HTMLResponse(content=json.dumps(res_data, ensure_ascii=False), media_type="application/json")
            
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={
            "request": request,
            "error": None if success_count > 0 else msg_summary,
            "success_message": msg_summary if success_count > 0 else None
        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": str(e), "success_message": None})

@app.post("/delete-option")
async def delete_option_submit(request: Request):
    try:
        form = await request.form()
        identifiers_raw = form.get("identifiers", "")
        id_types = form.getlist("id_type")
        option_name = form.get("option_name", "").strip()

        raw_list = re.split(r'[\r\n,]+', identifiers_raw)
        identifiers = [i.strip() for i in raw_list if i.strip()]
        
        if not identifiers:
            msg = "Danh sách sản phẩm trống"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})
            
        if not option_name:
            msg = "Vui lòng nhập tên Variant Option cần xóa"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})

        success_count = 0
        details = []

        for ident in identifiers:
            prod_id = resolve_product_id(ident, id_types)
            if not prod_id:
                details.append({"identifier": ident, "status": "FAIL", "message": "Không tìm thấy định danh hoặc handle hợp lệ"})
                continue

            success, msg = delete_option_from_product(prod_id, option_name)
            if success:
                success_count += 1
                details.append({"identifier": ident, "status": "OK", "message": msg})
            else:
                details.append({"identifier": ident, "status": "FAIL", "message": msg})

        msg_summary = f"Đã thực thi xong: Thành công {success_count}/{len(identifiers)} sản phẩm."
        if is_ajax_request(request):
            import json
            res_data = {
                "success": success_count > 0,
                "message": msg_summary,
                "details": details
            }
            return HTMLResponse(content=json.dumps(res_data, ensure_ascii=False), media_type="application/json")
            
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={
            "request": request,
            "error": None if success_count > 0 else msg_summary,
            "success_message": msg_summary if success_count > 0 else None
        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": str(e), "success_message": None})

@app.get("/api/taxonomy")
async def api_taxonomy(request: Request, search: str = "", cursor: str = None):
    try:
        import json
        query_args = "$first: Int!, $after: String"
        taxonomy_args = "first: $first, after: $after"
        
        if search:
            query_args += ", $search: String"
            taxonomy_args += ", search: $search"
            # Keep query_vars mapping 'query' to search if that's what taxonomyNodes used,
            # but wait, the variable in query_vars is "query": "B", let's change it to "search"
            
        # We need to make sure query_vars matches the declared variables
        query_vars = {"first": 50}
        if cursor:
            query_vars["after"] = cursor
        if search:
            query_vars["search"] = search
            
        query = f'''
        query getTaxonomyNodes({query_args}) {{
          taxonomyNodes({taxonomy_args}) {{
            pageInfo {{
              hasNextPage
              endCursor
            }}
            edges {{
              node {{
                id
                name
                fullName
              }}
            }}
          }}
        }}
        '''
        
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": query_vars}, headers=HEADERS)
        if res.status_code == 200 and "errors" not in res.json():
            return HTMLResponse(content=json.dumps({"success": True, "data": res.json().get("data", {}).get("taxonomyNodes", {})}), media_type="application/json")
            
        error_msg_1 = str(res.json().get("errors", []))
            
        # Fallback to taxonomy if taxonomyNodes is not available
        query_fallback = f'''
        query getTaxonomyNodes({query_args}) {{
          taxonomy {{
            categories({taxonomy_args}) {{
              pageInfo {{
                hasNextPage
                endCursor
              }}
              edges {{
                node {{
                  id
                  name
                  fullName
                }}
              }}
            }}
          }}
        }}
        '''
        res2 = requests.post(GRAPHQL_URL, json={"query": query_fallback, "variables": query_vars}, headers=HEADERS)
        res2.raise_for_status()
        data = res2.json()
        if "errors" in data:
            error2_str = str(data["errors"])
            return HTMLResponse(content=json.dumps({"success": False, "message": f"Query 1: {error_msg_1} | Query 2: {error2_str}"}), media_type="application/json")
            
        return HTMLResponse(content=json.dumps({"success": True, "data": data.get("data", {}).get("taxonomy", {}).get("categories", {})}), media_type="application/json")
    except Exception as e:
        import traceback
        traceback.print_exc()
        import json
        return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}), media_type="application/json")

def add_tags_to_product(product_id: str, tags: list):
    mutation = """
    mutation tagsAdd($id: ID!, $tags: [String!]!) {
      tagsAdd(id: $id, tags: $tags) {
        node {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    variables = {
        "id": product_id,
        "tags": tags
    }
    res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        return False, f"GraphQL Error: {data['errors'][0]['message']}"
    user_errs = data.get("data", {}).get("tagsAdd", {}).get("userErrors", [])
    if user_errs:
        return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
    return True, f"Đã thêm tags thành công"

@app.post("/add-tags")
async def add_tags_submit(request: Request):
    try:
        form = await request.form()
        identifiers_raw = form.get("identifiers", "")
        id_types = form.getlist("id_type")
        tags_raw = form.get("tags", "")

        raw_list = re.split(r'[\r\n,]+', identifiers_raw)
        identifiers = [i.strip() for i in raw_list if i.strip()]
        
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        if not identifiers:
            msg = "Danh sách sản phẩm trống"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})
            
        if not tags:
            msg = "Danh sách tags trống"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})

        success_count = 0
        details = []

        for ident in identifiers:
            prod_id = resolve_product_id(ident, id_types)
            if not prod_id:
                details.append({"identifier": ident, "status": "FAIL", "message": "Không tìm thấy định danh hoặc handle hợp lệ"})
                continue

            success, msg = add_tags_to_product(prod_id, tags)
            if success:
                success_count += 1
                details.append({"identifier": ident, "status": "OK", "message": msg})
            else:
                details.append({"identifier": ident, "status": "FAIL", "message": msg})

        msg_summary = f"Đã thực thi xong: Thành công {success_count}/{len(identifiers)} sản phẩm."
        if is_ajax_request(request):
            import json
            res_data = {
                "success": success_count > 0,
                "message": msg_summary,
                "details": details
            }
            return HTMLResponse(content=json.dumps(res_data, ensure_ascii=False), media_type="application/json")
            
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={
            "request": request,
            "error": None if success_count > 0 else msg_summary,
            "success_message": msg_summary if success_count > 0 else None
        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": str(e), "success_message": None})


def get_publications_map():
    query = """
    query {
      publications(first: 20) {
        edges {
          node {
            id
            name
          }
        }
      }
    }
    """
    res = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    pub_map = {}
    if "data" in data and "publications" in data["data"]:
        for edge in data["data"]["publications"]["edges"]:
            node = edge["node"]
            pub_map[node["name"]] = node["id"]
    return pub_map

def update_product_channels(prod_id: str, desired_states: dict, pub_map: dict):
    publish_inputs = []
    unpublish_inputs = []
    
    for channel_name, should_publish in desired_states.items():
        if channel_name in pub_map:
            pub_id = pub_map[channel_name]
            if should_publish:
                publish_inputs.append({"publicationId": pub_id})
            else:
                unpublish_inputs.append({"publicationId": pub_id})
                
    results = []
    
    if publish_inputs:
        pub_query = """
        mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
          publishablePublish(id: $id, input: $input) {
            userErrors {
              message
            }
          }
        }
        """
        res = requests.post(GRAPHQL_URL, json={"query": pub_query, "variables": {"id": prod_id, "input": publish_inputs}}, headers=HEADERS)
        data = res.json()
        user_errs = data.get("data", {}).get("publishablePublish", {}).get("userErrors", [])
        if user_errs:
            results.append(f"Lỗi Bật: {user_errs[0]['message']}")
            
    if unpublish_inputs:
        unpub_query = """
        mutation publishableUnpublish($id: ID!, $input: [PublicationInput!]!) {
          publishableUnpublish(id: $id, input: $input) {
            userErrors {
              message
            }
          }
        }
        """
        res = requests.post(GRAPHQL_URL, json={"query": unpub_query, "variables": {"id": prod_id, "input": unpublish_inputs}}, headers=HEADERS)
        data = res.json()
        user_errs = data.get("data", {}).get("publishableUnpublish", {}).get("userErrors", [])
        if user_errs:
            results.append(f"Lỗi Tắt: {user_errs[0]['message']}")
            
    if results:
        return False, " | ".join(results)
    return True, "Cập nhật channel thành công"


@app.post("/edit-channels")
async def edit_channels_submit(request: Request):
    try:
        form = await request.form()
        identifiers_raw = form.get("identifiers", "")
        id_types = form.getlist("id_type")
        
        channel_online = form.get("channel_online") == "on"
        channel_pos = form.get("channel_pos") == "on"
        channel_headless = form.get("channel_headless") == "on"
        channel_inbox = form.get("channel_inbox") == "on"

        raw_list = re.split(r'[\r\n,]+', identifiers_raw)
        identifiers = [i.strip() for i in raw_list if i.strip()]

        if not identifiers:
            msg = "Danh sách sản phẩm trống"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})
            
        success_count = 0
        details = []
        
        pub_map = get_publications_map()
        
        desired_states = {
            "Online Store": channel_online,
            "Point of Sale": channel_pos,
            "Wrydeco Headless": channel_headless,
            "Inbox": channel_inbox
        }

        for ident in identifiers:
            prod_id = resolve_product_id(ident, id_types)
            if not prod_id:
                details.append({"identifier": ident, "status": "FAIL", "message": "Không tìm thấy định danh hoặc handle hợp lệ"})
                continue

            success, msg = update_product_channels(prod_id, desired_states, pub_map)
            if success:
                success_count += 1
                details.append({"identifier": ident, "status": "OK", "message": msg})
            else:
                details.append({"identifier": ident, "status": "FAIL", "message": msg})

        msg_summary = f"Đã thực thi xong: Thành công {success_count}/{len(identifiers)} sản phẩm."
        if is_ajax_request(request):
            import json
            res_data = {
                "success": success_count > 0,
                "message": msg_summary,
                "details": details
            }
            return HTMLResponse(content=json.dumps(res_data, ensure_ascii=False), media_type="application/json")
            
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={
            "request": request,
            "error": None if success_count > 0 else msg_summary,
            "success_message": msg_summary if success_count > 0 else None
        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": str(e), "success_message": None})

@app.post("/edit-meta-info")
async def edit_meta_info(request: Request):
    try:
        form_data = await request.form()
        identifiers_str = form_data.get("identifiers", "")
        id_types = form_data.getlist("id_type")
        action_type = form_data.get("action_type")
        product_type = form_data.get("product_type", "").strip()

        identifiers = [x.strip() for x in identifiers_str.replace(",", "\n").split("\n") if x.strip()]
        if not identifiers or not id_types:
            msg = "Vui lòng nhập định danh sản phẩm và chọn loại ID."
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": msg, "success_message": None})

        success_count = 0
        details = []

        for ident in identifiers:
            prod_id = resolve_product_id(ident, id_types)
            if not prod_id:
                details.append({"identifier": ident, "status": "FAIL", "message": "Không tìm thấy định danh hoặc handle hợp lệ"})
                continue

            msgs = []
            has_error = False

            tags = [t.strip() for t in form_data.get("tags", "").split(",") if t.strip()]

            if product_type:
                upd_success, upd_msg = update_product_type(prod_id, product_type)
                msgs.append(upd_msg)
                if not upd_success:
                    has_error = True
            
            if tags:
                tag_success, tag_msg = add_tags_to_product(prod_id, tags)
                msgs.append(tag_msg)
                if not tag_success:
                    has_error = True
                    
            if not product_type and not tags:
                msgs.append("Không có thông tin nào được cập nhật")
                has_error = True

            if has_error:
                details.append({"identifier": ident, "status": "FAIL", "message": " | ".join(msgs)})
            else:
                success_count += 1
                details.append({"identifier": ident, "status": "OK", "message": " | ".join(msgs)})

        msg_summary = f"Đã thực thi xong: Thành công {success_count}/{len(identifiers)} sản phẩm."
        if is_ajax_request(request):
            import json
            res_data = {
                "success": success_count > 0,
                "message": msg_summary,
                "details": details
            }
            return HTMLResponse(content=json.dumps(res_data, ensure_ascii=False), media_type="application/json")
            
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={
            "request": request,
            "error": None if success_count > 0 else msg_summary,
            "success_message": msg_summary if success_count > 0 else None
        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse(request=request, name="edit_variants.html", context={"request": request, "error": str(e), "success_message": None})

@app.post("/internal-reorder-media")
async def internal_reorder_media(request: Request):
    try:
        import json
        data = await request.json()
        product_id = data.get("product_id")
        moves = data.get("moves")
        
        if not product_id or not moves:
            return HTMLResponse(content=json.dumps({"success": False, "message": "Thiếu dữ liệu"}), media_type="application/json")
            
        if not str(product_id).startswith("gid://"):
            product_id = f"gid://shopify/Product/{product_id}"
            
        mutation = '''
        mutation productReorderMedia($id: ID!, $moves: [MoveInput!]!) {
          productReorderMedia(id: $id, moves: $moves) {
            userErrors {
              field
              message
            }
          }
        }
        '''
        variables = {
            "id": product_id,
            "moves": moves
        }
        
        response = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
        response.raise_for_status()
        result = response.json()
        
        if "errors" in result:
            return HTMLResponse(content=json.dumps({"success": False, "message": str(result["errors"])}), media_type="application/json")
            
        user_errors = result.get("data", {}).get("productReorderMedia", {}).get("userErrors", [])
        if user_errors:
            msg = ", ".join([e.get("message", "") for e in user_errors])
            return HTMLResponse(content=json.dumps({"success": False, "message": msg}), media_type="application/json")
            
        return HTMLResponse(content=json.dumps({"success": True}), media_type="application/json")
    except Exception as e:
        import traceback
        traceback.print_exc()
        import json
        return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}), media_type="application/json")

@app.post("/internal-edit-product")
async def internal_edit_product(request: Request):
    try:
        import json
        form = await request.form()
        product_id = form.get("product_id")
        target_field = form.get("target_field")
        new_value = form.get("new_value")

        if not product_id or not target_field or not new_value:
            return HTMLResponse(content=json.dumps({"success": False, "message": "Thiếu dữ liệu"}), media_type="application/json")
            
        if not str(product_id).startswith("gid://"):
            product_id = f"gid://shopify/Product/{product_id}"

        if target_field == "productTitle":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                  title
                }
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "title": new_value
                }
            }
        elif target_field == "productHandle":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                  handle
                }
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "handle": new_value
                }
            }
        elif target_field == "productType":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                  productType
                }
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "productType": new_value
                }
            }
        elif target_field == "tags":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                  tags
                }
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "tags": [t.strip() for t in new_value.split(",") if t.strip()]
                }
            }
        elif target_field == "productCategory":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                }
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "productCategory": {
                        "productTaxonomyNodeId": new_value
                    }
                }
            }
        elif target_field == "amazonLink":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                }
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "metafields": [
                        {
                            "namespace": "custom",
                            "key": "amazon_link",
                            "value": new_value,
                            "type": "single_line_text_field"
                        }
                    ]
                }
            }
        elif target_field == "descriptionHtml":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product { id }
                userErrors { field message }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "descriptionHtml": new_value
                }
            }
        elif target_field == "seoTitle":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product { id }
                userErrors { field message }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "seo": { "title": new_value }
                }
            }
        elif target_field == "seoDescription":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product { id }
                userErrors { field message }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "seo": { "description": new_value }
                }
            }
        elif target_field.startswith("metafield:"):
            parts = target_field.split(":")
            if len(parts) >= 4:
                mf_namespace = parts[1]
                mf_key = parts[2]
                mf_type = parts[3]
            else:
                return HTMLResponse(content=json.dumps({"success": False, "message": "Sai định dạng metafield"}), media_type="application/json")
                
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product { id }
                userErrors { field message }
              }
            }
            '''
            variables = {
                "input": {
                    "id": product_id,
                    "metafields": [
                        {
                            "namespace": mf_namespace,
                            "key": mf_key,
                            "value": new_value,
                            "type": mf_type
                        }
                    ]
                }
            }
        else:
            return HTMLResponse(content=json.dumps({"success": False, "message": f"Trường '{target_field}' chưa được hỗ trợ cập nhật"}), media_type="application/json")

        res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        
        if "errors" in data:
            return HTMLResponse(content=json.dumps({"success": False, "message": f"GraphQL Error: {data['errors'][0]['message']}"}), media_type="application/json")
        
        user_errs = data.get("data", {}).get("productUpdate", {}).get("userErrors", [])
        if user_errs:
            return HTMLResponse(content=json.dumps({"success": False, "message": f"Lỗi từ Shopify: {user_errs[0]['message']}"}), media_type="application/json")
            
        new_handle = data.get("data", {}).get("productUpdate", {}).get("product", {}).get("handle")
        return HTMLResponse(content=json.dumps({"success": True, "message": "Thành công", "newHandle": new_handle}), media_type="application/json")
            
    except Exception as e:
        import json
        return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}), media_type="application/json")

CONFIG_FILE = "config.json"

def get_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {"DELETE_PASSWORD": "abc123"}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            import json
            json.dump(default_config, f, indent=4)
        return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            import json
            return json.load(f)
    except:
        return {"DELETE_PASSWORD": "abc123"}

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        import json
        json.dump(config_data, f, indent=4)

def get_articles(sort_key="ID", reverse=True, first=50):
    query = """
    query getArticles($first: Int!, $sortKey: ArticleSortKeys, $reverse: Boolean) {
      articles(first: $first, sortKey: $sortKey, reverse: $reverse) {
        edges {
          node {
            id
            title
            isPublished
            publishedAt
            createdAt
            updatedAt
            image {
              url
            }
            blog {
              title
            }
          }
        }
      }
    }
    """
    variables = {
        "first": first,
        "sortKey": sort_key,
        "reverse": reverse
    }
    try:
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors fetching articles:", data["errors"])
            return []
        return [edge["node"] for edge in data.get("data", {}).get("articles", {}).get("edges", [])]
    except Exception as e:
        print("Error fetching articles:", e)
        return []

@app.get("/blogs", response_class=HTMLResponse)
async def blogs_page(request: Request, sort: str = "created_desc"):
    # sort can be: created_desc, created_asc, updated_desc, updated_asc, title_asc, title_desc
    sort_key = "ID"
    reverse = True
    
    if sort == "created_asc":
        sort_key = "ID"
        reverse = False
    elif sort == "updated_desc":
        sort_key = "UPDATED_AT"
        reverse = True
    elif sort == "updated_asc":
        sort_key = "UPDATED_AT"
        reverse = False
    elif sort == "title_asc":
        sort_key = "TITLE"
        reverse = False
    elif sort == "title_desc":
        sort_key = "TITLE"
        reverse = True
        
    articles = get_articles(sort_key=sort_key, reverse=reverse)
    
    # Format dates
    from datetime import datetime
    for article in articles:
        for date_field in ["createdAt", "updatedAt", "publishedAt"]:
            if article.get(date_field):
                try:
                    dt = datetime.fromisoformat(article[date_field].replace("Z", "+00:00"))
                    article[f"{date_field}_fmt"] = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    article[f"{date_field}_fmt"] = article[date_field]
            else:
                article[f"{date_field}_fmt"] = ""
                
    return templates.TemplateResponse(request=request, name="blogs.html", context={
        "request": request,
        "articles": articles,
        "current_sort": sort
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(request=request, name="settings.html", context={"request": request})

@app.post("/update-settings")
async def update_settings(request: Request, current_password: str = Form(...), new_password: str = Form(...)):
    config_data = get_config()
    import json
    if current_password != config_data.get("DELETE_PASSWORD"):
        return HTMLResponse(content=json.dumps({"success": False, "message": "Mật khẩu hiện tại không chính xác!"}), media_type="application/json")
        
    config_data["DELETE_PASSWORD"] = new_password
    save_config(config_data)
    return HTMLResponse(content=json.dumps({"success": True, "message": "Cập nhật mật khẩu thành công"}), media_type="application/json")

@app.post("/reset-token")
async def reset_token(request: Request):
    import json
    try:
        client_id = os.getenv("SHOPIFY_CLIENT_ID")
        client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            return HTMLResponse(content=json.dumps({"success": False, "message": "Thiếu CLIENT_ID hoặc CLIENT_SECRET trong .env"}), media_type="application/json")
        
        url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/oauth/access_token"
        response = requests.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=30,
        )
        if not response.ok:
            return HTMLResponse(content=json.dumps({"success": False, "message": f"Lỗi từ Shopify: {response.text}"}), media_type="application/json")
            
        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return HTMLResponse(content=json.dumps({"success": False, "message": "Không nhận được access_token"}), media_type="application/json")
            
        # Hot update
        global SHOPIFY_ADMIN_TOKEN
        SHOPIFY_ADMIN_TOKEN = access_token
        HEADERS["X-Shopify-Access-Token"] = access_token
        
        # Save to .env
        env_path = ".env"
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            with open(env_path, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("SHOPIFY_ADMIN_TOKEN="):
                        f.write(f"SHOPIFY_ADMIN_TOKEN={access_token}\n")
                    else:
                        f.write(line)
        else:
            with open(env_path, "a", encoding="utf-8") as f:
                f.write(f"\\nSHOPIFY_ADMIN_TOKEN={access_token}\\n")
                
        return HTMLResponse(content=json.dumps({"success": True, "message": "Reset Token thành công!"}), media_type="application/json")
    except Exception as e:
        return HTMLResponse(content=json.dumps({"success": False, "message": f"Lỗi nội bộ: {str(e)}"}), media_type="application/json")

@app.post("/delete-product")
async def delete_product(request: Request, product_id: str = Form(...), password: str = Form(...)):
    import json
    config_data = get_config()
    if password != config_data.get("DELETE_PASSWORD"):
        return HTMLResponse(content=json.dumps({"success": False, "message": "Mật khẩu không chính xác!"}), media_type="application/json")
        
    if not product_id.startswith("gid://"):
        product_id = f"gid://shopify/Product/{product_id}"
        
    try:
        # Fetch media IDs first to delete them
        media_query = """
        query getProductMedia($id: ID!) {
          product(id: $id) {
            media(first: 50) {
              edges {
                node {
                  id
                }
              }
            }
          }
        }
        """
        res_media = requests.post(GRAPHQL_URL, json={"query": media_query, "variables": {"id": product_id}}, headers=HEADERS)
        media_data = res_media.json()
        media_ids = []
        if "data" in media_data and media_data["data"]["product"] and media_data["data"]["product"]["media"]["edges"]:
            for edge in media_data["data"]["product"]["media"]["edges"]:
                media_ids.append(edge["node"]["id"])
                
        if media_ids:
            del_media_query = """
            mutation productDeleteMedia($mediaIds: [ID!]!, $productId: ID!) {
              productDeleteMedia(mediaIds: $mediaIds, productId: $productId) {
                deletedMediaIds
                userErrors {
                  field
                  message
                }
              }
            }
            """
            requests.post(GRAPHQL_URL, json={"query": del_media_query, "variables": {"mediaIds": media_ids, "productId": product_id}}, headers=HEADERS)

        # Delete the product
        query = """
        mutation productDelete($input: ProductDeleteInput!) {
          productDelete(input: $input) {
            deletedProductId
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {"input": {"id": product_id}}
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        
        if "errors" in data:
            return HTMLResponse(content=json.dumps({"success": False, "message": "GraphQL Error: " + str(data["errors"])}), media_type="application/json")
            
        delete_res = data.get("data", {}).get("productDelete", {})
        if delete_res and delete_res.get("userErrors"):
            return HTMLResponse(content=json.dumps({"success": False, "message": delete_res["userErrors"][0]["message"]}), media_type="application/json")
            
        return HTMLResponse(content=json.dumps({"success": True, "message": "Sản phẩm đã được xóa thành công."}), media_type="application/json")
    except Exception as e:
        return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}), media_type="application/json")

@app.post("/api/products/publications")
async def api_product_publications(request: Request):
    try:
        import json
        data = await request.json()
        product_id = data.get("product_id")
        publish_ids = data.get("publish_ids", [])
        unpublish_ids = data.get("unpublish_ids", [])
        
        if not product_id:
            return HTMLResponse(content=json.dumps({"success": False, "message": "Missing product ID"}), media_type="application/json")
            
        full_product_id = f"gid://shopify/Product/{product_id}" if not str(product_id).startswith("gid://") else product_id
        
        errors = []
        
        # Publish
        if publish_ids:
            publish_input = [{"publicationId": pub_id} for pub_id in publish_ids]
            query_publish = '''
            mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
              publishablePublish(id: $id, input: $input) {
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {"id": full_product_id, "input": publish_input}
            res = requests.post(GRAPHQL_URL, json={"query": query_publish, "variables": variables}, headers=HEADERS)
            res.raise_for_status()
            res_data = res.json()
            if "errors" in res_data:
                errors.append(f"Publish errors: {res_data['errors']}")
            else:
                user_errors = res_data.get("data", {}).get("publishablePublish", {}).get("userErrors", [])
                if user_errors:
                    errors.append(f"Publish user errors: {user_errors}")
                    
        # Unpublish
        if unpublish_ids:
            unpublish_input = [{"publicationId": pub_id} for pub_id in unpublish_ids]
            query_unpublish = '''
            mutation publishableUnpublish($id: ID!, $input: [PublicationInput!]!) {
              publishableUnpublish(id: $id, input: $input) {
                userErrors {
                  field
                  message
                }
              }
            }
            '''
            variables = {"id": full_product_id, "input": unpublish_input}
            res = requests.post(GRAPHQL_URL, json={"query": query_unpublish, "variables": variables}, headers=HEADERS)
            res.raise_for_status()
            res_data = res.json()
            if "errors" in res_data:
                errors.append(f"Unpublish errors: {res_data['errors']}")
            else:
                user_errors = res_data.get("data", {}).get("publishableUnpublish", {}).get("userErrors", [])
                if user_errors:
                    errors.append(f"Unpublish user errors: {user_errors}")
                    
        if errors:
            return HTMLResponse(content=json.dumps({"success": False, "message": " | ".join(errors)}), media_type="application/json")
            
        return HTMLResponse(content=json.dumps({"success": True, "message": "Đã cập nhật trạng thái kênh bán hàng thành công"}), media_type="application/json")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}), media_type="application/json")
