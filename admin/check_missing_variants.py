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
    
    has_size = False
    has_wood_finish = False
    
    for option in options:
        name = option.get("name", "").lower()
        if "size" in name or "width" in name or "depth" in name or "height" in name or "length" in name:
            has_size = True
        if "wood" in name or "finish" in name:
            has_wood_finish = True
            
    if not has_size or not has_wood_finish:
        result.append({
            "id": product["id"],
            "title": product["title"],
            "missing_size": not has_size,
            "missing_wood": not has_wood_finish
        })

print("Found products:")
for r in result:
    print(f"- {r['title']} (ID: {r['id']}) - Missing Size: {r['missing_size']}, Missing Wood Finish: {r['missing_wood']}")
print(f"Total: {len(result)}")
