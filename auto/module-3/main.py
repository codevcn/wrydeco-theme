import os
import re
import time
import uuid
import csv
import io
import json
import base64
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel
from PIL import Image
import requests
import threading

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

os.makedirs("assets", exist_ok=True)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

os.makedirs("backups", exist_ok=True)
app.mount("/backups", StaticFiles(directory="backups"), name="backups")

templates = Jinja2Templates(directory="templates")

SHOPIFY_SHOP = (os.getenv("SHOPIFY_SHOP") or "").strip().strip('"').strip("'")
SHOPIFY_ADMIN_TOKEN = (os.getenv("SHOPIFY_ADMIN_TOKEN") or "").strip().strip('"').strip("'")
SHOPIFY_API_VERSION = (os.getenv("SHOPIFY_API_VERSION") or "2024-04").strip().strip('"').strip("'")

GRAPHQL_URL = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
    "Content-Type": "application/json"
}

# =====================================================================
# PROXY GATEWAY CONFIGURATION & HELPERS
# =====================================================================
class ProxySafetyException(Exception):
    """Ném ra khi Proxy Gateway đang bật nhưng mất kết nối hoặc không ổn định"""
    pass

@app.exception_handler(ProxySafetyException)
async def proxy_safety_exception_handler(request: Request, exc: ProxySafetyException):
    return JSONResponse(
        status_code=503,
        content={"success": False, "error": str(exc)}
    )

PROXY_CONFIG_FILE = "proxy_config.json"
_proxy_lock = threading.Lock()
DEFAULT_PROXY_CONFIG = {
    "enabled": False,
    "proxy_url": "http://nPMZfSl5QX0shvm:hKTQVcQVNAvYHXq@185.124.63.174:55031",
    "proxy_ip": "185.124.63.174",
    "is_stable": False,
    "last_status": "unknown",
    "last_latency_ms": 0,
    "last_checked_at": None,
    "last_error": None
}

