#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script sinh file CSV sản phẩm gương (Mirrors) chuẩn Shopify để import.
- 9 sản phẩm: 6 mẫu Rustic (Mẫu 1 - 6) + 3 mẫu Organic (Mẫu 1 - 3).
- Mỗi sản phẩm có đúng 14 biến thể kích thước (Size) lấy từ bảng giá Google Sheet.
- Hình ảnh lấy từ file kết quả mapping CDN Shopify (uploaded_images_mapping.json).
- Tuân thủ 100% bộ quy chuẩn dữ liệu Leader yêu cầu và tiêu chuẩn On-page SEO của Wrydeco.
- Đúng chuẩn 68 cột theo file mẫu của store.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MAPPING_JSON_PATH = BASE_DIR / "todo" / "scripts" / "uploaded_images_mapping.json"
OUTPUT_CSV_PATH = BASE_DIR / "todo" / "SEO" / "final" / "new-mirrors-product-listing.csv"

# 14 kích thước và giá bán (giá chưa giảm) lấy từ Tab BẢNG GIÁ GƯƠNG (Google Sheet)
PRICING_TABLE = [
    {"size": "16'' x 12''", "label": "", "price_organic": "315.00", "price_rustic": "473.00"},
    {"size": "20'' x 16''", "label": "", "price_organic": "354.00", "price_rustic": "531.00"},
    {"size": "28'' x 16''", "label": "", "price_organic": "393.00", "price_rustic": "590.00"},
    {"size": "28'' x 20''", "label": "Best small option", "price_organic": "462.00", "price_rustic": "693.00"},
    {"size": "25'' x 25''", "label": "Square mirror", "price_organic": "462.00", "price_rustic": "693.00"},
    {"size": "32\" × 24\"", "label": "", "price_organic": "511.00", "price_rustic": "766.00"},
    {"size": "36\" × 24\"", "label": "", "price_organic": "526.00", "price_rustic": "789.00"},
    {"size": "38\" × 26\"", "label": "", "price_organic": "549.00", "price_rustic": "823.00"},
    {"size": "40\" × 28\"", "label": "", "price_organic": "602.00", "price_rustic": "903.00"},
    {"size": "55\" × 22\"", "label": "Popular choice", "price_organic": "658.00", "price_rustic": "987.00"},
    {"size": "55\" × 30\"", "label": "", "price_organic": "705.00", "price_rustic": "1058.00"},
    {"size": "65\" × 24\"", "label": "", "price_organic": "772.00", "price_rustic": "1158.00"},
    {"size": "71'' x 24''", "label": "Full length option", "price_organic": "858.00", "price_rustic": "1287.00"},
    {"size": "79'' x 32''", "label": "", "price_organic": "1022.00", "price_rustic": "1533.00"},
]

