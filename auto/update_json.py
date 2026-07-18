import json
import os

with open('crawl/B0H6FHL19T/B0H6FHL19T.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Ensure keys are in right order or at least top level
new_data = {}
new_data['product_type'] = "Headboard"
new_data['product_category'] = "Furniture"
new_data['schema_version'] = data.get('schema_version', '1.2.0')
new_data['asin'] = data['asin']
new_data['source_url'] = data['source_url']
new_data['crawl_metadata'] = data['crawl_metadata']

# Title must be 50 to 70 chars
new_data['product'] = data['product']
new_data['product']['title'] = "PREAUREUM Rustic Solid Wood Live Edge Headboard Panel"

new_data['assets'] = data['assets']
new_data['color_swatches'] = data['color_swatches']

# extra_fields MUST be the last key
new_data['extra_fields'] = {
    "seo_product_title": "PREAUREUM Rustic Solid Wood Live Edge Headboard Panel",
    "page_title": "PREAUREUM Rustic Solid Wood Live Edge Headboard Panel ", # 54 chars
    "meta_description": "Upgrade your bedroom with the PREAUREUM Rustic Solid Wood Live Edge Headboard. This natural wood panel brings warmth and cozy cabin style to your sleep space.", # 158 chars
    "url_slug": "preaureum-rustic-solid-wood-live-edge-headboard-wood" # 52 chars
}

with open('crawl/B0H6FHL19T/B0H6FHL19T.json', 'w', encoding='utf-8') as f:
    json.dump(new_data, f, indent=2, ensure_ascii=False)
