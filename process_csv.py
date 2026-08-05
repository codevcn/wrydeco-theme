import csv
import os
import requests
import shutil

# 1. Fetch categories
def get_categories(lang):
    url = f"https://raw.githubusercontent.com/Shopify/product-taxonomy/main/dist/{lang}/categories.txt"
    resp = requests.get(url)
    resp.raise_for_status()
    mapping = {}
    for line in resp.text.splitlines():
        if line.startswith("gid://"):
            parts = line.split(" : ", 1)
            if len(parts) == 2:
                mapping[parts[0].strip()] = parts[1].strip()
    return mapping

print("Fetching taxonomies...")
vi_cats = get_categories('vi')
en_cats = get_categories('en')

# Build vi -> en mapping
vi_to_en = {}
for gid, vi_name in vi_cats.items():
    if gid in en_cats:
        vi_to_en[vi_name] = en_cats[gid]

# Sort keys by length descending to avoid prefix trap
sorted_vi_keys = sorted(vi_to_en.keys(), key=len, reverse=True)

csv_path = 'temp/products_export.csv'
bak_path = csv_path + '.bak'

if not os.path.exists(bak_path):
    shutil.copy2(csv_path, bak_path)

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

empty_cats_titles = []

for row in rows:
    cat = row.get('Product Category', '').strip()
    
    if not cat:
        # Collect for guessing
        empty_cats_titles.append(row.get('Title', ''))
    else:
        # Translate
        # Using exact replacement
        new_cat = vi_to_en.get(cat)
        if new_cat:
            row['Product Category'] = new_cat
        else:
            # Fallback to replace longest substrings
            temp_cat = cat
            for vi_k in sorted_vi_keys:
                if vi_k in temp_cat:
                    temp_cat = temp_cat.replace(vi_k, vi_to_en[vi_k])
            row['Product Category'] = temp_cat

    # Clear Inventory Tracker and Qty
    row['Variant Inventory Tracker'] = ""
    row['Variant Inventory Qty'] = ""

print(f"Found {len(empty_cats_titles)} rows with empty Product Category")
for t in set(empty_cats_titles):
    print(" - " + t)

# Write back
with open(csv_path, 'w', encoding='utf-8', newline='\n') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(rows)

print("Done processing CSV.")
