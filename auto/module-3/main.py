import os
import re
import time
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import requests

load_dotenv()

app = FastAPI()
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
            judgeme_data: metafield(namespace: "judgeme", key: "review_widget_data") {
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
                jdgm = node.get("judgeme_data")
                if jdgm and jdgm.get("value"):
                    try:
                        jdgm_data = json.loads(jdgm["value"])
                        count = int(jdgm_data.get("number_of_reviews", 0))
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

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, after: str = None, before: str = None, filter_type: str = "tag", filter_value: str = None, sort_by: str = "created_desc", special_filter: str = ""):
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
        elif filter_value and filter_type == "metafield_amazon_link":
            data = get_products_by_metafield_amazon_link(filter_value, sort_by=sort_by)
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
                if filter_type == "tag":
                    filter_query = f"tag:{filter_value}"
                elif filter_type == "title":
                    filter_query = f"title:*{filter_value}*"
                elif filter_type == "id":
                    filter_query = f"id:{filter_value}"
                elif filter_type == "handle":
                    filter_query = f"handle:{filter_value}"
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
            if not amz_link_node and filter_type == "metafield_amazon_link":
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
        
        return templates.TemplateResponse("index.html", {
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
        return templates.TemplateResponse("index.html", {
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
            return HTMLResponse(content="Product not found", status_code=404)
            
        media_urls = []
        for media_edge in product_data.get("media", {}).get("edges", []):
            media_node = media_edge["node"]
            if "image" in media_node and media_node["image"]:
                media_urls.append(media_node["image"]["url"])
            elif "preview" in media_node and media_node["preview"] and media_node["preview"]["image"]:
                media_urls.append(media_node["preview"]["image"]["url"])
                
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
            "media": media_urls,
            "prices": sorted_prices,
            "metafields": metafields
        }
        
        return templates.TemplateResponse("product.html", {
            "request": request, 
            "product": product,
            "error": None
        })
    except Exception as e:
        return templates.TemplateResponse("product.html", {
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
            
        return templates.TemplateResponse("collections.html", {
            "request": request, 
            "collections": collections,
            "total_count": total_collections_count,
            "sort_by": sort_by,
            "filter_mode": filter_mode,
            "error": None
        })
    except Exception as e:
        return templates.TemplateResponse("collections.html", {
            "request": request,
            "collections": [],
            "total_count": 0,
            "sort_by": sort_by,
            "filter_mode": filter_mode,
            "error": str(e)
        })

@app.get("/create", response_class=HTMLResponse)
async def create_product_form(request: Request):
    return templates.TemplateResponse("create_product.html", {
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
            
        return templates.TemplateResponse("create_product.html", {
            "request": request,
            "error": None,
            "success_message": f"Đã tạo thành công {success_count} sản phẩm!"
        })
        
    except Exception as e:
        return templates.TemplateResponse("create_product.html", {
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

def add_variant_options_to_product(product_id: str, option_pairs: list):
    product = get_product_options_by_id(product_id)
    if not product:
        return False, "Không tìm thấy sản phẩm trên Shopify"
    existing_opts = product.get("options", [])
    for opt_name, opt_values in option_pairs:
        existing_opt = next((o for o in existing_opts if o["name"].lower() == opt_name.lower()), None)
        if existing_opt is None:
            mutation = """
            mutation productOptionsCreate($productId: ID!, $options: [OptionCreateInput!]!) {
              productOptionsCreate(productId: $productId, options: $options, variantStrategy: CREATE) {
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
                "options": [{"name": opt_name, "values": [{"name": v} for v in opt_values]}]
            }
            res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
            res.raise_for_status()
            data = res.json()
            if "errors" in data:
                return False, f"GraphQL Error: {data['errors'][0]['message']}"
            user_errs = data.get("data", {}).get("productOptionsCreate", {}).get("userErrors", [])
            if user_errs:
                return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
            if data.get("data", {}).get("productOptionsCreate", {}).get("product"):
                existing_opts = data["data"]["productOptionsCreate"]["product"].get("options", [])
        else:
            existing_vals = set(existing_opt.get("values", []))
            new_vals = [v for v in opt_values if v not in existing_vals]
            if new_vals:
                mutation = """
                mutation productOptionUpdate($productId: ID!, $option: OptionUpdateInput!, $optionValuesToAdd: [OptionValueCreateInput!]!) {
                  productOptionUpdate(productId: $productId, option: $option, optionValuesToAdd: $optionValuesToAdd, variantStrategy: MANAGE) {
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
                    "optionValuesToAdd": [{"name": v} for v in new_vals]
                }
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
    return True, f"Đã thêm/cập nhật thành công {len(option_pairs)} variant options cho '{product.get('title', product_id)}'"

def is_ajax_request(request: Request) -> bool:
    accept = request.headers.get("accept", "").lower()
    x_req = request.headers.get("x-requested-with", "").lower()
    sec_dest = request.headers.get("sec-fetch-dest", "").lower()
    return "application/json" in accept or x_req == "xmlhttprequest" or sec_dest == "empty"

@app.get("/edit-variants", response_class=HTMLResponse)
async def edit_variants_form(request: Request):
    return templates.TemplateResponse("edit_variants.html", {
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

        raw_list = re.split(r'[\r\n,]+', identifiers_raw)
        identifiers = [i.strip() for i in raw_list if i.strip()]
        if not identifiers:
            msg = "Danh sách sản phẩm trống hoặc không hợp lệ"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse("edit_variants.html", {"request": request, "error": msg, "success_message": None})

        option_pairs = []
        for name, vals_str in zip(option_names, option_values):
            name_clean = name.strip()
            if not name_clean:
                continue
            vals_clean = [v.strip() for v in vals_str.split(",") if v.strip()]
            if not vals_clean:
                continue
            option_pairs.append((name_clean, vals_clean))

        if not option_pairs:
            msg = "Danh sách option hoặc giá trị trống"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse("edit_variants.html", {"request": request, "error": msg, "success_message": None})

        success_count = 0
        details = []

        for ident in identifiers:
            prod_id = resolve_product_id(ident, id_types)
            if not prod_id:
                details.append({"identifier": ident, "status": "FAIL", "message": "Không tìm thấy định danh hoặc handle hợp lệ"})
                continue

            success, msg = add_variant_options_to_product(prod_id, option_pairs)
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
            
        return templates.TemplateResponse("edit_variants.html", {
            "request": request,
            "error": None if success_count > 0 else msg_summary,
            "success_message": msg_summary if success_count > 0 else None
        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse("edit_variants.html", {"request": request, "error": str(e), "success_message": None})

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
            return templates.TemplateResponse("edit_variants.html", {"request": request, "error": msg, "success_message": None})
            
        if not tags:
            msg = "Danh sách tags trống"
            if is_ajax_request(request):
                import json
                return HTMLResponse(content=json.dumps({"success": False, "message": msg}, ensure_ascii=False), media_type="application/json")
            return templates.TemplateResponse("edit_variants.html", {"request": request, "error": msg, "success_message": None})

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
            
        return templates.TemplateResponse("edit_variants.html", {
            "request": request,
            "error": None if success_count > 0 else msg_summary,
            "success_message": msg_summary if success_count > 0 else None
        })
    except Exception as e:
        if is_ajax_request(request):
            import json
            return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}, ensure_ascii=False), media_type="application/json")
        return templates.TemplateResponse("edit_variants.html", {"request": request, "error": str(e), "success_message": None})