# Định nghĩa 9 sản phẩm gương
PRODUCTS_DEFINITIONS = [
    # --- 6 MẪU RUSTIC ---
    {
        "collection_key": "Rustic",
        "model_key": "MẪU 1",
        "title": "Rustic Handcrafted Solid Wood Wall Mirror 1",
        "handle": "rustic-handcrafted-solid-wood-wall-mirror-1",
        "sku_prefix": "WRY-MR-RST-01",
        "differentiator": "natural timber frame with raw handcrafted wood grain character",
        "seo_product_title": "Rustic Handcrafted Solid Wood Wall Mirror with Natural Timber Grain",
    },
    {
        "collection_key": "Rustic",
        "model_key": "MẪU 2",
        "title": "Rustic Farmhouse Solid Wood Wall Mirror 2",
        "handle": "rustic-farmhouse-solid-wood-wall-mirror-2",
        "sku_prefix": "WRY-MR-RST-02",
        "differentiator": "deep-set weathered wooden frame with authentic artisan finish",
        "seo_product_title": "Rustic Farmhouse Solid Wood Wall Accent Mirror for Living Room",
    },
    {
        "collection_key": "Rustic",
        "model_key": "MẪU 3",
        "title": "Rustic Reclaimed Solid Wood Wall Mirror 3",
        "handle": "rustic-reclaimed-solid-wood-wall-mirror-3",
        "sku_prefix": "WRY-MR-RST-03",
        "differentiator": "chunky solid wood border highlighting earthy knots and organic texture",
        "seo_product_title": "Rustic Reclaimed Solid Wood Framed Wall Mirror Decor",
    },
    {
        "collection_key": "Rustic",
        "model_key": "MẪU 4",
        "title": "Rustic Cottage Carved Wood Wall Mirror 4",
        "handle": "rustic-cottage-carved-wood-wall-mirror-4",
        "sku_prefix": "WRY-MR-RST-04",
        "differentiator": "artisan hand-shaped timber profile with rustic architectural presence",
        "seo_product_title": "Rustic Cottage Hand-Shaped Solid Wood Vanity Wall Mirror",
    },
    {
        "collection_key": "Rustic",
        "model_key": "MẪU 5",
        "title": "Rustic Vintage Plank Solid Wood Wall Mirror 5",
        "handle": "rustic-vintage-plank-solid-wood-wall-mirror-5",
        "sku_prefix": "WRY-MR-RST-05",
        "differentiator": "distressed natural wood perimeter inspired by traditional craftsmanship",
        "seo_product_title": "Rustic Vintage Distressed Solid Wood Wall Decor Mirror",
    },
    {
        "collection_key": "Rustic",
        "model_key": "MẪU 6",
        "title": "Rustic Minimalist Thick Timber Wall Mirror 6",
        "handle": "rustic-minimalist-thick-timber-wall-mirror-6",
        "sku_prefix": "WRY-MR-RST-06",
        "differentiator": "substantial solid timber silhouette designed as a statement focal point",
        "seo_product_title": "Substantial Rustic Solid Wood Wall Mirror Statement Decor",
    },
    # --- 3 MẪU ORGANIC ---
    {
        "collection_key": "Organic",
        "model_key": "MẪU 1",
        "title": "Organic Irregular Curved Solid Wood Wall Mirror 1",
        "handle": "organic-irregular-curved-solid-wood-wall-mirror-1",
        "sku_prefix": "WRY-MR-ORG-01",
        "differentiator": "fluid pebble-inspired asymmetrical silhouette with smooth wood contours",
        "seo_product_title": "Organic Irregular Asymmetrical Pebble Shaped Wood Wall Mirror",
    },
    {
        "collection_key": "Organic",
        "model_key": "MẪU 2",
        "title": "Organic Asymmetrical Shaped Wood Wall Mirror 2",
        "handle": "organic-asymmetrical-shaped-wood-wall-mirror-2",
        "sku_prefix": "WRY-MR-ORG-02",
        "differentiator": "sculptural wavy wood contour creating soft organic focal lines",
        "seo_product_title": "Organic Asymmetrical Wavy Solid Wood Framed Wall Accent Mirror",
    },
    {
        "collection_key": "Organic",
        "model_key": "MẪU 3",
        "title": "Organic Fluid Contour Solid Wood Wall Mirror 3",
        "handle": "organic-fluid-contour-solid-wood-wall-mirror-3",
        "sku_prefix": "WRY-MR-ORG-03",
        "differentiator": "biophilic cloud-like curved frame celebrating natural flowing lines",
        "seo_product_title": "Biophilic Organic Fluid Curved Solid Wood Vanity Wall Mirror",
    },
]

CSV_HEADERS = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Product Category",
    "Type",
    "Tags",
    "Published",
    "Option1 Name",
    "Option1 Value",
    "Option1 Linked To",
    "Option2 Name",
    "Option2 Value",
    "Option2 Linked To",
    "Option3 Name",
    "Option3 Value",
    "Option3 Linked To",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Tracker",
    "Variant Inventory Qty",
    "Variant Inventory Policy",
    "Variant Fulfillment Service",
    "Variant Price",
    "Variant Compare At Price",
    "Variant Requires Shipping",
    "Variant Taxable",
    "Unit Price Total Measure",
    "Unit Price Total Measure Unit",
    "Unit Price Base Measure",
    "Unit Price Base Measure Unit",
    "Variant Barcode",
    "Image Src",
    "Image Position",
    "Image Alt Text",
    "Gift Card",
    "SEO Title",
    "SEO Description",
    "Google Shopping / Google Product Category",
    "Google Shopping / Gender",
    "Google Shopping / Age Group",
    "Google Shopping / MPN",
    "Google Shopping / Condition",
    "Google Shopping / Custom Product",
    "Google Shopping / Custom Label 0",
    "Google Shopping / Custom Label 1",
    "Google Shopping / Custom Label 2",
    "Google Shopping / Custom Label 3",
    "Google Shopping / Custom Label 4",
    "Amazon Link (product.metafields.custom.amazon_link)",
    "Author Info (product.metafields.custom.author_info)",
    "Bought Amount (product.metafields.custom.bought_amount)",
    "product_video_media (product.metafields.custom.product_video_media)",
    "Rich Description (product.metafields.custom.rich_description)",
    "SEO product title (product.metafields.custom.seo_product_title)",
    "Size Guide (product.metafields.custom.size_guide)",
    "Google: Custom Product (product.metafields.mm-google-shopping.custom_product)",
    "Product rating count (product.metafields.reviews.rating_count)",
    "Complementary products (product.metafields.shopify--discovery--product_recommendation.complementary_products)",
    "Related products (product.metafields.shopify--discovery--product_recommendation.related_products)",
    "Related products settings (product.metafields.shopify--discovery--product_recommendation.related_products_display)",
    "Search product boosts (product.metafields.shopify--discovery--product_search_boost.queries)",
    "Variant Image",
    "Variant Weight Unit",
    "Variant Tax Code",
    "Cost per item",
    "Status",
    "Original Price 10 Percent (product.metafields.custom.original_price_10_percent)",
]