def load_proxy_config() -> dict:
    with _proxy_lock:
        if not os.path.exists(PROXY_CONFIG_FILE):
            tmp_file = f"{PROXY_CONFIG_FILE}.tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_PROXY_CONFIG, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_file, PROXY_CONFIG_FILE)
            except Exception:
                pass
            return DEFAULT_PROXY_CONFIG.copy()
        try:
            with open(PROXY_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                for k, v in DEFAULT_PROXY_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except Exception as e:
            print(f"Error loading proxy config: {e}")
            return DEFAULT_PROXY_CONFIG.copy()

def save_proxy_config(cfg: dict):
    with _proxy_lock:
        tmp_file = f"{PROXY_CONFIG_FILE}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, PROXY_CONFIG_FILE)
        except Exception as e:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
            print(f"Error saving proxy config: {e}")

def mark_proxy_unstable(err: str, latency: int = 0):
    try:
        cfg = load_proxy_config()
        cfg["is_stable"] = False
        cfg["last_status"] = "unstable"
        cfg["last_latency_ms"] = latency
        cfg["last_checked_at"] = datetime.now().isoformat()
        cfg["last_error"] = str(err)
        save_proxy_config(cfg)
    except Exception as e:
        print(f"Error marking proxy unstable: {e}")

def test_proxy_connectivity(proxy_url: str = None, timeout: int = 8):
    if not proxy_url:
        cfg = load_proxy_config()
        proxy_url = cfg.get("proxy_url")
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    test_url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/shop.json"
    test_headers = {
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN
    }
    
    t0 = time.time()
    try:
        resp = requests.get(test_url, headers=test_headers, proxies=proxies, timeout=timeout)
        latency_ms = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            return True, latency_ms, None
        else:
            return False, latency_ms, f"Shopify API HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        latency_ms = int((time.time() - t0) * 1000)
        return False, latency_ms, f"Hết thời gian chờ kết nối (Timeout > {timeout}s)"
    except Exception as e:
        latency_ms = int((time.time() - t0) * 1000)
        return False, latency_ms, str(e)

def fetch_proxy_egress_geo(proxy_url: str = None, timeout: int = 6):
    """
    Live Egress Verification: Bắn request xuyên qua Proxy để xác định vị trí thực tế, quốc gia, ISP mà phía ngoài nhìn thấy.
    """
    if not proxy_url:
        cfg = load_proxy_config()
        proxy_url = cfg.get("proxy_url")
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    # Nguồn 1: ipwho.is (rất chi tiết: emoji flag, country, region, city, isp)
    try:
        resp = requests.get("https://ipwho.is/", proxies=proxies, timeout=timeout)
        if resp.status_code == 200:
            d = resp.json()
            if d.get("success", False) or "country" in d:
                flag = "🌐"
                if isinstance(d.get("flag"), dict) and d.get("flag", {}).get("emoji"):
                    flag = d["flag"]["emoji"]
                elif d.get("country_code") == "US":
                    flag = "🇺🇸"
                
                isp = None
                if isinstance(d.get("connection"), dict):
                    isp = d["connection"].get("isp")
                
                return {
                    "ip": d.get("ip"),
                    "country": d.get("country"),
                    "country_code": d.get("country_code"),
                    "region": d.get("region"),
                    "city": d.get("city"),
                    "flag": flag,
                    "isp": isp,
                    "verified_at": datetime.now().isoformat()
                }
    except Exception as e:
        print(f"fetch_proxy_egress_geo (ipwho.is) notice: {e}")
        
    # Nguồn 2: ipapi.co fallback
    try:
        resp = requests.get("https://ipapi.co/json/", proxies=proxies, timeout=timeout)
        if resp.status_code == 200:
            d = resp.json()
            country_code = d.get("country_code")
            return {
                "ip": d.get("ip"),
                "country": d.get("country_name"),
                "country_code": country_code,
                "region": d.get("region"),
                "city": d.get("city"),
                "flag": "🇺🇸" if country_code == "US" else "🌐",
                "isp": d.get("org"),
                "verified_at": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"fetch_proxy_egress_geo (ipapi.co) notice: {e}")
        
    return None

def get_shopify_request_proxies():
    cfg = load_proxy_config()
    if not cfg.get("enabled"):
        return None
    
    now = datetime.now()
    last_check = None
    if cfg.get("last_checked_at"):
        try:
            last_check = datetime.fromisoformat(cfg["last_checked_at"])
        except Exception:
            last_check = None

    if not cfg.get("is_stable") or not last_check or (now - last_check).total_seconds() > 60:
        is_ok, latency, err = test_proxy_connectivity(cfg.get("proxy_url"), timeout=8)
        if not is_ok:
            cfg["is_stable"] = False
            cfg["last_status"] = "unstable"
            cfg["last_latency_ms"] = latency
            cfg["last_checked_at"] = now.isoformat()
            cfg["last_error"] = err
            save_proxy_config(cfg)
            raise ProxySafetyException(f"CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
        else:
            cfg["is_stable"] = True
            cfg["last_status"] = "stable"
            cfg["last_latency_ms"] = latency
            cfg["last_checked_at"] = now.isoformat()
            cfg["last_error"] = None
            save_proxy_config(cfg)

    return {
        "http": cfg["proxy_url"],
        "https": cfg["proxy_url"]
    }

# =====================================================================
# LOGO UPDATER DEDICATED CREDENTIALS CONFIGURATION & HELPERS
# =====================================================================
LOGO_UPDATER_CONFIG_FILE = "logo_updater_config.json"
_logo_updater_lock = threading.Lock()
DEFAULT_LOGO_UPDATER_CONFIG = {
    "shop_domain": "",
    "shop_name": "",
    "client_id": "",
    "client_secret": "",
    "access_token": "",
    "is_custom": False,
    "updated_at": None
}

def clean_shopify_domain(raw: str) -> str:
    if not raw:
        return ""
    d = str(raw).strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("?")[0].split("#")[0].strip("/")
    # Hỗ trợ đường dẫn admin Shopify dạng admin.shopify.com/store/{shop_name}
    m = re.search(r"admin\.shopify\.com/store/([^/]+)", d)
    if m:
        return m.group(1).replace(".myshopify.com", "")
    d = d.split("/")[0].split(":")[0]
    d = d.replace(".myshopify.com", "")
    return d

def mask_secret(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    if len(s) <= 8:
        return "********"
    return f"{s[:4]}...{s[-4:]}"

def load_logo_updater_config() -> dict:
    with _logo_updater_lock:
        if not os.path.exists(LOGO_UPDATER_CONFIG_FILE):
            tmp_file = f"{LOGO_UPDATER_CONFIG_FILE}.tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_LOGO_UPDATER_CONFIG, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_file, LOGO_UPDATER_CONFIG_FILE)
            except Exception:
                pass
            return DEFAULT_LOGO_UPDATER_CONFIG.copy()
        try:
            with open(LOGO_UPDATER_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                for k, v in DEFAULT_LOGO_UPDATER_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except Exception as e:
            print(f"Error loading logo updater config: {e}")
            return DEFAULT_LOGO_UPDATER_CONFIG.copy()

def save_logo_updater_config(cfg: dict):
    with _logo_updater_lock:
        tmp_file = f"{LOGO_UPDATER_CONFIG_FILE}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, LOGO_UPDATER_CONFIG_FILE)
        except Exception as e:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
            print(f"Error saving logo updater config: {e}")

def get_logo_updater_credentials() -> dict:
    proxy_cfg = load_proxy_config()
    is_proxy_enabled = bool(proxy_cfg.get("enabled", False))
    default_shop = clean_shopify_domain(SHOPIFY_SHOP)
    
    # 1. NẾU PROXY TẮT: BẮT BUỘC DÙNG LOẠI 1 (MẶC ĐỊNH SERVER TỪ .ENV)
    if not is_proxy_enabled:
        return {
            "type": 1,
            "is_custom": False,
            "proxy_enabled": False,
            "shop": default_shop,
            "token": SHOPIFY_ADMIN_TOKEN,
            "client_id": os.getenv("SHOPIFY_CLIENT_ID") or "",
            "client_secret": os.getenv("SHOPIFY_CLIENT_SECRET") or "",
            "headers": {
                "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
                "Content-Type": "application/json"
            },
            "graphql_url": f"https://{default_shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
        }
        
    # 2. NẾU PROXY BẬT: ĐỌC LOẠI 2 TỪ logo_updater_config.json
    custom_cfg = load_logo_updater_config()
    custom_token = (custom_cfg.get("access_token") or "").strip()
    if custom_token and custom_cfg.get("is_custom"):
        raw_shop = custom_cfg.get("shop_domain")
        shop = clean_shopify_domain(raw_shop) if raw_shop else default_shop
        if not shop:
            shop = default_shop
        return {
            "type": 2,
            "is_custom": True,
            "proxy_enabled": True,
            "shop": shop,
            "token": custom_token,
            "client_id": custom_cfg.get("client_id") or "",
            "client_secret": custom_cfg.get("client_secret") or "",
            "headers": {
                "X-Shopify-Access-Token": custom_token,
                "Content-Type": "application/json"
            },
            "graphql_url": f"https://{shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
        }
        
    # 3. FALLBACK NẾU PROXY BẬT NHƯNG CHƯA CẤU HÌNH LOẠI 2
    return {
        "type": 1,
        "is_custom": False,
        "proxy_enabled": True,
        "shop": default_shop,
        "token": SHOPIFY_ADMIN_TOKEN,
        "client_id": os.getenv("SHOPIFY_CLIENT_ID") or "",
        "client_secret": os.getenv("SHOPIFY_CLIENT_SECRET") or "",
        "headers": {
            "X-Shopify-Access-Token": SHOPIFY_ADMIN_TOKEN,
            "Content-Type": "application/json"
        },
        "graphql_url": f"https://{default_shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
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
    return get_products_by_metafield_amazon_link_list(keyword, sort_by=sort_by)

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
    keyword_list = [k.strip().lower() for k in re.split(r'[\r\n,]+', keywords_str) if k.strip()]
    
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
        elif filter_value and filter_type in ["metafield_amazon_link", "metafield_amazon_link_list"]:
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
        status
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
        collections(first: 50) {
          edges {
            node {
              id
              title
              handle
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
            "status": product_data.get("status", "ACTIVE"),
            "product_type": product_data.get("productType", ""),
            "category": product_data.get("category", {}).get("name", "") if product_data.get("category") else None,
            "tags": product_data.get("tags", []),
            "description": product_data.get("descriptionHtml", ""),
            "seo": product_data.get("seo", {}),
            "options": product_data.get("options", []),
            "media": media_list,
            "prices": sorted_prices,
            "metafields": metafields,
            "publications": publications,
            "collections": product_data.get("collections", {})
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
                createdAt
                image {
                  url
                }
                productsCount {
                  count
                }
                resourcePublications(first: 10) {
                  edges {
                    node {
                      publication {
                        name
                      }
                    }
                  }
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
            
            # Kiểm tra xem có publish lên Online Store không
            is_published = False
            for pub_edge in node.get("resourcePublications", {}).get("edges", []):
                pub_name = pub_edge.get("node", {}).get("publication", {}).get("name", "")
                if pub_name.lower() in ["online store", "cửa hàng trực tuyến"]:
                    is_published = True
                    break
                    
            all_collections.append({
                "id": node["id"].split("/")[-1],
                "handle": node["handle"],
                "title": node["title"],
                "description": node.get("descriptionHtml", ""),
                "image": node.get("image", {}).get("url") if node.get("image") else None,
                "products_count": node.get("productsCount", {}).get("count", 0) if node.get("productsCount") else 0,
                "published_online": is_published,
                "created_at": node.get("createdAt", "")
            })
            
        page_info = collections_data.get("pageInfo", {})
        has_next_page = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
        
    return all_collections


def get_collection_by_id(collection_id: str):
    query = """
    query getCollection($id: ID!) {
      collection(id: $id) {
        id
        title
        handle
        descriptionHtml
        image { url }
        seo { title description }
        productsCount { count }
        resourcePublications(first: 20) {
          edges { node { publication { name } } }
        }
        ruleSet {
          appliedDisjunctively
          rules {
            column
            relation
            condition
          }
        }
        metafield_buying_guide: metafield(namespace: "custom", key: "buying_guide") {
          id
          value
          type
        }
        metafield_related: metafield(namespace: "custom", key: "related_collections") {
          id
          value
          type
          references(first: 20) {
            edges {
              node {
                ... on Collection {
                  id
                  title
                  handle
                  image { url }
                  productsCount { count }
                }
              }
            }
          }
        }
      }
    }
    """
    variables = {"id": f"gid://shopify/Collection/{collection_id}"}
    response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        raise Exception(f"GraphQL Error: {data['errors']}")
    
    node = data["data"]["collection"]
    if not node:
        return None
        
    pub_map = get_publications_map()
    channels = [pub["node"]["publication"]["name"] for pub in node.get("resourcePublications", {}).get("edges", [])]
    publications_data = []
    for pub_name, pub_id in pub_map.items():
        publications_data.append({
            "id": pub_id,
            "name": pub_name,
            "is_published": pub_name in channels
        })
    
    rules = []
    rule_set = node.get("ruleSet")
    rules_data = {"is_manual": True, "condition_logic": "", "rules": []}
    if rule_set:
        rules_data["is_manual"] = False
        applied_disjunctively = rule_set.get("appliedDisjunctively", False)
        condition_logic = "Bất kỳ (Any)" if applied_disjunctively else "Tất cả (All)"
        rules_data["condition_logic"] = condition_logic
        for rule in rule_set.get("rules", []):
            rules.append(f"{rule.get('column')} {rule.get('relation')} {rule.get('condition')}")
            rules_data["rules"].append({
                "column": rule.get('column'),
                "relation": rule.get('relation'),
                "condition": rule.get('condition')
            })
        rules_str = f"Must match {condition_logic}: " + " | ".join(rules) if rules else "Thêm sản phẩm tự động nhưng không có rule cụ thể"
    else:
        rules_str = "Manual collection (Thêm sản phẩm thủ công)"
        
    # Parse Metafields
    buying_guide_node = node.get("metafield_buying_guide")
    buying_guide_val = buying_guide_node.get("value") if buying_guide_node else ""
    
    related_node = node.get("metafield_related")
    related_list = []
    if related_node and related_node.get("references"):
        for ref_edge in related_node["references"].get("edges", []):
            ref_col = ref_edge.get("node", {})
            if ref_col:
                rel_raw_id = ref_col.get("id", "")
                rel_num_id = rel_raw_id.split("/")[-1] if "/" in rel_raw_id else rel_raw_id
                related_list.append({
                    "id": rel_num_id,
                    "title": ref_col.get("title", ""),
                    "handle": ref_col.get("handle", ""),
                    "image": ref_col.get("image", {}).get("url") if ref_col.get("image") else None,
                    "products_count": ref_col.get("productsCount", {}).get("count", 0) if ref_col.get("productsCount") else 0
                })
                
    metafields_data = {
        "buying_guide": {
            "name": "Collection Buying Guide",
            "key": "custom.buying_guide",
            "type": "multi_line_text_field",
            "has_value": bool(buying_guide_val),
            "value": buying_guide_val or "",
            "char_count": len(buying_guide_val) if buying_guide_val else 0,
            "kb_size": round(len(buying_guide_val.encode('utf-8')) / 1024, 1) if buying_guide_val else 0
        },
        "related_collections": {
            "name": "Related Collections",
            "key": "custom.related_collections",
            "type": "list.collection_reference",
            "has_value": len(related_list) > 0,
            "collections": related_list,
            "count": len(related_list)
        }
    }

    return {
        "id": node["id"].split("/")[-1],
        "handle": node["handle"],
        "title": node["title"],
        "description": node.get("descriptionHtml", ""),
        "seo_title": node.get("seo", {}).get("title") if node.get("seo") else "",
        "seo_description": node.get("seo", {}).get("description") if node.get("seo") else "",
        "image": node.get("image", {}).get("url") if node.get("image") else None,
        "products_count": node.get("productsCount", {}).get("count", 0) if node.get("productsCount") else 0,
        "channels": channels,
        "publications_data": publications_data,
        "rules_str": rules_str,
        "rules_data": rules_data,
        "metafields": metafields_data
    }


@app.post("/api/collections/{collection_id}/publications")
async def api_collection_publications(collection_id: str, request: Request):
    try:
        import json
        data = await request.json()
        publish_ids = data.get("publish_ids", [])
        unpublish_ids = data.get("unpublish_ids", [])
        
        full_collection_id = f"gid://shopify/Collection/{collection_id}"
        
        errors = []
        
        # Publish
        if publish_ids:
            publish_input = [{"publicationId": pub_id} for pub_id in publish_ids]
            query_publish = """
            mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
              publishablePublish(id: $id, input: $input) {
                userErrors { field message }
              }
            }
            """
            variables = {"id": full_collection_id, "input": publish_input}
            res = requests.post(GRAPHQL_URL, json={"query": query_publish, "variables": variables}, headers=HEADERS)
            res.raise_for_status()
            res_data = res.json()
            if "errors" in res_data:
                errors.append(str(res_data["errors"]))
            user_errors = res_data.get("data", {}).get("publishablePublish", {}).get("userErrors", [])
            for ue in user_errors:
                errors.append(ue["message"])
                
        # Unpublish
        if unpublish_ids:
            unpublish_input = [{"publicationId": pub_id} for pub_id in unpublish_ids]
            query_unpublish = """
            mutation publishableUnpublish($id: ID!, $input: [PublicationInput!]!) {
              publishableUnpublish(id: $id, input: $input) {
                userErrors { field message }
              }
            }
            """
            variables = {"id": full_collection_id, "input": unpublish_input}
            res = requests.post(GRAPHQL_URL, json={"query": query_unpublish, "variables": variables}, headers=HEADERS)
            res.raise_for_status()
            res_data = res.json()
            if "errors" in res_data:
                errors.append(str(res_data["errors"]))
            user_errors = res_data.get("data", {}).get("publishableUnpublish", {}).get("userErrors", [])
            for ue in user_errors:
                errors.append(ue["message"])
                
        if errors:
            return HTMLResponse(content=json.dumps({"success": False, "message": " | ".join(errors)}), media_type="application/json")
            
        return HTMLResponse(content=json.dumps({"success": True}), media_type="application/json")
    except Exception as e:
        return HTMLResponse(content=json.dumps({"success": False, "message": str(e)}), media_type="application/json")


from fastapi import UploadFile, File
import base64

@app.post("/api/collections/{collection_id}/image")
async def update_collection_image(collection_id: str, request: Request, image: UploadFile = File(...)):
    try:
        clean_token = (SHOPIFY_ADMIN_TOKEN or os.getenv("SHOPIFY_ADMIN_TOKEN", "")).strip().strip('"').strip("'")
        req_headers = {
            "X-Shopify-Access-Token": clean_token,
            "Content-Type": "application/json"
        }
        
        # Check if collection is smart or custom
        query = '''
        query getCollection($id: ID!) {
          collection(id: $id) {
            ruleSet { rules { column } }
          }
        }
        '''
        variables = {"id": f"gid://shopify/Collection/{collection_id}"}
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=req_headers)
        res.raise_for_status()
        data = res.json()
        
        node = data.get("data", {}).get("collection")
        if not node:
            return JSONResponse(status_code=404, content={"success": False, "message": "Collection not found"})
            
        is_smart = bool(node.get("ruleSet"))
        collection_type = "smart_collection" if is_smart else "custom_collection"
        
        shop = (SHOPIFY_SHOP or os.getenv("SHOPIFY_SHOP", "")).strip().strip('"').strip("'")
        api_version = (SHOPIFY_API_VERSION or os.getenv("SHOPIFY_API_VERSION", "2024-04")).strip().strip('"').strip("'")
        rest_base_url = f"https://{shop}.myshopify.com/admin/api/{api_version}"
        target_url = f"{rest_base_url}/{collection_type}s/{collection_id}.json"
        
        # Read and encode uploaded image
        contents = await image.read()
        encoded = base64.b64encode(contents).decode("utf-8")
        
        upload_payload = {
            collection_type: {
                "id": collection_id,
                "image": {
                    "attachment": encoded,
                    "filename": image.filename
                }
            }
        }
        res_upload = requests.put(target_url, json=upload_payload, headers=req_headers)
        if not res_upload.ok:
            # Fallback: if direct update failed, try clearing image then upload again
            try:
                delete_payload = {
                    collection_type: {
                        "id": collection_id,
                        "image": None
                    }
                }
                requests.put(target_url, json=delete_payload, headers=req_headers)
                res_retry = requests.put(target_url, json=upload_payload, headers=req_headers)
                if res_retry.ok:
                    return JSONResponse(content={"success": True})
            except Exception:
                pass
            return JSONResponse(status_code=400, content={"success": False, "message": f"Không thể upload ảnh mới: {res_upload.text}"})
            
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

class CollectionUpdate(BaseModel):
    field: str
    value: str


@app.post("/api/collections/{collection_id}/update_rules")
async def update_collection_rules(collection_id: str, request: Request):
    form_data = await request.form()
    rule_columns = form_data.getlist("rule_column[]")
    rule_relations = form_data.getlist("rule_relation[]")
    rule_conditions = form_data.getlist("rule_condition[]")
    rule_match = form_data.get("rule_match", "ALL")
    
    rules = []
    for c, r, v in zip(rule_columns, rule_relations, rule_conditions):
        if c and r and v:
            rules.append({"column": c, "relation": r, "condition": v})
            
    input_data = {
        "id": f"gid://shopify/Collection/{collection_id}",
        "ruleSet": {
            "appliedDisjunctively": rule_match == "ANY",
            "rules": rules
        }
    }
    
    query = '''
    mutation collectionUpdate($input: CollectionInput!) {
      collectionUpdate(input: $input) {
        collection {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    '''
    try:
        response = requests.post(GRAPHQL_URL, json={"query": query, "variables": {"input": input_data}}, headers=HEADERS)
        response.raise_for_status()
        res_data = response.json()
        if "errors" in res_data:
            return JSONResponse(status_code=400, content={"success": False, "message": str(res_data["errors"])})
            
        user_errors = res_data["data"]["collectionUpdate"].get("userErrors", [])
        if user_errors:
            return JSONResponse(status_code=400, content={"success": False, "message": user_errors[0]["message"]})
            
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.post("/api/collections/{collection_id}/update")

async def update_collection(collection_id: str, data: CollectionUpdate):
    field = data.field
    value = data.value
    
    valid_fields = ["title", "handle", "descriptionHtml", "seo_title", "seo_description"]
    if field not in valid_fields:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid field"})
        
    input_data = {"id": f"gid://shopify/Collection/{collection_id}"}
    if field in ["seo_title", "seo_description"]:
        collection = get_collection_by_id(collection_id)
        existing_title = collection.get("seo_title") or "" if collection else ""
        existing_desc = collection.get("seo_description") or "" if collection else ""
        
        if field == "seo_title":
            input_data["seo"] = {"title": value, "description": existing_desc}
        else:
            input_data["seo"] = {"title": existing_title, "description": value}
    else:
        input_data[field] = value
        
    query = """
    mutation collectionUpdate($input: CollectionInput!) {
      collectionUpdate(input: $input) {
        collection { id }
        userErrors { field message }
      }
    }
    """
    response = requests.post(GRAPHQL_URL, json={"query": query, "variables": {"input": input_data}}, headers=HEADERS)
    response.raise_for_status()
    res_data = response.json()
    if "errors" in res_data:
        return JSONResponse(status_code=500, content={"success": False, "message": str(res_data["errors"])})
        
    user_errors = res_data["data"]["collectionUpdate"].get("userErrors", [])
    if user_errors:
        return JSONResponse(status_code=400, content={"success": False, "message": str(user_errors)})
        
    return JSONResponse(content={"success": True})

@app.get("/collections/{collection_id}", response_class=HTMLResponse)
async def collection_detail(request: Request, collection_id: str):
    try:
        collection = get_collection_by_id(collection_id)
        if not collection:
            return HTMLResponse("Collection not found", status_code=404)
        return templates.TemplateResponse(request=request, name="collection_detail.html", context={
            "request": request,
            "collection": collection
        })
    except Exception as e:
        return HTMLResponse(f"Error: {e}", status_code=500)

@app.post("/api/collections/create")
async def create_collection(request: Request):
    form_data = await request.form()
    title = form_data.get("title")
    collection_type = form_data.get("type", "SMART") # MANUAL or SMART
    handle = form_data.get("handle", "")
    description = form_data.get("description", "")
    seo_title = form_data.get("seo_title", "")
    seo_description = form_data.get("seo_description", "")
    
    rule_columns = form_data.getlist("rule_column[]")
    rule_relations = form_data.getlist("rule_relation[]")
    rule_conditions = form_data.getlist("rule_condition[]")
    rule_match = form_data.get("rule_match", "ALL")
    
    image = form_data.get("image")
    
    input_data = {
        "title": title,
    }
    if handle: input_data["handle"] = handle
    if description: input_data["descriptionHtml"] = description
    
    if seo_title or seo_description:
        input_data["seo"] = {}
        if seo_title: input_data["seo"]["title"] = seo_title
        if seo_description: input_data["seo"]["description"] = seo_description
        
    if collection_type == "SMART":
        rules = []
        for c, r, v in zip(rule_columns, rule_relations, rule_conditions):
            if c and r and v:
                rules.append({"column": c, "relation": r, "condition": v})
        
        if not rules:
            return JSONResponse(status_code=400, content={"success": False, "message": "Smart collection requires at least one rule."})
            
        input_data["ruleSet"] = {
            "appliedDisjunctively": True if rule_match == "ANY" else False,
            "rules": rules
        }
        
    query = '''
    mutation collectionCreate($input: CollectionInput!) {
      collectionCreate(input: $input) {
        collection { id }
        userErrors { field message }
      }
    }
    '''
    res = requests.post(GRAPHQL_URL, json={"query": query, "variables": {"input": input_data}}, headers=HEADERS)
    data = res.json()
    
    user_errors = data.get("data", {}).get("collectionCreate", {}).get("userErrors", [])
    if user_errors:
        return JSONResponse(status_code=400, content={"success": False, "message": user_errors[0]["message"]})
        
    new_collection = data.get("data", {}).get("collectionCreate", {}).get("collection", {})
    new_id_gid = new_collection.get("id")
    if not new_id_gid:
        return JSONResponse(status_code=500, content={"success": False, "message": "Failed to get new collection ID"})
        
    new_id = new_id_gid.split("/")[-1]
    
    if image and hasattr(image, 'filename') and image.filename:
        try:
            shop = os.getenv("SHOPIFY_SHOP")
            api_version = os.getenv("SHOPIFY_API_VERSION")
            rest_base_url = f"https://{shop}.myshopify.com/admin/api/{api_version}"
            
            c_type = "smart_collection" if collection_type == "SMART" else "custom_collection"
            contents = await image.read()
            import base64
            encoded = base64.b64encode(contents).decode("utf-8")
            upload_payload = {
                c_type: {
                    "id": new_id,
                    "image": {
                        "attachment": encoded,
                        "filename": image.filename
                    }
                }
            }
            upload_url = f"{rest_base_url}/{c_type}s/{new_id}.json"
            requests.put(upload_url, json=upload_payload, headers=HEADERS)
        except Exception as e:
            print("Image upload error:", e)
            
    return JSONResponse(content={"success": True, "id": new_id})


@app.get("/collections", response_class=HTMLResponse)
async def read_collections(request: Request, 
                           sort_by: str = "created_desc", 
                           filter_mode: str = "all"):
    try:
        collections = get_all_collections()
        total_collections_count = len(collections)
        
        # 1. Filter (Lọc theo)
        if filter_mode == "empty":
            collections = [c for c in collections if c["products_count"] == 0]
        elif filter_mode == "not_empty":
            collections = [c for c in collections if c["products_count"] > 0]
        elif filter_mode == "published":
            collections = [c for c in collections if c.get("published_online")]
        elif filter_mode == "unpublished":
            collections = [c for c in collections if not c.get("published_online")]
            
        # 2. Sort (Sắp xếp)
        if sort_by == "title_asc":
            collections.sort(key=lambda x: x["title"].lower())
        elif sort_by == "title_desc":
            collections.sort(key=lambda x: x["title"].lower(), reverse=True)
        elif sort_by == "count_asc":
            collections.sort(key=lambda x: x["products_count"])
        elif sort_by == "count_desc":
            collections.sort(key=lambda x: x["products_count"], reverse=True)
        elif sort_by == "created_asc":
            collections.sort(key=lambda x: int(x["id"]) if str(x.get("id", "")).isdigit() else 0)
        else: # created_desc (mặc định)
            collections.sort(key=lambda x: int(x["id"]) if str(x.get("id", "")).isdigit() else 0, reverse=True)
            sort_by = "created_desc"
            
        return templates.TemplateResponse(request=request, name="collections.html", context={
            "request": request, 
            "collections": collections,
            "total_count": len(collections),
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

def add_tags_to_product(product_id: str, tags: list, headers: dict = None, graphql_url: str = None):
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
    proxies = get_shopify_request_proxies()
    use_headers = headers or HEADERS
    use_url = graphql_url or GRAPHQL_URL
    try:
        res = requests.post(use_url, json={"query": mutation, "variables": variables}, headers=use_headers, proxies=proxies, timeout=30)
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        if proxies:
            mark_proxy_unstable(str(pe))
            raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
        raise
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        return False, f"GraphQL Error: {data['errors'][0]['message']}"
    user_errs = data.get("data", {}).get("tagsAdd", {}).get("userErrors", [])
    if user_errs:
        return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
    return True, f"Đã thêm tags thành công"

def remove_tags_from_product(product_id: str, tags: list, headers: dict = None, graphql_url: str = None):
    mutation = """
    mutation tagsRemove($id: ID!, $tags: [String!]!) {
      tagsRemove(id: $id, tags: $tags) {
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
    proxies = get_shopify_request_proxies()
    use_headers = headers or HEADERS
    use_url = graphql_url or GRAPHQL_URL
    try:
        res = requests.post(use_url, json={"query": mutation, "variables": variables}, headers=use_headers, proxies=proxies, timeout=30)
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        if proxies:
            mark_proxy_unstable(str(pe))
            raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
        raise
    res.raise_for_status()
    data = res.json()
    if "errors" in data:
        return False, f"GraphQL Error: {data['errors'][0]['message']}"
    user_errs = data.get("data", {}).get("tagsRemove", {}).get("userErrors", [])
    if user_errs:
        return False, f"Lỗi từ Shopify: {user_errs[0]['message']}"
    return True, f"Đã xóa tags thành công"

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
            tags_to_delete = [t.strip() for t in form_data.get("tags_to_delete", "").split(",") if t.strip()]

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
            
            if tags_to_delete:
                del_tag_success, del_tag_msg = remove_tags_from_product(prod_id, tags_to_delete)
                msgs.append(del_tag_msg)
                if not del_tag_success:
                    has_error = True
                    
            if not product_type and not tags and not tags_to_delete:
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


@app.get("/api/product-authors")
def get_product_authors():
    query = """
    query {
      metaobjects(type: "product_author", first: 100) {
        edges {
          node {
            id
            handle
            fields {
              key
              value
            }
          }
        }
      }
    }
    """
    try:
        res = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        
        authors = []
        if "data" in data and "metaobjects" in data["data"]:
            for edge in data["data"]["metaobjects"]["edges"]:
                node = edge["node"]
                author = {"id": node["id"], "handle": node["handle"]}
                for field in node["fields"]:
                    if field["key"] == "title" or field["key"] == "name":
                        author["name"] = field["value"]
                authors.append(author)
        return JSONResponse(content=authors)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

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

        if target_field == "status":
            mutation = '''
            mutation productUpdate($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                  status
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
                    "status": new_value.upper()
                }
            }

        elif target_field == "productTitle":
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

def get_articles_count(search_query=None):
    count = 0
    has_next = True
    cursor = None
    
    while has_next:
        query = """
        query getArticlesCount($first: Int!, $query: String, $after: String) {
          articles(first: $first, query: $query, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
              }
            }
          }
        }
        """
        variables = {"first": 250}
        if search_query:
            variables["query"] = search_query
        if cursor:
            variables["after"] = cursor
            
        try:
            res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
            res.raise_for_status()
            data = res.json()
            if "errors" in data:
                print("GraphQL Errors fetching articles count:", data["errors"])
                break
                
            articles_data = data.get("data", {}).get("articles", {})
            edges = articles_data.get("edges", [])
            count += len(edges)
            
            page_info = articles_data.get("pageInfo", {})
            has_next = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")
        except Exception as e:
            print("Error fetching articles count:", e)
            break
            
    return count

def get_articles(sort_key="ID", reverse=True, first=50, after=None, before=None, search_query=None):
    args = "$first: Int, $sortKey: ArticleSortKeys, $reverse: Boolean, $query: String, $after: String, $before: String"
    articles_args = "first: $first, sortKey: $sortKey, reverse: $reverse, query: $query, after: $after, before: $before"
    
    # If going backwards, use last instead of first
    if before:
        args = "$last: Int, $sortKey: ArticleSortKeys, $reverse: Boolean, $query: String, $after: String, $before: String"
        articles_args = "last: $last, sortKey: $sortKey, reverse: $reverse, query: $query, after: $after, before: $before"

    query = f"""
    query getArticles({args}) {{
      articles({articles_args}) {{
        pageInfo {{
          hasNextPage
          hasPreviousPage
          startCursor
          endCursor
        }}
        edges {{
          node {{
            id
            title
            isPublished
            publishedAt
            createdAt
            updatedAt
            image {{
              url
            }}
            blog {{
              title
            }}
          }}
        }}
      }}
    }}
    """
    
    variables = {
        "sortKey": sort_key,
        "reverse": reverse
    }
    
    if before:
        variables["last"] = first
        variables["before"] = before
    else:
        variables["first"] = first
        if after:
            variables["after"] = after
            
    if search_query:
        variables["query"] = search_query

    try:
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors fetching articles:", data["errors"])
            return [], {}
        
        articles_data = data.get("data", {}).get("articles", {})
        edges = articles_data.get("edges", [])
        page_info = articles_data.get("pageInfo", {})
        
        return [edge["node"] for edge in edges], page_info
    except Exception as e:
        print("Error fetching articles:", e)
        return [], {}

@app.get("/blogs")
async def blogs_page(request: Request, sort: str = "created_desc", search: str = "", after: str = None, before: str = None, date_type: str = "created_at", date_from: str = None, date_to: str = None):
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
        
    query_parts = []
    if search:
        query_parts.append(f"*{search}*")
    if date_from:
        query_parts.append(f"{date_type}:>={date_from}:00Z")
    if date_to:
        query_parts.append(f"{date_type}:<={date_to}:00Z")
        
    search_query = " ".join(query_parts) if query_parts else None
        
    articles, page_info = get_articles(sort_key=sort_key, reverse=reverse, after=after, before=before, search_query=search_query)
    
    total_store_count = get_articles_count()
    total_search_count = get_articles_count(search_query) if search_query else total_store_count
    
    # If we are searching and there is a keyword, we can also perform a local fallback filter for summary/content
    if search:
        search_lower = search.lower()
        
        def get_relevance_score(a):
            score = 0
            title = a.get('title', '') or ''
            if title.lower() == search_lower:
                score += 100
            elif search_lower in title.lower():
                score += 50
                if title.lower().startswith(search_lower):
                    score += 10
                    
            blog_title = (a.get('blog') or {}).get('title', '') or ''
            if blog_title.lower() == search_lower:
                score += 30
            elif search_lower in blog_title.lower():
                score += 20
                
            return score
            
        # Sort so that higher scores (matches in title/blog) appear at the top
        articles.sort(key=get_relevance_score, reverse=True)

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
                
    if is_ajax_request(request):
        import json
        return HTMLResponse(content=json.dumps({
            "articles": articles,
            "pageInfo": page_info,
            "totalStoreCount": total_store_count,
            "totalSearchCount": total_search_count
        }), media_type="application/json")
    # Fetch all blogs for the dropdown
    try:
        b_query = "{ blogs(first: 50) { edges { node { id title } } } }"
        b_res = requests.post(GRAPHQL_URL, json={"query": b_query}, headers=HEADERS).json()
        all_blogs = [edge["node"] for edge in b_res.get("data", {}).get("blogs", {}).get("edges", [])]
    except Exception as e:
        print("Error fetching blogs:", e)
        all_blogs = []

    return templates.TemplateResponse(request=request, name="blogs.html", context={
        "request": request,
        "articles": articles,
        "pageInfo": page_info,
        "current_sort": sort,
        "search": search,
        "total_store_count": total_store_count,
        "total_search_count": total_search_count,
        "date_type": date_type,
        "date_from": date_from,
        "date_to": date_to,
        "all_blogs": all_blogs
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
@app.post("/api/products/duplicate")
@app.post("/duplicate-product")
async def duplicate_product_endpoint(request: Request):
    import json
    try:
        product_id = None
        title = None
        new_title = None

        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
            product_id = data.get("product_id")
            title = data.get("title")
            new_title = data.get("new_title")
        else:
            form = await request.form()
            product_id = form.get("product_id")
            title = form.get("title")
            new_title = form.get("new_title")

        if not product_id:
            return JSONResponse({"success": False, "message": "Vui lòng cung cấp ID sản phẩm cần nhân bản."}, status_code=400)

        if not str(product_id).startswith("gid://"):
            gid = f"gid://shopify/Product/{product_id}"
        else:
            gid = str(product_id)

        # Lấy title sản phẩm gốc nếu chưa có
        if not title:
            q_title = """
            query getProd($id: ID!) {
              product(id: $id) {
                title
              }
            }
            """
            res_t = requests.post(GRAPHQL_URL, json={"query": q_title, "variables": {"id": gid}}, headers=HEADERS)
            if res_t.ok:
                title = res_t.json().get("data", {}).get("product", {}).get("title", "Product")
            else:
                title = "Product"

        if not new_title:
            new_title = f"Copy of {title}"

        mutation = """
        mutation productDuplicate($productId: ID!, $newTitle: String!) {
          productDuplicate(productId: $productId, newTitle: $newTitle, includeImages: true, synchronous: true) {
            newProduct {
              id
              title
              handle
              createdAt
              status
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "productId": gid,
            "newTitle": new_title
        }

        res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        res_data = res.json()

        if "errors" in res_data:
            err_msg = res_data["errors"][0].get("message", "Lỗi GraphQL từ Shopify")
            return JSONResponse({"success": False, "message": f"Shopify GraphQL Error: {err_msg}"})

        dup_payload = res_data.get("data", {}).get("productDuplicate", {})
        user_errors = dup_payload.get("userErrors", [])
        if user_errors:
            err_msg = "; ".join([e.get("message", "") for e in user_errors])
            return JSONResponse({"success": False, "message": f"Lỗi nhân bản từ Shopify: {err_msg}"})

        new_product = dup_payload.get("newProduct")
        if not new_product:
            return JSONResponse({"success": False, "message": "Shopify không trả về thông tin sản phẩm mới sau khi nhân bản."})

        new_id = new_product["id"].split("/")[-1]
        new_handle = new_product.get("handle", "")
        new_prod_title = new_product.get("title", "")

        # Thêm tag "duplicated-product" cho sản phẩm được nhân bản
        try:
            add_tags_to_product(new_product["id"], ["duplicated-product"])
        except Exception as tag_err:
            print(f"Lỗi khi thêm tag duplicated-product: {tag_err}")

        return JSONResponse({
            "success": True,
            "message": f"Nhân bản sản phẩm thành công! Sản phẩm mới: {new_prod_title} (ID: {new_id}) kèm tag 'duplicated-product'",
            "newProduct": {
                "id": new_id,
                "title": new_prod_title,
                "handle": new_handle
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi hệ thống: {str(e)}"}, status_code=500)

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


def get_article_detail(article_id):
    query = """
    query getArticle($id: ID!) {
      article(id: $id) {
        id
        handle
        title
        summary
        isPublished
        publishedAt
        createdAt
        updatedAt
        image { url }
        author { name }
        blog { id title }
        tags
        seo_title: metafield(namespace: "global", key: "title_tag") { value }
        seo_desc: metafield(namespace: "global", key: "description_tag") { value }
        body
        comments(first: 50) {
          edges {
            node {
              id
              author { name email }
              bodyHtml
              status
              createdAt
            }
          }
        }
      }
    }
    """
    
    full_id = f"gid://shopify/Article/{article_id}"
    variables = {"id": full_id}
    
    try:
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL Errors fetching article detail:", data["errors"])
            return None
        return data.get("data", {}).get("article")
    except Exception as e:
        print("Error fetching article detail:", e)
        return None

@app.get("/blogs/handle/{handle}")
async def redirect_blog_by_handle(handle: str):
    query = """
    query getArticlesByHandle($query: String!) {
      articles(first: 1, query: $query) {
        edges {
          node {
            id
          }
        }
      }
    }
    """
    variables = {"query": f"handle:{handle}"}
    try:
        res = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=HEADERS)
        data = res.json()
        edges = data.get("data", {}).get("articles", {}).get("edges", [])
        if edges:
            node_id = edges[0]["node"]["id"].split("/")[-1]
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"/blogs/{node_id}")
        return HTMLResponse("Không tìm thấy bài viết nào với handle này.", status_code=404)
    except Exception as e:
        return HTMLResponse(f"Lỗi: {str(e)}", status_code=500)

@app.get("/blogs/{article_id}")
async def blog_detail_page(request: Request, article_id: str):
    article = get_article_detail(article_id)
    if not article:
        return HTMLResponse("Không tìm thấy bài viết hoặc có lỗi xảy ra.", status_code=404)
        
    # Format date
    from datetime import datetime
    for date_field in ["createdAt", "updatedAt", "publishedAt"]:
        if article.get(date_field):
            try:
                dt = datetime.fromisoformat(article[date_field].replace("Z", "+00:00"))
                article[f"{date_field}_fmt"] = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                article[f"{date_field}_fmt"] = article[date_field]
                
    if article.get("comments") and article["comments"].get("edges"):
        for edge in article["comments"]["edges"]:
            c_node = edge["node"]
            if c_node.get("createdAt"):
                try:
                    dt = datetime.fromisoformat(c_node["createdAt"].replace("Z", "+00:00"))
                    c_node["createdAt_fmt"] = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    c_node["createdAt_fmt"] = c_node["createdAt"]
    
    # Fetch all blogs for the dropdown
    try:
        b_query = "{ blogs(first: 50) { edges { node { id title } } } }"
        b_res = requests.post(GRAPHQL_URL, json={"query": b_query}, headers=HEADERS).json()
        all_blogs = [edge["node"] for edge in b_res.get("data", {}).get("blogs", {}).get("edges", [])]
    except Exception as e:
        print("Error fetching blogs:", e)
        all_blogs = []
    
    return templates.TemplateResponse(request=request, name="blog_detail.html", context={
        "request": request,
        "article": article,
        "all_blogs": all_blogs
    })



@app.post("/blogs/{article_id}/update")
async def update_blog_post(article_id: str, request: Request):
    try:
        data = await request.json()
        field = data.get("field")
        value = data.get("value")
        
        article_gid = f"gid://shopify/Article/{article_id}"
        article_input = {}
        
        if field == "title":
            article_input["title"] = value
        elif field == "handle":
            article_input["handle"] = value
        elif field == "summary":
            article_input["summary"] = value
        elif field == "body":
            article_input["body"] = value
        elif field == "isPublished":
            article_input["isPublished"] = str(value).lower() == "true"
        elif field == "seo":
            article_input["metafields"] = [
                {"namespace": "global", "key": "title_tag", "value": str(value.get("title", "")), "type": "string"},
                {"namespace": "global", "key": "description_tag", "value": str(value.get("description", "")), "type": "string"}
            ]
        elif field == "blogId":
            article_input["blogId"] = value
        elif field == "tags":
            article_input["tags"] = value
        elif field == "image":
            import re
            b64_data = re.sub('^data:image/.+;base64,', '', value)
            rest_url = f"https://{os.getenv('SHOPIFY_SHOP')}.myshopify.com/admin/api/{os.getenv('SHOPIFY_API_VERSION', '2024-04')}/articles/{article_id}.json"
            payload = {
                "article": {
                    "id": article_id,
                    "image": {
                        "attachment": b64_data
                    }
                }
            }
            res = requests.put(rest_url, json=payload, headers=HEADERS)
            if res.status_code in [200, 201]:
                return JSONResponse({"success": True})
            else:
                return JSONResponse({"success": False, "error": res.text})
                
        if article_input:
            mutation = """
            mutation articleUpdate($id: ID!, $article: ArticleUpdateInput!) {
              articleUpdate(id: $id, article: $article) {
                article { id }
                userErrors { field message }
              }
            }
            """
            res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": {"id": article_gid, "article": article_input}}, headers=HEADERS)
            res_data = res.json()
            errors = res_data.get("data", {}).get("articleUpdate", {}).get("userErrors", [])
            if errors:
                return JSONResponse({"success": False, "error": errors[0]["message"]})
            return JSONResponse({"success": True})
            
        return JSONResponse({"success": False, "error": "Invalid field"})
    except Exception as e:
        print("Update error:", e)
        return JSONResponse({"success": False, "error": str(e)})



@app.post("/blogs/create")
async def create_blog_post(request: Request):
    try:
        data = await request.json()
        
        # Build article input
        article_input = {
            "title": data.get("title", ""),
            "author": {"name": data.get("author", "Wrydeco Admin")},
        }
        
        if data.get("blogId"):
            article_input["blogId"] = data.get("blogId")
        if data.get("summary"):
            article_input["summary"] = data.get("summary")
        if data.get("body"):
            article_input["body"] = data.get("body")
        if "isPublished" in data:
            article_input["isPublished"] = data.get("isPublished")
            
        mutation = """
        mutation articleCreate($article: ArticleCreateInput!) {
          articleCreate(article: $article) {
            article { id }
            userErrors { field message }
          }
        }
        """
        res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": {"article": article_input}}, headers=HEADERS)
        res_data = res.json()
        
        errors = res_data.get("data", {}).get("articleCreate", {}).get("userErrors", [])
        if errors:
            return JSONResponse({"success": False, "error": errors[0]["message"]})
            
        article_id = res_data["data"]["articleCreate"]["article"]["id"].split('/')[-1]
        return JSONResponse({"success": True, "id": article_id})
    except Exception as e:
        print("Create error:", e)
        return JSONResponse({"success": False, "error": str(e)})



@app.post("/blogs/{article_id}/delete")
async def delete_blog_post(article_id: str, request: Request):
    try:
        data = await request.json()
        password = data.get("password")
        
        # Verify password
        config_data = get_config()
        if password != config_data.get("DELETE_PASSWORD"):
            return JSONResponse({"success": False, "message": "Mật khẩu không chính xác!"})
            
        # Delete article via GraphQL
        article_gid = f"gid://shopify/Article/{article_id}"
        mutation = """
        mutation articleDelete($id: ID!) {
          articleDelete(id: $id) {
            deletedId
            userErrors { field message }
          }
        }
        """
        res = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": {"id": article_gid}}, headers=HEADERS)
        res_data = res.json()
        
        errors = res_data.get("data", {}).get("articleDelete", {}).get("userErrors", [])
        if errors:
            return JSONResponse({"success": False, "message": errors[0]["message"]})
            
        return JSONResponse({"success": True})
    except Exception as e:
        print("Delete error:", e)
        return JSONResponse({"success": False, "message": str(e)})



def get_metaobject_definitions_data():
    from datetime import datetime
    query = """
    query getMetaobjectDefinitions {
      metaobjectDefinitions(first: 50) {
        edges {
          node {
            id
            name
            type
            description
            metaobjectsCount
            fieldDefinitions {
              name
              key
              type {
                name
              }
              description
              required
            }
            access {
              storefront
            }
          }
        }
      }
    }
    """
    try:
        res = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        if "errors" in data:
            print("GraphQL error in get_metaobject_definitions:", data["errors"])
            return []
        edges = data.get("data", {}).get("metaobjectDefinitions", {}).get("edges", [])
        defs = [e["node"] for e in edges]
        
        # Process defs
        for d in defs:
            d["numeric_id"] = d["id"].split("/")[-1]
            d["is_custom"] = not d["type"].startswith("shopify--")
            d["added_by"] = "Shopify Web" if d["is_custom"] else "Shopify Standard"
            d["storefront_access"] = d.get("access", {}).get("storefront", "NONE")
            d["fields_count"] = len(d.get("fieldDefinitions", []))
            d["entries"] = []

        # Batch query entries
        active_defs = [d for d in defs if d.get("metaobjectsCount", 0) > 0]
        if active_defs:
            query_parts = []
            alias_map = {}
            for i, d in enumerate(active_defs):
                alias = f"mo_{i}"
                alias_map[alias] = d
                safe_type = d["type"].replace('"', '\\"')
                query_parts.append(f"""
                {alias}: metaobjects(type: "{safe_type}", first: 50, sortKey: "updated_at", reverse: true) {{
                  edges {{
                    node {{
                      id
                      handle
                      type
                      displayName
                      updatedAt
                      fields {{
                        key
                        value
                        type
                      }}
                    }}
                  }}
                }}
                """)
            batched_query = "query {\n" + "\n".join(query_parts) + "\n}"
            try:
                res2 = requests.post(GRAPHQL_URL, json={"query": batched_query}, headers=HEADERS)
                res2.raise_for_status()
                data2 = res2.json()
                for alias, result in data2.get("data", {}).items():
                    d = alias_map.get(alias)
                    if d:
                        for e in result.get("edges", []):
                            entry = e["node"]
                            entry["numeric_id"] = entry["id"].split("/")[-1]
                            raw_time = entry.get("updatedAt", "")
                            if raw_time:
                                try:
                                    dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                                    entry["updatedAt_fmt"] = dt.strftime("%d/%m/%Y %H:%M")
                                except Exception:
                                    entry["updatedAt_fmt"] = raw_time
                            else:
                                entry["updatedAt_fmt"] = ""
                            d["entries"].append(entry)
            except Exception as e:
                print("Error in batched metaobjects query:", e)

        for d in defs:
            latest_time = ""
            if d.get("entries"):
                latest_time = max((e.get("updatedAt", "") for e in d["entries"]), default="")
            d["latest_updated_at"] = latest_time
            if latest_time:
                try:
                    dt = datetime.fromisoformat(latest_time.replace("Z", "+00:00"))
                    d["latest_updated_at_fmt"] = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    d["latest_updated_at_fmt"] = latest_time
            else:
                d["latest_updated_at_fmt"] = "--"

        # Sắp xếp theo thời điểm cập nhật metaobject:
        # Bước 1: Sắp xếp theo tên A-Z
        defs.sort(key=lambda d: d.get("name", "").lower())
        # Bước 2: Sắp xếp theo latest_updated_at giảm dần (thời điểm mới nhất đưa lên đầu)
        defs.sort(key=lambda d: d.get("latest_updated_at") or "", reverse=True)
        return defs
    except Exception as e:
        print("Error fetching metaobject definitions:", e)
        return []


def get_metaobject_definitions():
    defs = get_metaobject_definitions_data()
    return defs


@app.get("/metaobjects", response_class=HTMLResponse)
async def metaobjects_page(request: Request, tab: str = "custom", search: str = ""):
    all_defs = get_metaobject_definitions_data()
    
    # Custom definitions (14 definitions matching Shopify Admin settings)
    custom_defs = [d for d in all_defs if d.get("is_custom")]
    standard_defs = [d for d in all_defs if not d.get("is_custom")]
    
    if tab == "all":
        display_defs = list(all_defs)
    elif tab == "standard":
        display_defs = list(standard_defs)
    else:
        tab = "custom"
        display_defs = list(custom_defs)

    if search and search.strip():
        q = search.strip().lower()
        display_defs = [
            d for d in display_defs
            if q in d.get("name", "").lower()
            or q in d.get("type", "").lower()
            or q in (d.get("description") or "").lower()
            or any(q in f.get("name", "").lower() or q in f.get("key", "").lower() for f in d.get("fieldDefinitions", []))
            or any(q in e.get("displayName", "").lower() or q in e.get("handle", "").lower() for e in d.get("entries", []))
        ]

    total_custom = len(custom_defs)
    total_all = len(all_defs)
    total_entries = sum(len(d.get("entries", [])) for d in all_defs)

    return templates.TemplateResponse(request=request, name="metaobjects.html", context={
        "request": request,
        "definitions": display_defs,
        "all_definitions": all_defs,
        "current_tab": tab,
        "search": search,
        "total_custom": total_custom,
        "total_all": total_all,
        "total_entries": total_entries,
        "total_displayed": len(display_defs),
        "shopify_shop": SHOPIFY_SHOP
    })


@app.post("/api/metaobjects/update")
async def update_metaobject_entry(request: Request):
    try:
        body = await request.json()
        entry_id = body.get("id")
        fields = body.get("fields", [])
        
        if not entry_id:
            return JSONResponse({"success": False, "message": "Thiếu ID bản ghi metaobject"}, status_code=400)
            
        if not str(entry_id).startswith("gid://shopify/Metaobject/"):
            gid = f"gid://shopify/Metaobject/{entry_id}"
        else:
            gid = str(entry_id)
            
        cleaned_fields = []
        for f in fields:
            k = f.get("key")
            v = f.get("value")
            if k is not None and v is not None:
                cleaned_fields.append({"key": str(k), "value": str(v)})
                
        mutation = """
        mutation updateMetaobject($id: ID!, $metaobject: MetaobjectUpdateInput!) {
          metaobjectUpdate(id: $id, metaobject: $metaobject) {
            metaobject {
              id
              handle
              displayName
              updatedAt
              fields {
                key
                value
                type
              }
            }
            userErrors {
              field
              message
              code
            }
          }
        }
        """
        
        res = requests.post(GRAPHQL_URL, json={
            "query": mutation,
            "variables": {
                "id": gid,
                "metaobject": {
                    "fields": cleaned_fields
                }
            }
        }, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        
        if "errors" in data:
            return JSONResponse({"success": False, "message": str(data["errors"])}, status_code=400)
            
        update_res = data.get("data", {}).get("metaobjectUpdate", {})
        user_errors = update_res.get("userErrors", [])
        if user_errors:
            error_msgs = [e.get("message", "Lỗi không xác định") for e in user_errors]
            return JSONResponse({"success": False, "message": "; ".join(error_msgs), "errors": user_errors}, status_code=400)
            
        updated_obj = update_res.get("metaobject")
        return JSONResponse({"success": True, "message": "Đã lưu bản ghi thành công!", "metaobject": updated_obj})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi hệ thống: {str(e)}"}, status_code=500)


@app.post("/api/metaobjects/definitions/create")
async def create_metaobject_definition(request: Request):
    try:
        body = await request.json()
        name = (body.get("name") or "").strip()
        type_key = (body.get("type") or "").strip()
        description = (body.get("description") or "").strip()
        storefront = body.get("storefront", True)
        fields = body.get("fields", [])
        
        if not name:
            return JSONResponse({"success": False, "message": "Vui lòng nhập Tên Metaobject (Name)."}, status_code=400)
            
        if not type_key:
            clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name).lower().strip()
            type_key = re.sub(r'\s+', '_', clean_name)
            
        # Chuẩn hóa type_key: chỉ chữ thường, số và dấu gạch dưới
        type_key = re.sub(r'[^a-z0-9_]', '_', type_key.lower()).strip('_')
        if not type_key:
            return JSONResponse({"success": False, "message": "Mã định dạng (Type) không hợp lệ."}, status_code=400)

        cleaned_field_definitions = []
        for f in fields:
            k = (f.get("key") or "").strip().lower()
            k = re.sub(r'[^a-z0-9_]', '_', k).strip('_')
            fn = (f.get("name") or "").strip() or k
            ft = (f.get("type") or "single_line_text_field").strip()
            req = bool(f.get("required", False))
            desc = (f.get("description") or "").strip()
            
            if k:
                field_obj = {
                    "key": k,
                    "name": fn,
                    "type": ft,
                    "required": req
                }
                if desc:
                    field_obj["description"] = desc
                cleaned_field_definitions.append(field_obj)
                
        if not cleaned_field_definitions:
            return JSONResponse({"success": False, "message": "Metaobject cần ít nhất 1 trường dữ liệu (Field) có key hợp lệ."}, status_code=400)
            
        mutation = """
        mutation createDefinition($definition: MetaobjectDefinitionCreateInput!) {
          metaobjectDefinitionCreate(definition: $definition) {
            metaobjectDefinition {
              id
              name
              type
              metaobjectsCount
            }
            userErrors {
              field
              message
              code
            }
          }
        }
        """
        
        definition_input = {
            "name": name,
            "type": type_key,
            "access": {
                "storefront": "PUBLIC_READ" if storefront else "NONE"
            },
            "fieldDefinitions": cleaned_field_definitions
        }
        if description:
            definition_input["description"] = description
            
        text_field = next((f["key"] for f in cleaned_field_definitions if "text" in f["type"]), None)
        if text_field:
            definition_input["displayNameKey"] = text_field
        elif cleaned_field_definitions:
            definition_input["displayNameKey"] = cleaned_field_definitions[0]["key"]

        res = requests.post(GRAPHQL_URL, json={
            "query": mutation,
            "variables": {
                "definition": definition_input
            }
        }, headers=HEADERS)
        res.raise_for_status()
        data = res.json()
        
        if "errors" in data:
            return JSONResponse({"success": False, "message": str(data["errors"])}, status_code=400)
            
        create_res = data.get("data", {}).get("metaobjectDefinitionCreate", {})
        user_errors = create_res.get("userErrors", [])
        if user_errors:
            error_msgs = [e.get("message", "Lỗi không xác định") for e in user_errors]
            return JSONResponse({"success": False, "message": "; ".join(error_msgs), "errors": user_errors}, status_code=400)
            
        created_def = create_res.get("metaobjectDefinition")
        return JSONResponse({"success": True, "message": "Đã tạo mới Metaobject thành công trên Shopify!", "definition": created_def})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi hệ thống: {str(e)}"}, status_code=500)


TYPE_TO_HANDLE = {
    "CONTACT_INFORMATION": "contact-information",
    "LEGAL_NOTICE": "legal-notice",
    "PRIVACY_POLICY": "privacy-policy",
    "REFUND_POLICY": "refund-policy",
    "SHIPPING_POLICY": "shipping-policy",
    "TERMS_OF_SERVICE": "terms-of-service",
    "TERMS_OF_SALE": "terms-of-sale",
    "SUBSCRIPTION_POLICY": "subscription-policy"
}

POLICY_DISPLAY_TITLES = {
    "CONTACT_INFORMATION": "Contact information",
    "REFUND_POLICY": "Return and refund policy",
    "SHIPPING_POLICY": "Shipping policy",
    "CANCEL_ORDER": "Cancel Order"
}

def get_store_policies():
    query = """
    query {
      shop {
        shopPolicies {
          id
          title
          body
          type
          url
          createdAt
          updatedAt
        }
      }
    }
    """
    res = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    raw_policies = data.get("data", {}).get("shop", {}).get("shopPolicies", [])

    rest_url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/policies.json"
    rest_map = {}
    try:
        r_rest = requests.get(rest_url, headers=HEADERS, timeout=10)
        if r_rest.status_code == 200:
            for p in r_rest.json().get("policies", []):
                h = p.get("handle")
                t = (p.get("title") or "").strip().lower()
                if h:
                    rest_map[h] = p
                if t:
                    rest_map[t] = p
    except Exception as e:
        print(f"Error fetching REST policies: {e}")

    policies = []
    for item in raw_policies:
        p_type = item.get("type", "")
        handle = TYPE_TO_HANDLE.get(p_type, "")
        raw_title = item.get("title", "")
        body = item.get("body", "") or ""

        rest_info = rest_map.get(handle) or rest_map.get(raw_title.lower()) or {}
        storefront_url = rest_info.get("url")
        if not storefront_url and handle:
            storefront_url = f"https://{SHOPIFY_SHOP}.myshopify.com/policies/{handle}"
            
        actual_handle = rest_info.get("handle") or handle

        # Ánh xạ tên chính sách (Title) theo yêu cầu hiển thị
        display_title = raw_title
        if p_type in POLICY_DISPLAY_TITLES:
            display_title = POLICY_DISPLAY_TITLES[p_type]
        elif raw_title.strip().lower() == "contact":
            display_title = "Contact information"
        elif raw_title.strip().lower() in ["refund", "refund policy"]:
            display_title = "Return and refund policy"
        elif raw_title.strip().lower() == "shipping":
            display_title = "Shipping policy"

        updated_at = item.get("updatedAt", "")
        formatted_date = ""
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                formatted_date = updated_at[:16].replace("T", " ")

        policies.append({
            "id": item.get("id"),
            "title": display_title,
            "type": p_type,
            "handle": actual_handle,
            "body": body,
            "char_count": len(body),
            "word_count": len(body.split()),
            "url": item.get("url"),
            "storefront_url": storefront_url,
            "created_at": item.get("createdAt"),
            "updated_at": updated_at,
            "formatted_updated_at": formatted_date
        })

    # Bổ sung trang chính sách "Cancel Order" (/pages/modify-cancel-order)
    try:
        page_url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/pages.json?handle=modify-cancel-order"
        r_page = requests.get(page_url, headers=HEADERS, timeout=10)
        page_item = None
        if r_page.status_code == 200:
            pages = r_page.json().get("pages", [])
            if pages:
                page_item = pages[0]

        if page_item:
            p_id = page_item.get("id")
            body = page_item.get("body_html", "") or ""
            handle = page_item.get("handle", "modify-cancel-order")
            updated_at = page_item.get("updated_at", "")
            created_at = page_item.get("created_at", "")
        else:
            p_id = 165869846585
            body = ""
            local_doc = os.path.join(os.path.dirname(__file__), "..", "..", "doc", "policy", "public", "Modify and cancel order policy.html")
            if os.path.exists(local_doc):
                with open(local_doc, "r", encoding="utf-8") as f:
                    body = f.read()
            handle = "modify-cancel-order"
            updated_at = ""
            created_at = ""

        formatted_date = ""
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                formatted_date = updated_at[:16].replace("T", " ")

        policies.append({
            "id": f"gid://shopify/Page/{p_id}",
            "page_id": p_id,
            "title": "Cancel Order",
            "type": "CANCEL_ORDER",
            "handle": handle,
            "url_path": f"/pages/{handle}",
            "body": body,
            "char_count": len(body),
            "word_count": len(body.split()),
            "url": f"https://{SHOPIFY_SHOP}.myshopify.com/pages/{handle}",
            "storefront_url": f"https://{SHOPIFY_SHOP}.myshopify.com/pages/{handle}",
            "created_at": created_at,
            "updated_at": updated_at,
            "formatted_updated_at": formatted_date,
            "is_page": True
        })
    except Exception as e:
        print(f"Error fetching Cancel Order page: {e}")

    # Sort policies by standard order if desired, or keep Shopify order
    return policies


@app.get("/policies", response_class=HTMLResponse)
async def policies_page(request: Request):
    try:
        policies = get_store_policies()
        return templates.TemplateResponse(request=request, name="policies.html", context={
            "request": request,
            "policies": policies,
            "shop_name": SHOPIFY_SHOP
        })
    except Exception as e:
        return HTMLResponse(f"Lỗi tải danh sách chính sách (Policies): {str(e)}", status_code=500)


@app.get("/api/policies")
async def api_get_policies():
    try:
        policies = get_store_policies()
        return JSONResponse({"success": True, "policies": policies})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


class PolicyUpdateRequest(BaseModel):
    type: str
    body: str


@app.post("/api/policies/update")
async def api_update_policy(payload: PolicyUpdateRequest):
    try:
        p_type = payload.type.strip()
        body = payload.body

        if not p_type:
            return JSONResponse({"success": False, "message": "Mã loại chính sách (type) là bắt buộc."}, status_code=400)

        # Xử lý cập nhật cho chính sách dạng Page như CANCEL_ORDER
        if p_type == "CANCEL_ORDER":
            page_id = 165869846585
            page_url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/pages/{page_id}.json"
            put_res = requests.put(page_url, json={"page": {"id": page_id, "body_html": body}}, headers=HEADERS, timeout=15)
            if put_res.status_code not in (200, 201):
                # Tìm lại ID qua handle nếu cần
                search_url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/pages.json?handle=modify-cancel-order"
                s_res = requests.get(search_url, headers=HEADERS, timeout=10)
                if s_res.status_code == 200 and s_res.json().get("pages"):
                    found_id = s_res.json()["pages"][0]["id"]
                    put_res = requests.put(f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/pages/{found_id}.json", json={"page": {"id": found_id, "body_html": body}}, headers=HEADERS, timeout=15)

            if put_res.status_code in (200, 201):
                updated_page = put_res.json().get("page", {})
                return JSONResponse({
                    "success": True,
                    "message": "Đã lưu chính sách 'Cancel Order' thành công vào store!",
                    "policy": {
                        "id": f"gid://shopify/Page/{updated_page.get('id', page_id)}",
                        "title": "Cancel Order",
                        "type": "CANCEL_ORDER",
                        "body": updated_page.get("body_html", body),
                        "updatedAt": updated_page.get("updated_at")
                    }
                })
            else:
                return JSONResponse({"success": False, "message": f"Lỗi cập nhật trang Cancel Order: {put_res.text}"}, status_code=400)

        mutation = """
        mutation updateShopPolicy($shopPolicy: ShopPolicyInput!) {
          shopPolicyUpdate(shopPolicy: $shopPolicy) {
            shopPolicy {
              id
              title
              type
              body
              url
              updatedAt
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        res = requests.post(GRAPHQL_URL, json={
            "query": mutation,
            "variables": {
                "shopPolicy": {
                    "type": p_type,
                    "body": body
                }
            }
        }, headers=HEADERS)
        res.raise_for_status()
        data = res.json()

        if "errors" in data:
            return JSONResponse({"success": False, "message": str(data["errors"])}, status_code=400)

        update_res = data.get("data", {}).get("shopPolicyUpdate", {})
        user_errors = update_res.get("userErrors", [])
        if user_errors:
            error_msgs = [e.get("message", "Lỗi cập nhật") for e in user_errors]
            return JSONResponse({"success": False, "message": "; ".join(error_msgs), "errors": user_errors}, status_code=400)

        updated_policy = update_res.get("shopPolicy")
        if updated_policy:
            p_type_ret = updated_policy.get("type", "")
            raw_t = updated_policy.get("title", "")
            if p_type_ret in POLICY_DISPLAY_TITLES:
                updated_policy["title"] = POLICY_DISPLAY_TITLES[p_type_ret]
            elif raw_t.strip().lower() == "contact":
                updated_policy["title"] = "Contact information"
            elif raw_t.strip().lower() in ["refund", "refund policy"]:
                updated_policy["title"] = "Return and refund policy"
            elif raw_t.strip().lower() == "shipping":
                updated_policy["title"] = "Shipping policy"

        return JSONResponse({
            "success": True,
            "message": f"Đã lưu chính sách '{updated_policy.get('title') if updated_policy else ''}' thành công vào store!",
            "policy": updated_policy
        })
    except Exception as e:
        return JSONResponse({"success": False, "message": f"Lỗi hệ thống: {str(e)}"}, status_code=500)


# =====================================================================
# PRODUCT LOGO MANAGEMENT ROUTES & APIS
# =====================================================================

@app.get("/update-product-logo", response_class=HTMLResponse)
async def update_product_logo_page(request: Request):
    return templates.TemplateResponse(request=request, name="update_product_logo.html", context={"request": request})


# =====================================================================
# PROXY STATUS & CONTROL ROUTES
# =====================================================================

@app.get("/api/proxy/status")
async def get_proxy_status():
    cfg = load_proxy_config()
    return JSONResponse({
        "success": True,
        "enabled": cfg.get("enabled", False),
        "proxy_url": cfg.get("proxy_url"),
        "proxy_ip": cfg.get("proxy_ip", "185.124.63.174"),
        "is_stable": cfg.get("is_stable", False),
        "last_status": cfg.get("last_status", "unknown"),
        "last_latency_ms": cfg.get("last_latency_ms", 0),
        "last_checked_at": cfg.get("last_checked_at"),
        "last_error": cfg.get("last_error"),
        "geo": cfg.get("geo")
    })


@app.post("/api/proxy/toggle")
async def toggle_proxy(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    
    enabled = bool(payload.get("enabled", False))
    cfg = load_proxy_config()
    cfg["enabled"] = enabled
    
    if enabled:
        now = datetime.now()
        is_ok, latency, err = test_proxy_connectivity(cfg.get("proxy_url"), timeout=8)
        cfg["is_stable"] = is_ok
        cfg["last_status"] = "stable" if is_ok else "unstable"
        cfg["last_latency_ms"] = latency
        cfg["last_checked_at"] = now.isoformat()
        cfg["last_error"] = err if not is_ok else None
        if is_ok:
            geo = fetch_proxy_egress_geo(cfg.get("proxy_url"), timeout=6)
            if geo:
                cfg["geo"] = geo
        save_proxy_config(cfg)
    else:
        save_proxy_config(cfg)
        
    return JSONResponse({
        "success": True,
        "enabled": cfg.get("enabled", False),
        "proxy_url": cfg.get("proxy_url"),
        "proxy_ip": cfg.get("proxy_ip", "185.124.63.174"),
        "is_stable": cfg.get("is_stable", False),
        "last_status": cfg.get("last_status", "unknown"),
        "last_latency_ms": cfg.get("last_latency_ms", 0),
        "last_checked_at": cfg.get("last_checked_at"),
        "last_error": cfg.get("last_error"),
        "geo": cfg.get("geo")
    })


@app.post("/api/proxy/check")
async def check_proxy():
    cfg = load_proxy_config()
    now = datetime.now()
    is_ok, latency, err = test_proxy_connectivity(cfg.get("proxy_url"), timeout=8)
    cfg["is_stable"] = is_ok
    cfg["last_status"] = "stable" if is_ok else "unstable"
    cfg["last_latency_ms"] = latency
    cfg["last_checked_at"] = now.isoformat()
    cfg["last_error"] = err if not is_ok else None
    
    if is_ok:
        geo = fetch_proxy_egress_geo(cfg.get("proxy_url"), timeout=6)
        if geo:
            cfg["geo"] = geo
            
    save_proxy_config(cfg)
    
    return JSONResponse({
        "success": True,
        "enabled": cfg.get("enabled", False),
        "proxy_url": cfg.get("proxy_url"),
        "proxy_ip": cfg.get("proxy_ip", "185.124.63.174"),
        "is_stable": cfg.get("is_stable", False),
        "last_status": cfg.get("last_status", "unknown"),
        "last_latency_ms": cfg.get("last_latency_ms", 0),
        "last_checked_at": cfg.get("last_checked_at"),
        "last_error": cfg.get("last_error"),
        "geo": cfg.get("geo")
    })


@app.get("/api/logo-updater/store-info")
async def get_logo_updater_store_info():
    creds = get_logo_updater_credentials()
    shop = creds["shop"]
    shop_domain = f"{shop}.myshopify.com" if not shop.endswith(".myshopify.com") else shop
    proxy_cfg = load_proxy_config()
    proxy_enabled = bool(proxy_cfg.get("enabled", False))
    cred_type = creds["type"]
    is_custom = creds["is_custom"]
    
    custom_cfg = load_logo_updater_config()
    shop_name = custom_cfg.get("shop_name") if is_custom and custom_cfg.get("shop_name") else shop.replace(".myshopify.com", "").title()
    
    if not proxy_enabled:
        status_label = "Mặc định Server • Trực tiếp"
    elif is_custom:
        status_label = "Cấu hình riêng • Proxy US 🇺🇸"
    else:
        status_label = "Mặc định Server • Proxy US 🇺🇸"

    return JSONResponse({
        "success": True,
        "credentials_type": cred_type,
        "is_custom": is_custom,
        "proxy_enabled": proxy_enabled,
        "shop_domain": shop_domain,
        "shop_name": shop_name,
        "status_label": status_label
    })


@app.get("/api/settings/logo-updater")
async def get_settings_logo_updater():
    cfg = load_logo_updater_config()
    return JSONResponse({
        "success": True,
        "config": {
            "shop_domain": cfg.get("shop_domain", ""),
            "shop_name": cfg.get("shop_name", ""),
            "client_id": cfg.get("client_id", ""),
            "client_secret_masked": mask_secret(cfg.get("client_secret", "")),
            "access_token_masked": mask_secret(cfg.get("access_token", "")),
            "has_secret": bool(cfg.get("client_secret")),
            "has_token": bool(cfg.get("access_token")),
            "is_custom": cfg.get("is_custom", False),
            "updated_at": cfg.get("updated_at")
        },
        "default_shop": f"{SHOPIFY_SHOP}.myshopify.com"
    })


@app.post("/api/settings/logo-updater")
async def save_settings_logo_updater(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"success": False, "message": "Dữ liệu JSON không hợp lệ"}, status_code=400)

    existing_cfg = load_logo_updater_config()
    
    raw_shop = payload.get("shop_domain", "").strip()
    shop = clean_shopify_domain(raw_shop) or clean_shopify_domain(SHOPIFY_SHOP)
    
    raw_token = payload.get("access_token", "").strip()
    if raw_token and not raw_token.startswith("****") and not "..." in raw_token:
        access_token = raw_token
    else:
        access_token = existing_cfg.get("access_token", "")
        
    if not access_token:
        return JSONResponse({"success": False, "message": "Access Token không được để trống khi lưu cấu hình riêng."}, status_code=400)

    raw_client_id = payload.get("client_id", "").strip()
    client_id = raw_client_id if raw_client_id else existing_cfg.get("client_id", "")
    
    raw_secret = payload.get("client_secret", "").strip()
    if raw_secret and not raw_secret.startswith("****") and not "..." in raw_secret:
        client_secret = raw_secret
    else:
        client_secret = existing_cfg.get("client_secret", "")

    # Xác thực token mới với Shopify API /shop.json
    test_url = f"https://{shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/shop.json"
    test_headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    try:
        proxies = None
        proxy_cfg = load_proxy_config()
        if proxy_cfg.get("enabled"):
            try:
                proxies = get_shopify_request_proxies()
            except ProxySafetyException as pse:
                return JSONResponse({
                    "success": False,
                    "message": f"Proxy Gateway đang BẬT nhưng mất kết nối/không ổn định! Đã chặn request đến Shopify để bảo vệ gian hàng khỏi rò rỉ IP."
                }, status_code=503)
            except Exception as pe:
                return JSONResponse({
                    "success": False,
                    "message": f"Lỗi khởi tạo Proxy Gateway: {str(pe)}. Đã chặn request để bảo vệ an toàn."
                }, status_code=503)
        
        resp = requests.get(test_url, headers=test_headers, proxies=proxies, timeout=12)
        if resp.status_code == 200:
            shop_data = resp.json().get("shop", {})
            shop_name = shop_data.get("name", shop.capitalize())
            myshopify_domain = shop_data.get("myshopify_domain", f"{shop}.myshopify.com")
            
            new_cfg = {
                "shop_domain": myshopify_domain,
                "shop_name": shop_name,
                "client_id": client_id,
                "client_secret": client_secret,
                "access_token": access_token,
                "is_custom": True,
                "updated_at": datetime.now().isoformat()
            }
            save_logo_updater_config(new_cfg)
            return JSONResponse({
                "success": True,
                "message": f"Xác thực thành công! Đã kết nối tới store '{shop_name}' ({myshopify_domain}) và lưu cấu hình Loại 2.",
                "shop_name": shop_name,
                "shop_domain": myshopify_domain
            })
        elif resp.status_code in (401, 403):
            return JSONResponse({
                "success": False,
                "message": f"Shopify từ chối xác thực (HTTP {resp.status_code}): Access Token không hợp lệ hoặc không có quyền truy cập store {shop}."
            }, status_code=400)
        else:
            return JSONResponse({
                "success": False,
                "message": f"Shopify trả về mã lỗi HTTP {resp.status_code}: {resp.text}"
            }, status_code=400)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Không thể kết nối đến Shopify để kiểm tra credentials: {str(e)}"
        }, status_code=500)



@app.post("/api/settings/logo-updater/reset")
async def reset_settings_logo_updater():
    reset_cfg = {
        "shop_domain": "",
        "shop_name": "",
        "client_id": "",
        "client_secret": "",
        "access_token": "",
        "is_custom": False,
        "updated_at": datetime.now().isoformat()
    }
    save_logo_updater_config(reset_cfg)
    return JSONResponse({
        "success": True,
        "message": "Đã khôi phục về trạng thái mặc định server (Loại 1)."
    })


def fetch_product_with_media_by_id(prod_id: str):
    clean_id = str(prod_id).strip()
    if not clean_id.startswith("gid://shopify/Product/"):
        clean_id = f"gid://shopify/Product/{clean_id}"
    query = """
    query getProductMediaById($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        tags
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
    """
    try:
        creds = get_logo_updater_credentials()
        proxies = get_shopify_request_proxies()
        res = requests.post(creds["graphql_url"], json={"query": query, "variables": {"id": clean_id}}, headers=creds["headers"], proxies=proxies, timeout=15)
        if res.ok:
            data = res.json()
            return data.get("data", {}).get("product")
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        mark_proxy_unstable(str(pe))
        raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
    except ProxySafetyException:
        raise
    except Exception as e:
        print(f"Error fetching product by ID {prod_id}: {e}")
        if "CHỐT CHẶN AN TOÀN" in str(e):
            raise ProxySafetyException(str(e))
    return None


def fetch_product_with_media_by_handle(handle: str):
    clean_handle = str(handle).strip()
    query = """
    query getProductMediaByHandle($handle: String!) {
      productByHandle(handle: $handle) {
        id
        title
        handle
        tags
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
    """
    try:
        creds = get_logo_updater_credentials()
        proxies = get_shopify_request_proxies()
        res = requests.post(creds["graphql_url"], json={"query": query, "variables": {"handle": clean_handle}}, headers=creds["headers"], proxies=proxies, timeout=15)
        if res.ok:
            data = res.json()
            return data.get("data", {}).get("productByHandle")
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        mark_proxy_unstable(str(pe))
        raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
    except ProxySafetyException:
        raise
    except Exception as e:
        print(f"Error fetching product by handle {handle}: {e}")
        if "CHỐT CHẶN AN TOÀN" in str(e):
            raise ProxySafetyException(str(e))
    return None


def get_image_position(clean_prod_id: str, media_or_image_id: str, image_url: str = None) -> int:
    clean_id = str(media_or_image_id).split("/")[-1].strip() if media_or_image_id else ""
    try:
        creds = get_logo_updater_credentials()
        proxies = get_shopify_request_proxies()
        list_url = f"https://{creds['shop']}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/products/{clean_prod_id}/images.json"
        res = requests.get(list_url, headers=creds["headers"], proxies=proxies, timeout=15)
        if res.ok:
            images = res.json().get("images", [])
            for img in images:
                gid = img.get("admin_graphql_api_id", "")
                if str(img.get("id")) == clean_id or gid == media_or_image_id or (clean_id and gid.endswith(f"/{clean_id}")):
                    return img.get("position", 1)
                if image_url:
                    fn1 = image_url.split("/")[-1].split("?")[0]
                    fn2 = img.get("src", "").split("/")[-1].split("?")[0]
                    if fn1 and fn2 and fn1 == fn2:
                        return img.get("position", 1)
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        mark_proxy_unstable(str(pe))
        raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
    except ProxySafetyException:
        raise
    except Exception as e:
        print(f"Error getting image position: {e}")
        if "CHỐT CHẶN AN TOÀN" in str(e):
            raise ProxySafetyException(str(e))
    return 1


def delete_shopify_image_or_media(clean_prod_id: str, media_or_image_id: str) -> bool:
    clean_id = str(media_or_image_id).split("/")[-1].strip()
    if not clean_id:
        return False

    prod_gid = f"gid://shopify/Product/{clean_prod_id}"
    del_media_gid = media_or_image_id if str(media_or_image_id).startswith("gid://shopify/MediaImage/") else f"gid://shopify/MediaImage/{clean_id}"

    creds = get_logo_updater_credentials()
    graphql_url = creds["graphql_url"]
    headers = creds["headers"]
    shop = creds["shop"]

    # 1. Try GraphQL productDeleteMedia
    del_mutation = """
    mutation productDeleteMedia($mediaIds: [ID!]!, $productId: ID!) {
      productDeleteMedia(mediaIds: $mediaIds, productId: $productId) {
        deletedMediaIds
        deletedProductImageIds
        userErrors {
          field
          message
        }
      }
    }
    """
    try:
        proxies = get_shopify_request_proxies()
        res = requests.post(graphql_url, json={
            "query": del_mutation,
            "variables": {"mediaIds": [del_media_gid], "productId": prod_gid}
        }, headers=headers, proxies=proxies, timeout=15)
        if res.ok:
            data = res.json()
            if not data.get("errors"):
                pdm = data.get("data", {}).get("productDeleteMedia", {})
                if not pdm.get("userErrors") and (pdm.get("deletedMediaIds") or pdm.get("deletedProductImageIds")):
                    return True
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        mark_proxy_unstable(str(pe))
        raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
    except ProxySafetyException:
        raise
    except Exception as e:
        print(f"GraphQL delete media exception: {e}")
        if "CHỐT CHẶN AN TOÀN" in str(e):
            raise ProxySafetyException(str(e))

    # 2. Try REST API delete: DELETE /products/{clean_prod_id}/images/{clean_id}.json
    try:
        proxies = get_shopify_request_proxies()
        rest_del_url = f"https://{shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/products/{clean_prod_id}/images/{clean_id}.json"
        res_rest = requests.delete(rest_del_url, headers=headers, proxies=proxies, timeout=15)
        if res_rest.ok:
            return True
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        mark_proxy_unstable(str(pe))
        raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
    except ProxySafetyException:
        raise
    except Exception as e:
        print(f"REST delete image exception: {e}")
        if "CHỐT CHẶN AN TOÀN" in str(e):
            raise ProxySafetyException(str(e))

    # 3. Fallback: Lookup image by GraphQL GID or clean_id from products images list
    try:
        proxies = get_shopify_request_proxies()
        list_url = f"https://{shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/products/{clean_prod_id}/images.json"
        res_list = requests.get(list_url, headers=headers, proxies=proxies, timeout=15)
        if res_list.ok:
            imgs = res_list.json().get("images", [])
            for img in imgs:
                img_gid = img.get("admin_graphql_api_id", "")
                if str(img.get("id")) == clean_id or img_gid == media_or_image_id or img_gid.split("/")[-1] == clean_id:
                    del_id = img["id"]
                    del_url = f"https://{shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/products/{clean_prod_id}/images/{del_id}.json"
                    r = requests.delete(del_url, headers=headers, proxies=proxies, timeout=15)
                    if r.ok:
                        return True
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        mark_proxy_unstable(str(pe))
        raise ProxySafetyException("CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng.")
    except ProxySafetyException:
        raise
    except Exception as e:
        print(f"Fallback delete exception: {e}")
        if "CHỐT CHẶN AN TOÀN" in str(e):
            raise ProxySafetyException(str(e))

    return False


@app.post("/api/products/batch-media")
async def batch_media_products(request: Request):
    try:
        # Chốt chặn an toàn Proxy Gateway
        get_shopify_request_proxies()
    except Exception as pe:
        return JSONResponse({"success": False, "error": str(pe)}, status_code=503)

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    id_type = payload.get("id_type", "id")
    raw_identifiers = payload.get("identifiers", [])
    if isinstance(raw_identifiers, str):
        identifiers = [x.strip() for x in re.split(r"[\r\n,]+", raw_identifiers) if x.strip()]
    elif isinstance(raw_identifiers, list):
        identifiers = []
        for item in raw_identifiers:
            if isinstance(item, str):
                for part in re.split(r"[\r\n,]+", item):
                    if part.strip():
                        identifiers.append(part.strip())
            elif item is not None:
                identifiers.append(str(item).strip())
    else:
        identifiers = []

    seen = set()
    unique_identifiers = []
    for ident in identifiers:
        # Clean URL if user pasted a URL
        if "http://" in ident or "https://" in ident:
            ident = ident.split("?")[0].rstrip("/").split("/")[-1]
        if ident and ident not in seen:
            seen.add(ident)
            unique_identifiers.append(ident)

    results = []
    try:
        for ident in unique_identifiers:
            prod = None
            if id_type == "handle":
                prod = fetch_product_with_media_by_handle(ident)
                if not prod and ident.isdigit():
                    prod = fetch_product_with_media_by_id(ident)
            else:
                prod = fetch_product_with_media_by_id(ident)
                if not prod and not ident.isdigit():
                    prod = fetch_product_with_media_by_handle(ident)

            if not prod:
                continue

            gid = prod.get("id", "")
            clean_prod_id = gid.split("/")[-1]
            tags = prod.get("tags", [])
            is_logo_updated = "logo-updated" in tags

            media_list = []
            manifest_file = os.path.join("backups", clean_prod_id, "manifest.json")
            manifest = {}
            if os.path.exists(manifest_file):
                try:
                    with open(manifest_file, "r", encoding="utf-8") as mf:
                        manifest = json.load(mf)
                except Exception:
                    manifest = {}

            edges = prod.get("media", {}).get("edges", [])
            for pos_idx, edge in enumerate(edges, start=1):
                node = edge.get("node", {})
                m_id = node.get("id", "")
                clean_m_id = m_id.split("/")[-1]
                url = node.get("image", {}).get("url") or (node.get("preview", {}).get("image", {}).get("url") if node.get("preview") else None)
                if not url:
                    continue

                orig_m_id = clean_m_id
                for k, v in manifest.items():
                    if v.get("new_image_id") == clean_m_id or v.get("new_media_raw_id") == clean_m_id or v.get("restored_image_id") == clean_m_id or v.get("restored_media_raw_id") == clean_m_id or k == clean_m_id:
                        orig_m_id = k
                        break

                backup_rel = f"backups/{clean_prod_id}/{orig_m_id}_orig.jpg"
                has_backup = os.path.exists(backup_rel) and os.path.getsize(backup_rel) > 0

                # Kiểm tra trạng thái đã gắn logo của từng media
                is_logo_applied = False
                if orig_m_id in manifest:
                    m_info = manifest[orig_m_id]
                    if m_info.get("is_applied") is True:
                        is_logo_applied = True
                    elif m_info.get("is_applied") is False:
                        is_logo_applied = False
                    elif m_info.get("applied_at") and not m_info.get("restored_at"):
                        is_logo_applied = True

                media_list.append({
                    "id": m_id,
                    "raw_id": clean_m_id,
                    "orig_raw_id": orig_m_id,
                    "position": pos_idx,
                    "url": url,
                    "has_backup": has_backup,
                    "backup_url": f"/{backup_rel}" if has_backup else None,
                    "is_logo_applied": is_logo_applied
                })

            results.append({
                "id": gid,
                "raw_id": clean_prod_id,
                "handle": prod.get("handle", ""),
                "title": prod.get("title", ""),
                "tags": tags,
                "is_logo_updated": is_logo_updated,
                "media": media_list
            })
    except ProxySafetyException as pse:
        return JSONResponse({"success": False, "error": str(pse)}, status_code=503)

    return JSONResponse({"success": True, "products": results})


@app.post("/api/products/backup-media")
async def backup_product_media(request: Request):
    try:
        # Chốt chặn an toàn Proxy Gateway
        proxies = get_shopify_request_proxies()
    except (ProxySafetyException, Exception) as pe:
        if "CHỐT CHẶN AN TOÀN" in str(pe) or isinstance(pe, ProxySafetyException):
            return JSONResponse({"success": False, "error": str(pe)}, status_code=503)
        return JSONResponse({"success": False, "error": str(pe)}, status_code=500)

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "Invalid JSON body"}, status_code=400)

    product_id = payload.get("product_id", "")
    media_id = payload.get("media_id", "")
    orig_media_id = payload.get("orig_media_id", "")
    image_url = payload.get("image_url", "")
    position = payload.get("position")
    product_title = payload.get("product_title", "")

    if not product_id or not media_id or not image_url:
        return JSONResponse({"success": False, "error": "Thiếu thông tin product_id, media_id hoặc image_url"}, status_code=400)

    clean_prod_id = str(product_id).split("/")[-1].strip()
    clean_media_id = str(media_id).split("/")[-1].strip()
    clean_orig_id = str(orig_media_id).split("/")[-1].strip() if orig_media_id else clean_media_id

    try:
        if position is None:
            position = get_image_position(clean_prod_id, media_id)
    except ProxySafetyException as pse:
        return JSONResponse({"success": False, "error": str(pse)}, status_code=503)

    target_dir = os.path.join("backups", clean_prod_id)
    os.makedirs(target_dir, exist_ok=True)

    manifest_file = os.path.join(target_dir, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception:
            manifest = {}

    # Tra cứu liên kết trong manifest để luôn bảo tồn đúng ID ảnh gốc ban đầu
    for k, v in manifest.items():
        if v.get("new_image_id") in [clean_media_id, clean_orig_id] or v.get("new_media_raw_id") in [clean_media_id, clean_orig_id] or v.get("restored_image_id") in [clean_media_id, clean_orig_id] or v.get("restored_media_raw_id") in [clean_media_id, clean_orig_id] or k in [clean_media_id, clean_orig_id]:
            clean_orig_id = k
            break

    backup_file = os.path.join(target_dir, f"{clean_orig_id}_orig.jpg")
    temp_file = os.path.join(target_dir, f"{clean_orig_id}_orig.tmp")

    # Nếu file tồn tại dưới tên clean_media_id thì chuyển sang sử dụng nó
    if not os.path.exists(backup_file):
        alt_cand = os.path.join(target_dir, f"{clean_media_id}_orig.jpg")
        if os.path.exists(alt_cand) and os.path.getsize(alt_cand) > 0:
            backup_file = alt_cand
            clean_orig_id = clean_media_id

    # Chốt bảo tồn vĩnh viễn: Nếu file backup đã tồn tại và hợp lệ trên VPS, xác thực và bảo toàn 100%
    if os.path.exists(backup_file) and os.path.getsize(backup_file) > 0:
        try:
            with open(backup_file, "rb") as f:
                existing_bytes = f.read()
            test_img = Image.open(io.BytesIO(existing_bytes))
            test_img.verify()
            bio_full = Image.open(io.BytesIO(existing_bytes))
            img_w, img_h = bio_full.size

            # Cập nhật position và product_title vào manifest nếu có
            if clean_orig_id in manifest:
                if position is not None:
                    manifest[clean_orig_id]["position"] = position
                if product_title:
                    manifest[clean_orig_id]["product_title"] = product_title
                with open(manifest_file, "w", encoding="utf-8") as mf:
                    json.dump(manifest, mf, indent=2, ensure_ascii=False)

            return JSONResponse({
                "success": True,
                "backup_url": f"/backups/{clean_prod_id}/{clean_orig_id}_orig.jpg",
                "file_size": len(existing_bytes),
                "dimensions": f"{img_w}x{img_h}",
                "position": position or manifest.get(clean_orig_id, {}).get("position", 1),
                "message": "Bản sao lưu gốc trên VPS đã tồn tại, được bảo tồn vĩnh viễn và xác thực hoàn hảo 100%!"
            })
        except Exception as e:
            print(f"Existing backup verification error: {e}, will re-download.")

    try:
        # 1. Download image from CDN (qua Proxy nếu bật)
        try:
            resp = requests.get(image_url, proxies=proxies, timeout=30)
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
            if proxies:
                mark_proxy_unstable(str(pe))
                return JSONResponse({"success": False, "error": "CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng."}, status_code=503)
            raise

        if resp.status_code != 200:
            raise Exception(f"Không thể tải ảnh từ Shopify CDN (HTTP {resp.status_code})")

        content = resp.content
        if len(content) == 0:
            raise Exception("Ảnh tải về từ Shopify CDN có kích thước 0 byte")

        # 2. Strict Verification with PIL
        bio = io.BytesIO(content)
        test_img = Image.open(bio)
        img_format = test_img.format
        img_width, img_height = test_img.size
        test_img.verify()

        # Re-check decoding fully
        bio2 = io.BytesIO(content)
        test_img2 = Image.open(bio2)
        test_img2.load()

        # 3. Write to temporary file and atomic rename
        with open(temp_file, "wb") as f:
            f.write(content)

        if os.path.exists(backup_file):
            os.remove(backup_file)
        os.rename(temp_file, backup_file)

        saved_size = os.path.getsize(backup_file)
        if saved_size == 0:
            raise Exception("File sao lưu ghi trên đĩa VPS có kích thước 0 bytes")

        # 4. Update manifest.json với trường position và product_title
        manifest[clean_orig_id] = {
            "product_id": clean_prod_id,
            "product_title": product_title,
            "media_id": clean_orig_id,
            "position": position,
            "original_url": image_url,
            "backup_file": f"backups/{clean_prod_id}/{clean_orig_id}_orig.jpg",
            "file_size": saved_size,
            "width": img_width,
            "height": img_height,
            "format": img_format,
            "created_at": datetime.now().isoformat()
        }
        with open(manifest_file, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2, ensure_ascii=False)

        return JSONResponse({
            "success": True,
            "backup_url": f"/backups/{clean_prod_id}/{clean_orig_id}_orig.jpg",
            "file_size": saved_size,
            "dimensions": f"{img_width}x{img_height}",
            "position": position,
            "message": "Đã sao lưu ảnh gốc vĩnh viễn và hoàn hảo trên VPS!"
        })
    except ProxySafetyException as pse:
        return JSONResponse({"success": False, "error": str(pse)}, status_code=503)
    except Exception as e:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        print(f"Error in backup_product_media: {e}")
        if "CHỐT CHẶN AN TOÀN" in str(e):
            return JSONResponse({"success": False, "error": str(e)}, status_code=503)
        return JSONResponse({"success": False, "error": f"LỖI SAO LƯU VPS (DỪNG BƯỚC 2): {str(e)}"}, status_code=500)


@app.post("/api/products/apply-media-update")
async def apply_media_update(request: Request):
    try:
        # Chốt chặn an toàn Proxy Gateway
        proxies = get_shopify_request_proxies()
    except Exception as pe:
        return JSONResponse({"success": False, "error": str(pe)}, status_code=503)

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "Invalid JSON body"}, status_code=400)

    product_id = payload.get("product_id", "")
    old_media_id = payload.get("old_media_id", "")
    orig_media_id = payload.get("orig_media_id", "")
    image_base64 = payload.get("image_base64", "")
    position = payload.get("position")

    if not product_id or not old_media_id or not image_base64:
        return JSONResponse({"success": False, "error": "Thiếu product_id, old_media_id hoặc image_base64"}, status_code=400)

    clean_prod_id = str(product_id).split("/")[-1].strip()
    clean_media_id = str(old_media_id).split("/")[-1].strip()
    clean_orig_id = str(orig_media_id).split("/")[-1].strip() if orig_media_id else clean_media_id

    # CHỐT AN TOÀN KÉP: Kiểm tra file backup trên VPS (thử cả orig_id, clean_media_id, và manifest)
    backup_file = os.path.join("backups", clean_prod_id, f"{clean_orig_id}_orig.jpg")
    manifest_file = os.path.join("backups", clean_prod_id, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception:
            manifest = {}

    if not os.path.exists(backup_file):
        # Thử fallback qua clean_media_id
        cand1 = os.path.join("backups", clean_prod_id, f"{clean_media_id}_orig.jpg")
        if os.path.exists(cand1) and os.path.getsize(cand1) > 0:
            backup_file = cand1
            clean_orig_id = clean_media_id
        else:
            # Thử lookup qua manifest
            for k, v in manifest.items():
                if v.get("new_image_id") in [clean_orig_id, clean_media_id] or v.get("new_media_raw_id") in [clean_orig_id, clean_media_id] or k in [clean_orig_id, clean_media_id]:
                    cand2 = os.path.join("backups", clean_prod_id, f"{k}_orig.jpg")
                    if os.path.exists(cand2) and os.path.getsize(cand2) > 0:
                        backup_file = cand2
                        clean_orig_id = k
                        break

    if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
        return JSONResponse({
            "success": False,
            "error": "CHỐT AN TOÀN CHẶN: Chưa có bản sao lưu gốc trên VPS! Vui lòng thực hiện Bước 1 trước."
        }, status_code=400)

    clean_b64 = re.sub(r"^data:image/[^;]+;base64,", "", image_base64.strip())

    # Xác định position chính xác của media cũ để duy trì nguyên vẹn thứ tự ảnh
    try:
        if position is None:
            position = get_image_position(clean_prod_id, old_media_id)
    except ProxySafetyException as pse:
        return JSONResponse({"success": False, "error": str(pse)}, status_code=503)

    # 1. Upload ảnh mới lên Shopify qua REST Admin API (qua Proxy nếu bật)
    creds = get_logo_updater_credentials()
    shop = creds["shop"]
    headers = creds["headers"]
    graphql_url = creds["graphql_url"]

    rest_url = f"https://{shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/products/{clean_prod_id}/images.json"
    upload_payload = {
        "image": {
            "attachment": clean_b64,
            "filename": f"wrydeco_logo_{clean_media_id}.jpg"
        }
    }
    if position is not None:
        upload_payload["image"]["position"] = position

    try:
        res = requests.post(rest_url, json=upload_payload, headers=headers, proxies=proxies, timeout=45)
        if not res.ok:
            return JSONResponse({"success": False, "error": f"Lỗi upload ảnh lên Shopify REST API: {res.text}"}, status_code=500)
        
        image_data = res.json().get("image", {})
        new_prod_img_id = image_data.get("id")
        new_media_gid = image_data.get("admin_graphql_api_id")
        new_image_url = image_data.get("src")
        new_raw_id = new_media_gid.split("/")[-1] if new_media_gid else str(new_prod_img_id)
        if not new_media_gid:
            new_media_gid = f"gid://shopify/MediaImage/{new_raw_id}"
    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
        if proxies:
            mark_proxy_unstable(str(pe))
            return JSONResponse({"success": False, "error": "CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng."}, status_code=503)
        return JSONResponse({"success": False, "error": f"Lỗi kết nối Shopify API: {str(pe)}"}, status_code=500)
    except ProxySafetyException as pse:
        return JSONResponse({"success": False, "error": str(pse)}, status_code=503)
    except Exception as e:
        if "CHỐT CHẶN AN TOÀN" in str(e):
            return JSONResponse({"success": False, "error": str(e)}, status_code=503)
        return JSONResponse({"success": False, "error": f"Lỗi kết nối Shopify API: {str(e)}"}, status_code=500)

    try:
        # 2. Xóa media cũ khỏi storefront Shopify (thử GraphQL rồi fallback REST)
        # TUYỆT ĐỐI BẢO TỒN VĨNH VIỄN FILE BACKUP TRÊN VPS!
        delete_shopify_image_or_media(clean_prod_id, old_media_id)

        # 3. Ghi nhận manifest
        try:
            target_k = clean_orig_id if clean_orig_id in manifest else clean_media_id
            if target_k not in manifest:
                manifest[target_k] = {
                    "product_id": clean_prod_id,
                    "media_id": target_k,
                    "position": position,
                    "backup_file": f"backups/{clean_prod_id}/{clean_orig_id}_orig.jpg"
                }
            if position is not None:
                manifest[target_k]["position"] = position
            manifest[target_k]["new_image_id"] = str(new_prod_img_id)
            manifest[target_k]["new_media_gid"] = new_media_gid
            manifest[target_k]["new_media_raw_id"] = str(new_raw_id)
            manifest[target_k]["new_image_url"] = new_image_url
            manifest[target_k]["is_applied"] = True
            manifest[target_k]["applied_at"] = datetime.now().isoformat()
            manifest[target_k].pop("restored_at", None)
            manifest[target_k].pop("restored_image_id", None)
            manifest[target_k].pop("restored_media_gid", None)
            manifest[target_k].pop("restored_media_raw_id", None)
            with open(manifest_file, "w", encoding="utf-8") as mf:
                json.dump(manifest, mf, indent=2, ensure_ascii=False)
        except Exception as me:
            print(f"Manifest update warning: {me}")

        # 4. Kiểm tra điều kiện gắn tag 'logo-updated'
        # Chỉ khi 100% media hình ảnh của sản phẩm đã được update logo thì mới gắn tag!
        prod_gid = f"gid://shopify/Product/{clean_prod_id}"
        prod_info = fetch_product_with_media_by_id(clean_prod_id)
        total_media_count = 0
        actual_applied_media_count = 0
        clean_old_id = str(old_media_id).split("/")[-1].strip()

        if prod_info:
            edges = prod_info.get("media", {}).get("edges", [])
            # Chỉ xét media hình ảnh (MediaImage), loại trừ old_media_id nếu Shopify chưa kịp gỡ khỏi index
            active_media_edges = [
                e for e in edges
                if e.get("node", {}).get("image", {}).get("url")
                and str(e.get("node", {}).get("id", "")).split("/")[-1].strip() != clean_old_id
            ]

            edge_raw_ids = {str(e.get("node", {}).get("id", "")).split("/")[-1].strip() for e in active_media_edges}
            if str(new_raw_id) not in edge_raw_ids:
                edge_raw_ids.add(str(new_raw_id))

            total_media_count = len(edge_raw_ids)

            for eid in edge_raw_ids:
                if eid == str(new_raw_id):
                    actual_applied_media_count += 1
                    continue
                is_edge_applied = False
                for k, v in manifest.items():
                    if k == eid or v.get("new_image_id") == eid or v.get("new_media_raw_id") == eid:
                        if v.get("is_applied") is True or (v.get("applied_at") and not v.get("restored_at")):
                            is_edge_applied = True
                            break
                if is_edge_applied:
                    actual_applied_media_count += 1

        all_media_updated = False
        if total_media_count > 0 and actual_applied_media_count >= total_media_count:
            try:
                tag_success, tag_msg = add_tags_to_product(prod_gid, ["logo-updated"], headers=headers, graphql_url=graphql_url)
                all_media_updated = True
            except ProxySafetyException:
                raise
            except Exception as te:
                print(f"Error adding tag logo-updated: {te}")
                all_media_updated = False
        else:
            # Nếu chưa đủ 100% media có logo: đảm bảo không gắn tag, gỡ bỏ nếu có
            try:
                if prod_info and "logo-updated" in prod_info.get("tags", []):
                    remove_tags_from_product(prod_gid, ["logo-updated"], headers=headers, graphql_url=graphql_url)
            except ProxySafetyException:
                raise
            except Exception as rem_err:
                print(f"Error removing tag logo-updated: {rem_err}")
            all_media_updated = False
    except ProxySafetyException as pse:
        return JSONResponse({"success": False, "error": str(pse)}, status_code=503)

    return JSONResponse({
        "success": True,
        "message": "Cập nhật ảnh có logo lên Shopify thành công. Bản sao lưu gốc trên VPS được bảo tồn vĩnh viễn!",
        "all_media_updated": all_media_updated,
        "applied_count": actual_applied_media_count,
        "total_media_count": total_media_count,
        "new_media": {
            "id": new_media_gid,
            "raw_id": str(new_raw_id),
            "product_image_id": str(new_prod_img_id),
            "orig_raw_id": str(clean_orig_id),
            "url": new_image_url,
            "position": position
        }
    })


@app.post("/api/products/rollback-media")
async def rollback_media(request: Request):
    try:
        # Chốt chặn an toàn Proxy Gateway
        proxies = get_shopify_request_proxies()
    except (ProxySafetyException, Exception) as pe:
        if "CHỐT CHẶN AN TOÀN" in str(pe) or isinstance(pe, ProxySafetyException):
            return JSONResponse({"success": False, "error": str(pe)}, status_code=503)
        return JSONResponse({"success": False, "error": str(pe)}, status_code=500)

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "Invalid JSON body"}, status_code=400)

    product_id = payload.get("product_id", "")
    current_media_id = payload.get("current_media_id", "")
    original_media_id = payload.get("original_media_id", "")

    if not product_id or not original_media_id:
        return JSONResponse({"success": False, "error": "Thiếu product_id hoặc original_media_id để rollback"}, status_code=400)

    clean_prod_id = str(product_id).split("/")[-1].strip()
    clean_orig_id = str(original_media_id).split("/")[-1].strip()

    backup_file = os.path.join("backups", clean_prod_id, f"{clean_orig_id}_orig.jpg")
    manifest_file = os.path.join("backups", clean_prod_id, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                manifest = json.load(mf)
        except Exception:
            manifest = {}
    
    # Fallback resolution 1: check manifest.json if clean_orig_id or current_media_id is mapped
    if not os.path.exists(backup_file):
        clean_cur_id = str(current_media_id).split("/")[-1].strip() if current_media_id else ""
        for k, v in manifest.items():
            if v.get("new_image_id") in [clean_orig_id, clean_cur_id] or v.get("new_media_raw_id") in [clean_orig_id, clean_cur_id] or k in [clean_orig_id, clean_cur_id]:
                cand = os.path.join("backups", clean_prod_id, f"{k}_orig.jpg")
                if os.path.exists(cand):
                    backup_file = cand
                    clean_orig_id = k
                    break

    # Fallback resolution 2: if only one backup exists in product folder
    if not os.path.exists(backup_file):
        prod_backup_dir = os.path.join("backups", clean_prod_id)
        if os.path.exists(prod_backup_dir):
            orig_files = [f for f in os.listdir(prod_backup_dir) if f.endswith("_orig.jpg")]
            if len(orig_files) == 1:
                backup_file = os.path.join(prod_backup_dir, orig_files[0])
                clean_orig_id = orig_files[0].replace("_orig.jpg", "")

    if not os.path.exists(backup_file):
        return JSONResponse({"success": False, "error": f"Không tìm thấy bản sao lưu gốc {backup_file} trên ổ cứng VPS!"}, status_code=404)

    try:
        with open(backup_file, "rb") as f:
            orig_bytes = f.read()
        orig_b64 = base64.b64encode(orig_bytes).decode("utf-8")

        # Xác định position ban đầu của ảnh cần thay thế
        try:
            pos = get_image_position(clean_prod_id, current_media_id)
        except ProxySafetyException as pse:
            return JSONResponse({"success": False, "error": str(pse)}, status_code=503)

        if (pos is None or pos == 1) and clean_orig_id in manifest:
            pos = manifest[clean_orig_id].get("position", pos or 1)

        # 1. Upload lại ảnh gốc từ VPS lên Shopify đúng vị trí ban đầu (qua Proxy nếu bật)
        creds = get_logo_updater_credentials()
        shop = creds["shop"]
        headers = creds["headers"]
        graphql_url = creds["graphql_url"]

        rest_url = f"https://{shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/products/{clean_prod_id}/images.json"
        upload_payload = {
            "image": {
                "attachment": orig_b64,
                "filename": f"restored_{clean_orig_id}.jpg",
                "position": pos
            }
        }
        try:
            res = requests.post(rest_url, json=upload_payload, headers=headers, proxies=proxies, timeout=45)
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as pe:
            if proxies:
                mark_proxy_unstable(str(pe))
                return JSONResponse({"success": False, "error": "CHỐT CHẶN AN TOÀN: Proxy đang BẬT nhưng mất kết nối/không ổn định! Đã chặn toàn bộ request đi đến Shopify để bảo vệ gian hàng."}, status_code=503)
            raise

        if not res.ok:
            return JSONResponse({"success": False, "error": f"Lỗi tải lại ảnh gốc: {res.text}"}, status_code=500)

        restored_img = res.json().get("image", {})
        restored_prod_img_id = restored_img.get("id")
        restored_media_gid = restored_img.get("admin_graphql_api_id")
        restored_url = restored_img.get("src")
        restored_raw_id = restored_media_gid.split("/")[-1] if restored_media_gid else str(restored_prod_img_id)
        if not restored_media_gid:
            restored_media_gid = f"gid://shopify/MediaImage/{restored_raw_id}"

        # 2. Xóa ảnh có logo hiện tại khỏi Shopify (thử GraphQL rồi fallback REST)
        if current_media_id:
            delete_shopify_image_or_media(clean_prod_id, current_media_id)

        # 3. Gỡ bỏ tag 'logo-updated'
        prod_gid = f"gid://shopify/Product/{clean_prod_id}"
        try:
            rem_success, rem_msg = remove_tags_from_product(prod_gid, ["logo-updated"], headers=headers, graphql_url=graphql_url)
        except ProxySafetyException:
            raise
        except Exception as te:
            print(f"Lỗi khi gỡ tag logo-updated: {te}")

        # 4. Ghi nhận manifest
        try:
            if clean_orig_id in manifest:
                manifest[clean_orig_id]["is_applied"] = False
                manifest[clean_orig_id]["restored_at"] = datetime.now().isoformat()
                if pos is not None:
                    manifest[clean_orig_id]["position"] = pos
                manifest[clean_orig_id]["restored_image_id"] = str(restored_prod_img_id)
                manifest[clean_orig_id]["restored_media_gid"] = restored_media_gid
                manifest[clean_orig_id]["restored_media_raw_id"] = str(restored_raw_id)
                manifest[clean_orig_id].pop("applied_at", None)
                manifest[clean_orig_id].pop("new_image_id", None)
                manifest[clean_orig_id].pop("new_media_gid", None)
                manifest[clean_orig_id].pop("new_media_raw_id", None)
                manifest[clean_orig_id].pop("new_image_url", None)
            with open(manifest_file, "w", encoding="utf-8") as mf:
                json.dump(manifest, mf, indent=2, ensure_ascii=False)
        except Exception:
            pass

        return JSONResponse({
            "success": True,
            "message": "Đã khôi phục ảnh gốc thành công và gỡ bỏ tag logo-updated khỏi sản phẩm! Bản sao lưu VPS được bảo tồn vĩnh viễn.",
            "all_media_updated": False,
            "is_logo_updated": False,
            "restored_media": {
                "id": restored_media_gid,
                "raw_id": str(restored_raw_id),
                "product_image_id": str(restored_prod_img_id),
                "orig_raw_id": str(clean_orig_id),
                "url": restored_url,
                "position": pos
            }
        })
    except ProxySafetyException as pse:
        return JSONResponse({"success": False, "error": str(pse)}, status_code=503)
    except Exception as e:
        if "CHỐT CHẶN AN TOÀN" in str(e):
            return JSONResponse({"success": False, "error": str(e)}, status_code=503)
        return JSONResponse({"success": False, "error": f"Lỗi khôi phục ảnh gốc: {str(e)}"}, status_code=500)


@app.get("/api/products/backups")
async def list_vps_backups():
    """Liệt kê danh sách tất cả các file media đã backup trên VPS"""
    try:
        backups_dir = "backups"
        if not os.path.exists(backups_dir):
            return JSONResponse({
                "success": True,
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_formatted": "0 KB",
                "total_products": 0,
                "backups": []
            })

        backup_list = []
        total_size_bytes = 0
        product_dirs = [d for d in os.listdir(backups_dir) if os.path.isdir(os.path.join(backups_dir, d))]

        for prod_id in product_dirs:
            p_dir = os.path.join(backups_dir, prod_id)
            manifest_file = os.path.join(p_dir, "manifest.json")
            manifest = {}
            if os.path.exists(manifest_file):
                try:
                    with open(manifest_file, "r", encoding="utf-8") as mf:
                        manifest = json.load(mf)
                except Exception:
                    manifest = {}

            # Quét tất cả file kết thúc bằng _orig.jpg trong thư mục sản phẩm
            files = [f for f in os.listdir(p_dir) if f.endswith("_orig.jpg")]
            for f in files:
                f_path = os.path.join(p_dir, f)
                try:
                    f_size = os.path.getsize(f_path)
                except Exception:
                    f_size = 0
                total_size_bytes += f_size

                clean_orig_id = f.replace("_orig.jpg", "")
                m_info = manifest.get(clean_orig_id, {})

                # Format dung lượng
                if f_size >= 1024 * 1024:
                    f_size_fmt = f"{f_size / (1024 * 1024):.2f} MB"
                else:
                    f_size_fmt = f"{f_size / 1024:.1f} KB"

                # Kích thước ảnh: ưu tiên manifest, nếu chưa có thì lấy từ PIL
                dims = ""
                if m_info.get("width") and m_info.get("height"):
                    dims = f"{m_info.get('width')}x{m_info.get('height')}"
                elif f_size > 0:
                    try:
                        with Image.open(f_path) as im:
                            dims = f"{im.width}x{im.height}"
                    except Exception:
                        dims = "--"

                # Thời gian tạo
                mtime = os.path.getmtime(f_path)
                created_iso = m_info.get("created_at") or datetime.fromtimestamp(mtime).isoformat()
                try:
                    dt = datetime.fromisoformat(created_iso)
                    created_display = dt.strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    created_display = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M:%S")

                backup_list.append({
                    "product_id": prod_id,
                    "product_title": m_info.get("product_title", ""),
                    "media_id": clean_orig_id,
                    "filename": f,
                    "file_url": f"/backups/{prod_id}/{f}",
                    "file_size": f_size,
                    "file_size_formatted": f_size_fmt,
                    "dimensions": dims,
                    "position": m_info.get("position"),
                    "is_applied": m_info.get("is_applied", False),
                    "created_at": created_iso,
                    "created_display": created_display,
                    "original_url": m_info.get("original_url", "")
                })

        # Sắp xếp mới nhất lên đầu
        backup_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        if total_size_bytes >= 1024 * 1024:
            total_size_fmt = f"{total_size_bytes / (1024 * 1024):.2f} MB"
        else:
            total_size_fmt = f"{total_size_bytes / 1024:.1f} KB"

        return JSONResponse({
            "success": True,
            "total_files": len(backup_list),
            "total_size_bytes": total_size_bytes,
            "total_size_formatted": total_size_fmt,
            "total_products": len(product_dirs),
            "backups": backup_list
        })
    except Exception as e:
        print(f"Error list_vps_backups: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)






