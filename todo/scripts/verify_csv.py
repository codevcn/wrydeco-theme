import csv
import json
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ref_file = r"todo/SEO/final/newest-product--10-percent--clean-variant-values--installation-400.csv"
new_file = r"todo/SEO/final/new-mirrors-product-listing.csv"

with open(ref_file, encoding="utf-8") as f:
    ref_headers = next(csv.reader(f))

with open(new_file, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    new_headers = reader.fieldnames
    rows = list(reader)

print(f"Header match exactly: {ref_headers == new_headers}")
print(f"Total columns: {len(new_headers)}")
print(f"Total rows: {len(rows)}")

products = {}
for r in rows:
    h = r["Handle"]
    products.setdefault(h, []).append(r)

print(f"Unique products: {len(products)}")

for idx, (h, p_rows) in enumerate(products.items(), start=1):
    first = p_rows[0]
    author_field = first["Author Info (product.metafields.custom.author_info)"]
    rich_desc = first["Rich Description (product.metafields.custom.rich_description)"]
    orig_price = first["Original Price 10 Percent (product.metafields.custom.original_price_10_percent)"]
    img_urls = [r["Image Src"] for r in p_rows if r["Image Src"]]
    
    print(f"[{idx:02d}] Handle: {h}")
    print(f"     Title: {first['Title']}")
    print(f"     SEO Title ({len(first['SEO Title'])} chars): {first['SEO Title']}")
    print(f"     SEO Desc ({len(first['SEO Description'])} chars): {first['SEO Description']}")
    print(f"     Vendor: {first['Vendor']} | Type: {first['Type']} | Tags: {first['Tags']}")
    print(f"     Author Metafield: {author_field}")
    print(f"     Rich Desc Metafield: {rich_desc}")
    print(f"     Variants count: {len(p_rows)} | First Price: {first['Variant Price']} | Last Price: {p_rows[-1]['Variant Price']}")
    print(f"     Images attached: {len(img_urls)} | First image: {img_urls[0][:65]}...")
    orig_price_obj = json.loads(orig_price)
    print(f"     Original Price Metafield variants: {len(orig_price_obj)}")
    print()