def build_product_description(title: str, differentiator: str) -> str:
    """Tạo mô tả sản phẩm Body (HTML) tuân thủ 100% cấu trúc 3 thẻ <h2> của Wrydeco."""
    all_sizes_str = "; ".join([p["size"] for p in PRICING_TABLE])
    
    return (
        f'<div class="wrydeco-product-description"> '
        f'<p>The {title} is a natural wood wall mirror defined by its {differentiator}. '
        f'It is intended as an interior accent where wall space, hanging height, and room lighting reflections '
        f'should be reviewed before ordering. Use the dimensions, finish options, and gallery to compare fit before selecting a configuration.</p> '
        f'<h2>Product Details</h2> '
        f'<ul> '
        f'<li><strong>Design focus:</strong> {differentiator}</li> '
        f'<li><strong>Material and finish:</strong> The design is presented with natural wood character; review the gallery and finish options for variation in grain and tone.</li> '
        f'<li><strong>Available sizes:</strong> {all_sizes_str}</li> '
        f'<li><strong>Product category:</strong> mirror</li> '
        f'<li><strong>Available configurations:</strong> 14 selectable size configurations are listed for this product. Confirm the final option combination before ordering.</li> '
        f'</ul> '
        f'<h2>Planning Your Space</h2> '
        f'<p>Review the listed dimensions, wall span, mounting position, and room lighting reflections before choosing a display location.</p> '
        f'<h2>Before You Order</h2>'
        f'<p>For final purchase decisions, confirm product-specific details such as wood species, mounting hardware, mirror weight, '
        f'production and delivery lead time, care instructions through the latest Wrydeco product information or customer support. '
        f'These details should not be assumed from imagery alone.</p> '
        f'</div>'
    )


def build_original_price_metafield(is_rustic: bool) -> str:
    """Tạo cấu trúc JSON lưu bảng giá gốc cho metafield original_price_10_percent."""
    var_dict = {}
    for idx, item in enumerate(PRICING_TABLE, start=1):
        key = f"variant_{idx:03d}"
        price = item["price_rustic"] if is_rustic else item["price_organic"]
        var_dict[key] = {
            "option1_name": "Size",
            "option1_value": item["size"],
            "option2_name": "",
            "option2_value": "",
            "option3_name": "",
            "option3_value": "",
            "original_price": price,
        }
    return json.dumps(var_dict, ensure_ascii=False)


