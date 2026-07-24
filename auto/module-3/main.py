import os
import time
import uuid
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

def get_products(first=30, after=None, before=None, last=None, filter_query=None, sort_key="CREATED_AT", reverse=True):
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

def get_products_by_metafield_amazon_link(keyword, reverse=True):
    query = """
    query getProducts($after: String) {
      products(first: 250, after: $after) {
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
        
    all_matched_edges.sort(key=lambda edge: edge["node"].get("createdAt", ""), reverse=reverse)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

def get_products_by_description(keyword, reverse=True):
    query = """
    query getProducts($after: String) {
      products(first: 250, after: $after) {
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
        
    all_matched_edges.sort(key=lambda edge: edge["node"].get("createdAt", ""), reverse=reverse)
        
    return {
        "products": {
            "edges": all_matched_edges,
            "pageInfo": {"hasNextPage": False, "hasPreviousPage": False}
        },
        "productsCount": {"count": len(all_matched_edges)}
    }

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, after: str = None, before: str = None, filter_type: str = "tag", filter_value: str = None, sort_by: str = "created_desc"):
    try:
        filter_query = None
        data = None
        
        reverse = True if sort_by == "created_desc" else False
        
        if filter_value and filter_type == "metafield_amazon_link":
            data = get_products_by_metafield_amazon_link(filter_value, reverse=reverse)
        elif filter_value and filter_type == "description":
            data = get_products_by_description(filter_value, reverse=reverse)
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
                    
            data = get_products(first=30, after=after, before=before, filter_query=filter_query, sort_key="CREATED_AT", reverse=reverse)
            
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
            
            products.append({
                "id": node["id"].split("/")[-1],
                "handle": node["handle"],
                "title": node["title"],
                "description": node.get("descriptionHtml", ""),
                "createdAt": node.get("createdAt", ""),
                "options": options,
                "collections": collections,
                "media": media_urls
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
            "error": str(e)
        })

def get_product_by_handle(handle: str):
    query = """
    query getProductByHandle($handle: String!) {
      productByHandle(handle: $handle) {
        id
        title
        handle
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
            
        product = {
            "id": product_data["id"].split("/")[-1],
            "title": product_data["title"],
            "handle": product_data["handle"],
            "product_type": product_data.get("productType", ""),
            "category": product_data.get("category", {}).get("name", "") if product_data.get("category") else None,
            "tags": product_data.get("tags", []),
            "description": product_data.get("descriptionHtml", ""),
            "seo": product_data.get("seo", {}),
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
