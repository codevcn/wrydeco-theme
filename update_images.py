import json

index_path = r"d:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-theme\templates\index.json"
with open(index_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for block_id, block in data.get('sections', {}).get('customer_reviews', {}).get('blocks', {}).items():
    if 'fallback_image' in block.get('settings', {}):
        old_val = block['settings']['fallback_image']
        if old_val.startswith('sli-'):
            new_val = old_val.replace('sli-', 'eff-').replace('.webp', '.jpg')
            block['settings']['fallback_image'] = new_val

with open(index_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("Updated index.json")

# Now update customer-reviews.liquid
liquid_path = r"d:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-theme\sections\customer-reviews.liquid"
with open(liquid_path, 'r', encoding='utf-8') as f:
    content = f.read()

for i in range(1, 13):
    content = content.replace(f"sli-{i}.webp", f"eff-{i}.jpg")

with open(liquid_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated customer-reviews.liquid")