def generate_csv():
    print("Đang đọc mapping hình ảnh từ:", MAPPING_JSON_PATH)
    if not MAPPING_JSON_PATH.is_file():
        raise FileNotFoundError(f"Chưa có file mapping: {MAPPING_JSON_PATH}. Vui lòng chờ upload xong!")

    mapping_data: List[Dict[str, Any]] = json.loads(MAPPING_JSON_PATH.read_text(encoding="utf-8"))

    # Gom nhóm ảnh theo (Collection, Model)
    images_by_product: Dict[str, List[Dict[str, Any]]] = {}
    for img in mapping_data:
        col = "Rustic" if "rustic" in img.get("collection", "").lower() else "Organic"
        model_num_match = re.search(r"\d+", img.get("model", ""))
        model_num = model_num_match.group(0) if model_num_match else "1"
        key = f"{col}_{model_num}"
        images_by_product.setdefault(key, []).append(img)

    for k in images_by_product:
        images_by_product[k].sort(key=lambda x: x.get("index", 1))

    all_rows = []

    for prod_def in PRODUCTS_DEFINITIONS:
        col_key = prod_def["collection_key"]
        is_rustic = (col_key == "Rustic")
        model_match = re.search(r"\d+", prod_def["model_key"])
        model_num = model_match.group(0) if model_match else "1"
        group_key = f"{col_key}_{model_num}"

        prod_images = images_by_product.get(group_key, [])
        title = prod_def["title"]
        handle = prod_def["handle"]
        differentiator = prod_def["differentiator"]
        seo_prod_title = prod_def["seo_product_title"]

        # Chuẩn SEO
        seo_title = f"{title} | Wrydeco"
        seo_desc = (
            f"Explore the {title} by Wrydeco. "
            f"Compare available sizes, wood finishes, and product imagery."
        )
        body_html = build_product_description(title, differentiator)
        orig_price_json = build_original_price_metafield(is_rustic)

        # Số dòng của sản phẩm = max(14 biến thể, số ảnh)
        total_rows = max(len(PRICING_TABLE), len(prod_images))

        for row_idx in range(total_rows):
            row = {h: "" for h in CSV_HEADERS}
            row["Handle"] = handle

            # --- DÒNG ĐẦU TIÊN (PARENT ROW): ĐIỀN THÔNG TIN CHUNG SẢN PHẨM ---
            if row_idx == 0:
                row["Title"] = title
                row["Body (HTML)"] = body_html
                row["Vendor"] = "Wrydeco"
                row["Product Category"] = "Home & Garden > Decor > Mirrors"
                row["Type"] = "mirror"
                tag_style = "rustic" if is_rustic else "organic"
                row["Tags"] = f"source_amazon, {tag_style}"
                row["Published"] = "true"
                row["Status"] = "active"
                row["Option1 Name"] = "Size"
                row["Gift Card"] = "false"
                row["SEO Title"] = seo_title
                row["SEO Description"] = seo_desc
                row["Google Shopping / Google Product Category"] = "Home & Garden > Decor > Mirrors"
                row["Google Shopping / Condition"] = "new"
                row["Google Shopping / Custom Product"] = "false"
                row["Author Info (product.metafields.custom.author_info)"] = "gid://shopify/Metaobject/194643198009"
                row["Rich Description (product.metafields.custom.rich_description)"] = '<div class="description-root"></div>'
                row["SEO product title (product.metafields.custom.seo_product_title)"] = seo_prod_title
                row["Original Price 10 Percent (product.metafields.custom.original_price_10_percent)"] = orig_price_json

            # --- DỮ LIỆU BIẾN THỂ (VARIANT) ---
            if row_idx < len(PRICING_TABLE):
                var_item = PRICING_TABLE[row_idx]
                price = var_item["price_rustic"] if is_rustic else var_item["price_organic"]
                sku = f"{prod_def['sku_prefix']}-{row_idx + 1:02d}"

                row["Option1 Value"] = var_item["size"]
                row["Variant SKU"] = sku
                row["Variant Grams"] = "0.0"
                row["Variant Inventory Tracker"] = "shopify"
                row["Variant Inventory Qty"] = "10"
                row["Variant Inventory Policy"] = "deny"
                row["Variant Fulfillment Service"] = "manual"
                row["Variant Price"] = price
                row["Variant Requires Shipping"] = "true"
                row["Variant Taxable"] = "true"
                row["Variant Weight Unit"] = "kg"

            # --- DỮ LIỆU HÌNH ẢNH (IMAGE) ---
            if row_idx < len(prod_images):
                img_item = prod_images[row_idx]
                row["Image Src"] = img_item.get("cdn_url", "")
                row["Image Position"] = str(row_idx + 1)
                row["Image Alt Text"] = img_item.get("alt_text", "")

            all_rows.append(row)

    OUTPUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Đã tạo thành công file CSV: {OUTPUT_CSV_PATH}")
    print(f"Tổng số dòng: {len(all_rows)} dòng (tương ứng 9 sản phẩm, mỗi sản phẩm 14 dòng biến thể).")


if __name__ == "__main__":
    generate_csv()
