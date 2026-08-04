import os
import requests
import json

def get_token():
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("SHOPIFY_ADMIN_TOKEN="):
                return line.strip().split("=")[1].strip("'\"")
    return None

SHOP = 'wrydeco.myshopify.com'
TOKEN = get_token()
VERSION = '2026-07'

url = f"https://{SHOP}/admin/api/{VERSION}/products.json?limit=250"
headers = {
    "X-Shopify-Access-Token": TOKEN,
    "Content-Type": "application/json"
}

products = []
while url:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    products.extend(data.get("products", []))
    
    link_header = response.headers.get("Link")
    url = None
    if link_header:
        links = link_header.split(",")
        for link in links:
            if 'rel="next"' in link:
                url = link[link.find("<")+1:link.find(">")]

result = []
for product in products:
    options = product.get("options", [])
    
    size_custom = False
    wood_custom = False
    
    has_size = False
    has_wood = False
    
    for option in options:
        name = option.get("name", "").lower()
        is_size = "size" in name or "width" in name or "depth" in name
        is_wood = "wood" in name or "finish" in name
        
        if is_size:
            has_size = True
            for val in option.get("values", []):
                if "custom" in str(val).lower():
                    size_custom = True
        
        if is_wood:
            has_wood = True
            for val in option.get("values", []):
                if "custom" in str(val).lower():
                    wood_custom = True
                    
    missing_custom_in = []
    if has_size and not size_custom:
        missing_custom_in.append("Size")
    if has_wood and not wood_custom:
        missing_custom_in.append("Wood Finish")
        
    if missing_custom_in:
        result.append(product)

# Ensure tmp directory exists
os.makedirs(r"D:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-app\tmp", exist_ok=True)

with open(r"D:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-app\tmp\lack.md", "w", encoding="utf-8") as f:
    f.write("# Danh sách sản phẩm thiếu tùy chọn 'Custom'\n\n")
    f.write("| ID | Handle | Tên sản phẩm |\n")
    f.write("|---|---|---|\n")
    for r in result:
        f.write(f"| {r['id']} | {r['handle']} | {r['title']} |\n")

print(f"Successfully wrote {len(result)} products to tmp/lack.md")
