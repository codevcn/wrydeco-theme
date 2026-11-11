"""
product_create_service.py
Service subsystem phụ trách tạo sản phẩm mới cho WRYDECO Store thông qua Shopify GraphQL Admin API.
Kiến trúc cốt lõi:
- Đảm bảo Proxy Safety Gate tuyệt đối (bắt buộc qua proxy cho Custom Store WRYDECO).
- Sử dụng mutation nguyên tử productSet(synchronous: true, input: $input) để tạo đồng thời:
  title, description, productType, category, status, vendor, tags, seo, productOptions,
  variants (kèm price, compareAtPrice, sku, barcode riêng từng biến thể), metafields, files.
- Kiểm tra toàn vẹn server-side (Cartesian reconstruction, uniqueness check, whitelist validation).
- Xử lý upload media đa nguồn (local device qua stagedUploadsCreate + external image URLs).
"""

import os
import sys
import json
import uuid
import mimetypes
import itertools
from typing import Dict, Any, List, Tuple, Optional

import requests
from proxy_manager import (
    get_shopify_client, 
    execute_shopify_graphql, 
    ProxySafetyException,
    get_shopify_request_proxies
)

# Danh sách phong cách nội thất chuẩn của WRYDECO
WHITELIST_INTERIOR_STYLES = [
    "Rustic",
    "Japandi",
    "Mid-Century",
    "Organic Modern"
]

# Danh sách không gian phòng chuẩn của WRYDECO
WHITELIST_ROOM_TYPES = [
    "Living Room",
    "Bedroom",
    "Kitchen & Dining",
    "Home Office & Library",
    "Nursery & Kids' Room",
    "Entryway & Hallway",
    "Bathroom"
]

# Whitelist Vendor
WHITELIST_VENDORS = ["Wrydeco"]

# GraphQL Mutation chuẩn cho ProductSet
PRODUCT_SET_MUTATION = """
mutation CreateProductWithProductSet($synchronous: Boolean!, $identifier: ProductSetIdentifiers, $input: ProductSetInput!) {
  productSet(synchronous: $synchronous, identifier: $identifier, input: $input) {
    product {
      id
      handle
      title
      status
      productType
      vendor
      tags
      category {
        id
        name
      }
      options {
        id
        name
        values
      }
      variants(first: 100) {
        edges {
          node {
            id
            title
            price
            compareAtPrice
            sku
            barcode
            selectedOptions {
              name
              value
            }
          }
        }
      }
      metafields(first: 30) {
        edges {
          node {
            namespace
            key
            value
            type
          }
        }
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

# Query tra cứu sản phẩm bằng Unique Metafield Value (Strong Idempotency)
PRODUCT_BY_CUSTOM_ID_QUERY = """
query LookupProductByCustomId($namespace: String!, $key: String!, $value: String!) {
  productByIdentifier(identifier: { customId: { namespace: $namespace, key: $key, value: $value } }) {
    id
    handle
    title
    status
    productType
    vendor
  }
}
"""


def check_shopify_product_exists_by_custom_id(
    custom_id: str, 
    store_type: str = "default",
    namespace: str = "custom",
    key: str = "bulk_import_id"
) -> Optional[Dict[str, Any]]:
    """
    Tra cứu sản phẩm trên Shopify bằng Strong Custom Identifier (productByIdentifier).
    Đảm bảo 100% Strong Idempotency: Chỉ reconcile khi sản phẩm thuộc chính job item này.
    """
    if not custom_id or not str(custom_id).strip():
        return None
    try:
        client_info = get_shopify_client(store_type=store_type, force_proxy_for_custom=True)
        res = execute_shopify_graphql(client_info, PRODUCT_BY_CUSTOM_ID_QUERY, {
            "namespace": namespace,
            "key": key,
            "value": str(custom_id).strip()
        })
        data = res.get("data") or {}
        return data.get("productByIdentifier")
    except Exception as e:
        logger.warning(f"Lỗi khi tra cứu customId '{custom_id}' trên Shopify ({store_type}): {str(e)}")
        return None

# Query kiểm tra sản phẩm theo Handle phục vụ Preflight và Idempotency Reconciliation
PRODUCT_BY_HANDLE_QUERY = """
query CheckProductByHandle($handle: String!) {
  productByHandle(handle: $handle) {
    id
    handle
    title
    status
  }
}
"""


def check_shopify_product_exists_by_handle(handle: str, store_type: str = "default") -> Optional[Dict[str, Any]]:
    """
    Kiểm tra xem sản phẩm có URL Handle đã tồn tại trên Shopify Store hay chưa.
    Trả về dict {'id': ..., 'handle': ..., 'title': ..., 'status': ...} nếu tồn tại, ngược lại trả về None.
    Dùng cho:
    1. Preflight kiểm tra chống ghi đè sản phẩm cũ của merchant (HANDLE_EXISTS).
    2. Idempotency Reconciliation khi gặp sự cố mạng (Ambiguous commit recovery).
    """
    if not handle or not str(handle).strip():
        return None
    try:
        client_info = get_shopify_client(store_type=store_type, force_proxy_for_custom=True)
        res = execute_shopify_graphql(client_info, PRODUCT_BY_HANDLE_QUERY, {"handle": str(handle).strip()})
        data = res.get("data") or {}
        return data.get("productByHandle")
    except Exception as e:
        logger.warning(f"Lỗi khi tra cứu handle '{handle}' trên Shopify ({store_type}): {str(e)}")
        return None

# Staged upload mutation cho local files
STAGED_UPLOADS_CREATE_MUTATION = """
mutation StagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets {
      url
      resourceUrl
      parameters {
        name
        value
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""


def validate_create_payload(payload: Dict[str, Any]) -> Tuple[bool, List[Dict[str, str]]]:
    """
    Xác thực toàn diện các trường bắt buộc của payload tạo sản phẩm ở Server-Side.
    Trả về (is_valid, errors_list).
    """
    errors: List[Dict[str, str]] = []

    def add_err(field: str, msg: str, code: str = "REQUIRED_FIELD"):
        errors.append({"field": field, "message": msg, "code": code})

    # 1. Media
    media = payload.get("media") or []
    if not isinstance(media, list) or len(media) == 0:
        add_err("media", "Sản phẩm bắt buộc phải có ít nhất 1 hình ảnh hoặc video media.")

    # 2. Title
    title = (payload.get("title") or "").strip()
    if not title:
        add_err("title", "Tên sản phẩm (Title) là bắt buộc.")

    # 3. Description
    desc = (payload.get("descriptionHtml") or payload.get("description") or "").strip()
    if not desc:
        add_err("description", "Mô tả sản phẩm (Description) là bắt buộc.")

    # 4. Product Type
    product_type = (payload.get("productType") or "").strip()
    if not product_type:
        add_err("productType", "Loại sản phẩm (Product Type) là bắt buộc.")

    # 5. Category (Taxonomy Category GID)
    category = (payload.get("categoryId") or payload.get("category") or "").strip()
    if not category:
        add_err("category", "Danh mục sản phẩm (Category) là bắt buộc.")
    elif not category.startswith("gid://shopify/TaxonomyCategory/"):
        add_err("category", "Định dạng Category ID không hợp lệ, phải bắt đầu bằng gid://shopify/TaxonomyCategory/.")

    # 6. Status
    status = (payload.get("status") or "").strip().upper()
    if status not in ["DRAFT", "ACTIVE"]:
        add_err("status", "Trạng thái (Status) phải là 'DRAFT' hoặc 'ACTIVE'.")

    # 7. Tags
    tags = payload.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not isinstance(tags, list) or len(tags) == 0:
        add_err("tags", "Bắt buộc phải có ít nhất 1 thẻ (Tag) cho sản phẩm.")

    # 8. Vendor
    vendor = (payload.get("vendor") or "").strip()
    if not vendor:
        add_err("vendor", "Nhà cung cấp (Vendor) là bắt buộc.")
    elif vendor not in WHITELIST_VENDORS:
        add_err("vendor", f"Nhà cung cấp (Vendor) chỉ được phép là: {', '.join(WHITELIST_VENDORS)}.")

    # 9. SEO Title
    seo = payload.get("seo") or {}
    seo_title = (seo.get("title") or "").strip()
    if not seo_title:
        add_err("seoTitle", "SEO Title là bắt buộc để đảm bảo tối ưu hóa tìm kiếm.")

    # 10. SEO Description
    seo_desc = (seo.get("description") or "").strip()
    if not seo_desc:
        add_err("seoDescription", "SEO Description là bắt buộc để hiển thị snippet trên công cụ tìm kiếm.")

    # 11. Author (Metaobject reference)
    author_id = (payload.get("authorId") or "").strip()
    if not author_id:
        add_err("author", "Tác giả sản phẩm (Author) là bắt buộc.")
    elif not author_id.startswith("gid://shopify/Metaobject/"):
        add_err("author", "ID Tác giả không hợp lệ, phải là Metaobject GID (gid://shopify/Metaobject/...).")

    # 12. Rich Description (custom.rich_description)
    rich_desc = (payload.get("richDescription") or "").strip()
    if not rich_desc:
        add_err("richDescription", "Mô tả mở rộng (Rich Description) là trường bắt buộc cho store Wrydeco.")

    # 13. AEO (custom.aeo_html)
    aeo_html = (payload.get("aeoHtml") or "").strip()
    if not aeo_html:
        add_err("aeoHtml", "Nội dung Answer Engine Optimization (AEO) là bắt buộc.")

    # 14. Interior Style (custom.interior_style: list)
    interior_styles = payload.get("interiorStyle") or []
    if not isinstance(interior_styles, list) or len(interior_styles) == 0:
        add_err("interiorStyle", "Bắt buộc phải chọn ít nhất 1 phong cách nội thất (Interior Style).")
    else:
        invalid_styles = [s for s in interior_styles if s not in WHITELIST_INTERIOR_STYLES]
        if invalid_styles:
            add_err("interiorStyle", f"Phong cách nội thất không hợp lệ: {', '.join(invalid_styles)}. Danh sách cho phép: {', '.join(WHITELIST_INTERIOR_STYLES)}.")

    # 15. Room Type (custom.room_type: list)
    room_types = payload.get("roomType") or []
    if not isinstance(room_types, list) or len(room_types) == 0:
        add_err("roomType", "Bắt buộc phải chọn ít nhất 1 không gian phòng (Room Type).")
    else:
        invalid_rooms = [r for r in room_types if r not in WHITELIST_ROOM_TYPES]
        if invalid_rooms:
            add_err("roomType", f"Không gian phòng không hợp lệ: {', '.join(invalid_rooms)}. Danh sách cho phép: {', '.join(WHITELIST_ROOM_TYPES)}.")

    # 16. Variation (Options & Variants)
    options = payload.get("options") or []
    variants = payload.get("variants") or []
    var_ok, var_errors = validate_variation_structure(options, variants)
    if not var_ok:
        errors.extend(var_errors)

    return (len(errors) == 0, errors)


def validate_variation_structure(options: List[Dict[str, Any]], variants: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, str]]]:
    """
    Xác thực cấu trúc Variation:
    - 1 <= len(options) <= 3
    - Tên options không trùng lặp, không rỗng
    - Các giá trị trong mỗi option không rỗng, không trùng lặp
    - Tái tạo ma trận Descartes (Cartesian product) và kiểm tra tính toàn vẹn 100%
    - Tổng số biến thể <= 2048
    - Mỗi biến thể bắt buộc có: Price (>= 0), Compare-at price (> 0), SKU (không trùng), Barcode (không trùng)
    """
    errors: List[Dict[str, str]] = []

    def add_err(field: str, msg: str, code: str = "VARIATION_ERROR"):
        errors.append({"field": field, "message": msg, "code": code})

    if not isinstance(options, list) or len(options) == 0:
        add_err("options", "Sản phẩm bắt buộc phải có ít nhất 1 nhóm tùy chọn (Option).")
        return (False, errors)

    if len(options) > 3:
        add_err("options", "Shopify chỉ hỗ trợ tối đa 3 tùy chọn (Options) cho mỗi sản phẩm.")
        return (False, errors)

    seen_opt_names = set()
    cleaned_options = []

    for opt_idx, opt in enumerate(options):
        opt_name = (opt.get("name") or "").strip()
        if not opt_name:
            add_err(f"options[{opt_idx}].name", f"Tên tùy chọn thứ {opt_idx + 1} không được để trống.")
            continue

        if opt_name.lower() in seen_opt_names:
            add_err(f"options[{opt_idx}].name", f"Tên tùy chọn '{opt_name}' bị trùng lặp.")
        seen_opt_names.add(opt_name.lower())

        raw_values = opt.get("values") or []
        cleaned_values = []
        seen_val_labels = set()

        for val_idx, val in enumerate(raw_values):
            label = ""
            if isinstance(val, dict):
                label = (val.get("label") or val.get("name") or "").strip()
            elif isinstance(val, str):
                label = val.strip()

            if not label:
                add_err(f"options[{opt_idx}].values[{val_idx}]", f"Giá trị tùy chọn trong '{opt_name}' không được để trống.")
                continue

            if label.lower() in seen_val_labels:
                add_err(f"options[{opt_idx}].values[{val_idx}]", f"Giá trị '{label}' trong tùy chọn '{opt_name}' bị trùng lặp.")
            seen_val_labels.add(label.lower())
            cleaned_values.append(label)

        if len(cleaned_values) == 0:
            add_err(f"options[{opt_idx}].values", f"Tùy chọn '{opt_name}' phải có ít nhất 1 giá trị.")

        cleaned_options.append({"name": opt_name, "values": cleaned_values})

    if len(errors) > 0:
        return (False, errors)

    # Tính tích Descartes lý thuyết (Expected Cartesian combinations)
    option_value_lists = [opt["values"] for opt in cleaned_options]
    expected_combinations = list(itertools.product(*option_value_lists))
    expected_count = len(expected_combinations)

    if expected_count > 2048:
        add_err("variants", f"Tổng số lượng biến thể ({expected_count}) vượt quá giới hạn tối đa của Shopify (2048 biến thể).")
        return (False, errors)

    if not isinstance(variants, list) or len(variants) == 0:
        add_err("variants", "Danh sách biến thể không được rỗng.")
        return (False, errors)

    if len(variants) != expected_count:
        add_err("variants", f"Số lượng biến thể được gửi ({len(variants)}) không khớp với ma trận kết hợp thực tế ({expected_count}).")

    # Bản đồ kiểm tra tính duy nhất của SKU và Barcode
    seen_skus = set()
    seen_barcodes = set()
    matched_combinations = set()

    for v_idx, v in enumerate(variants):
        row_label = f"Biến thể #{v_idx + 1}"
        
        # 1. Trích xuất option values của row
        opt_values_input = v.get("optionValues") or []
        comb_tuple = None

        if isinstance(opt_values_input, list):
            # Format: [{"optionName": "...", "name": "..."}]
            name_map = {}
            for item in opt_values_input:
                if isinstance(item, dict):
                    name_map[item.get("optionName", "").strip().lower()] = item.get("name", "").strip()
            
            # Xếp theo thứ tự options
            tuple_vals = []
            for opt in cleaned_options:
                tuple_vals.append(name_map.get(opt["name"].lower(), ""))
            comb_tuple = tuple(tuple_vals)

        elif isinstance(opt_values_input, dict):
            tuple_vals = [opt_values_input.get(opt["name"], "") for opt in cleaned_options]
            comb_tuple = tuple(tuple_vals)

        if comb_tuple:
            if comb_tuple not in expected_combinations:
                add_err(f"variants[{v_idx}]", f"{row_label}: Tổ hợp biến thể {' / '.join(comb_tuple)} không hợp lệ (không tồn tại trong ma trận tùy chọn).")
            if comb_tuple in matched_combinations:
                add_err(f"variants[{v_idx}]", f"{row_label}: Tổ hợp biến thể {' / '.join(comb_tuple)} bị khai báo lặp lại.")
            matched_combinations.add(comb_tuple)

        # 2. Price ($) - Bắt buộc
        raw_price = str(v.get("price") or "").strip()
        price_val = None
        if not raw_price:
            add_err(f"variants[{v_idx}].price", f"{row_label}: Giá bán (Price) là bắt buộc.")
        else:
            try:
                price_val = float(raw_price)
                if price_val < 0:
                    add_err(f"variants[{v_idx}].price", f"{row_label}: Giá bán (Price) không được là số âm.")
            except ValueError:
                add_err(f"variants[{v_idx}].price", f"{row_label}: Giá bán '{raw_price}' không hợp lệ.")

        # 3. Compare-at price ($) - Bắt buộc và phải lớn hơn Price
        raw_compare = str(v.get("compareAtPrice") or "").strip()
        if not raw_compare:
            add_err(f"variants[{v_idx}].compareAtPrice", f"{row_label}: Giá so sánh (Compare-at price) là bắt buộc.")
        else:
            try:
                compare_val = float(raw_compare)
                if compare_val <= 0:
                    add_err(f"variants[{v_idx}].compareAtPrice", f"{row_label}: Giá so sánh phải lớn hơn 0.")
                elif price_val is not None and compare_val <= price_val:
                    add_err(f"variants[{v_idx}].compareAtPrice", f"{row_label}: Giá so sánh (${compare_val:.2f}) bắt buộc phải lớn hơn Giá bán (${price_val:.2f}).")
            except ValueError:
                add_err(f"variants[{v_idx}].compareAtPrice", f"{row_label}: Giá so sánh '{raw_compare}' không hợp lệ.")

        # 4. SKU - Bắt buộc & Duy nhất
        sku = str(v.get("sku") or "").strip()
        if not sku:
            add_err(f"variants[{v_idx}].sku", f"{row_label}: Mã SKU là bắt buộc.")
        else:
            sku_lower = sku.lower()
            if sku_lower in seen_skus:
                add_err(f"variants[{v_idx}].sku", f"{row_label}: Mã SKU '{sku}' bị trùng lặp với biến thể khác.")
            seen_skus.add(sku_lower)

        # 5. Barcode - Bắt buộc & Duy nhất
        barcode = str(v.get("barcode") or "").strip()
        if not barcode:
            add_err(f"variants[{v_idx}].barcode", f"{row_label}: Mã Barcode là bắt buộc.")
        else:
            barcode_lower = barcode.lower()
            if barcode_lower in seen_barcodes:
                add_err(f"variants[{v_idx}].barcode", f"{row_label}: Mã Barcode '{barcode}' bị trùng lặp với biến thể khác.")
            seen_barcodes.add(barcode_lower)

    # Kiểm tra xem có tổ hợp nào bị bỏ sót không
    for expected_comb in expected_combinations:
        if expected_comb not in matched_combinations:
            add_err("variants", f"Thiếu biến thể cho tổ hợp: {' / '.join(expected_comb)}.")

    return (len(errors) == 0, errors)


def stage_and_upload_local_file(client_info: Dict[str, Any], filename: str, content_bytes: bytes, mime_type: str) -> str:
    """
    Tải file nhị phân từ máy người dùng lên Shopify Staged Storage (Google Cloud Storage):
    1. Gọi mutation stagedUploadsCreate.
    2. Gửi multipart POST chứa parameters + content_bytes tới target URL.
    3. Trả về resourceUrl để đưa vào ProductSetInput.files.
    """
    safe_name = os.path.basename(filename) or "product_image.jpg"
    if not mime_type or mime_type == "application/octet-stream":
        guessed, _ = mimetypes.guess_type(safe_name)
        mime_type = guessed or "image/jpeg"

    staged_input = [{
        "resource": "IMAGE",
        "filename": safe_name,
        "mimeType": mime_type,
        "httpMethod": "POST"
    }]

    res = execute_shopify_graphql(client_info, STAGED_UPLOADS_CREATE_MUTATION, {"input": staged_input})
    data = res.get("data", {})
    staged_data = (data.get("stagedUploadsCreate") or {}).get("stagedTargets", [])

    if not staged_data:
        errs = (data.get("stagedUploadsCreate") or {}).get("userErrors", [])
        msg = errs[0].get("message") if errs else "Không lấy được Staged Target URL từ Shopify"
        raise Exception(f"Lỗi khởi tạo upload media: {msg}")

    target = staged_data[0]
    upload_url = target.get("url")
    resource_url = target.get("resourceUrl")
    params = target.get("parameters") or []

    # Chuẩn bị form data nhị phân
    form_data = {p["name"]: p["value"] for p in params}
    files_payload = {
        "file": (safe_name, content_bytes, mime_type)
    }

    # Upload nhị phân trực tiếp lên Cloud Storage
    upload_resp = requests.post(upload_url, data=form_data, files=files_payload, timeout=60)
    if upload_resp.status_code not in [200, 201, 204]:
        raise Exception(f"Tải file lên Cloud Storage thất bại (HTTP {upload_resp.status_code}): {upload_resp.text[:300]}")

    return resource_url


def build_product_set_input(
    payload: Dict[str, Any], 
    resolved_media_urls: List[str],
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Xây dựng object ProductSetInput chuẩn xác cho mutation productSet.
    """
    title = payload["title"].strip()
    desc_html = (payload.get("descriptionHtml") or payload.get("description") or "").strip()
    product_type = payload["productType"].strip()
    category_id = (payload.get("categoryId") or payload.get("category")).strip()
    if category_id.endswith("custom-imported") or not category_id:
        category_id = "gid://shopify/TaxonomyCategory/hg-3-47"
    status = payload.get("status", "DRAFT").strip().upper()
    vendor = payload.get("vendor", "Wrydeco").strip()

    # Tags
    raw_tags = payload.get("tags") or []
    if isinstance(raw_tags, str):
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
    else:
        tags = [str(t).strip() for t in raw_tags if str(t).strip()]

    # SEO
    seo_in = payload.get("seo") or {}
    seo = {
        "title": (seo_in.get("title") or title).strip(),
        "description": (seo_in.get("description") or "").strip()
    }

    # Options
    raw_options = payload.get("options") or []
    product_options = []
    for opt in raw_options:
        opt_name = opt["name"].strip()
        opt_values = []
        for v in opt.get("values", []):
            label = v.get("label") or v.get("name") if isinstance(v, dict) else str(v)
            opt_values.append({"name": label.strip()})
        product_options.append({
            "name": opt_name,
            "values": opt_values
        })

    # Variants
    raw_variants = payload.get("variants") or []
    variants = []
    for v in raw_variants:
        opt_vals = []
        for item in v.get("optionValues", []):
            opt_vals.append({
                "optionName": item["optionName"].strip(),
                "name": item["name"].strip()
            })

        variant_item = {
            "optionValues": opt_vals,
            "price": f"{float(v['price']):.2f}",
            "compareAtPrice": f"{float(v['compareAtPrice']):.2f}",
            "sku": str(v["sku"]).strip(),
            "barcodes": [{"value": str(v["barcode"]).strip()}]
        }
        variants.append(variant_item)

    # Metafields
    author_id = payload.get("authorId", "").strip()
    rich_desc = payload.get("richDescription", "").strip()
    aeo_html = payload.get("aeoHtml", "").strip()
    interior_styles = payload.get("interiorStyle") or []
    room_types = payload.get("roomType") or []

    metafields = [
        {
            "namespace": "custom",
            "key": "author_info",
            "value": author_id,
            "type": "metaobject_reference"
        },
        {
            "namespace": "custom",
            "key": "rich_description",
            "value": rich_desc,
            "type": "single_line_text_field"
        },
        {
            "namespace": "custom",
            "key": "aeo_html",
            "value": aeo_html,
            "type": "multi_line_text_field"
        },
        {
            "namespace": "custom",
            "key": "interior_style",
            "value": json.dumps(interior_styles),
            "type": "list.single_line_text_field"
        },
        {
            "namespace": "custom",
            "key": "room_type",
            "value": json.dumps(room_types),
            "type": "list.single_line_text_field"
        },
        {
            "namespace": "custom",
            "key": "seo_product_title",
            "value": seo["title"],
            "type": "single_line_text_field"
        }
    ]

    # Strong Idempotency: Gán custom.bulk_import_id kiểu id nếu có idempotency_key
    if idempotency_key:
        metafields.append({
            "namespace": "custom",
            "key": "bulk_import_id",
            "value": idempotency_key,
            "type": "id"
        })

    # Files (Media)
    files = []
    for url in resolved_media_urls:
        if url and url.strip():
            files.append({
                "originalSource": url.strip(),
                "contentType": "IMAGE"
            })

    product_set_input: Dict[str, Any] = {
        "title": title,
        "descriptionHtml": desc_html,
        "productType": product_type,
        "category": category_id,
        "status": status,
        "vendor": vendor,
        "tags": tags,
        "seo": seo,
        "productOptions": product_options,
        "variants": variants,
        "metafields": metafields,
        "files": files
    }

    # Handle (URL Slug tùy chỉnh chuẩn SEO nếu người dùng chỉ định)
    handle = (payload.get("handle") or "").strip()
    if handle:
        product_set_input["handle"] = handle

    return product_set_input


def create_wrydeco_product(
    payload: Dict[str, Any], 
    uploaded_file_tuples: Optional[List[Tuple[str, bytes, str]]] = None,
    store_type: str = "custom",
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quy trình thực thi tạo sản phẩm hoàn chỉnh:
    1. Validate toàn diện payload ở server-side.
    2. Khởi tạo Shopify Client qua Proxy Safety Gate (Bảo vệ tuyệt đối cho Custom Store WRYDECO).
    3. Tải các file local lên Cloud Storage qua Staged Upload, kết hợp cùng external image URLs.
    4. Xây dựng ProductSetInput.
    5. Thực thi mutation productSet(synchronous: true, input: $input).
    6. Xử lý phản hồi, giữ lại đầy đủ userErrors.
    7. Trả về kết quả có cấu trúc.
    """
    # 1. Validation
    is_valid, validation_errors = validate_create_payload(payload)
    if not is_valid:
        return {
            "success": False,
            "phase": "validation",
            "errors": validation_errors,
            "product": None
        }

    # 2. Khởi tạo Shopify Client qua Proxy Safety Gate
    try:
        client_info = get_shopify_client(store_type=store_type, force_proxy_for_custom=True)
    except ProxySafetyException as pse:
        return {
            "success": False,
            "phase": "proxy_safety",
            "errors": [{
                "field": "proxy",
                "message": f"CHỐT CHẶN AN TOÀN: {str(pse)}",
                "code": "PROXY_SAFETY_BLOCKED"
            }],
            "product": None
        }
    except Exception as e:
        return {
            "success": False,
            "phase": "client_init",
            "errors": [{
                "field": "client",
                "message": f"Không thể khởi tạo kết nối an toàn tới Shopify Store ({store_type}): {str(e)}",
                "code": "CLIENT_INIT_FAILED"
            }],
            "product": None
        }

    # 3. Xử lý Media URLs (Cả file local và URL ảnh)
    resolved_media_urls: List[str] = []
    raw_media_items = payload.get("media") or []

    # Map các file upload từ thiết bị theo index hoặc clientId
    uploaded_files_by_index = {}
    if uploaded_file_tuples:
        for idx, (fn, content, mime) in enumerate(uploaded_file_tuples):
            uploaded_files_by_index[idx] = (fn, content, mime)

    try:
        for item in raw_media_items:
            kind = item.get("kind", "url")
            if kind == "url":
                u = (item.get("url") or "").strip()
                if u:
                    resolved_media_urls.append(u)
            elif kind == "device":
                file_idx = item.get("fileIndex")
                if file_idx is not None and file_idx in uploaded_files_by_index:
                    fn, content, mime = uploaded_files_by_index[file_idx]
                    staged_res_url = stage_and_upload_local_file(client_info, fn, content, mime)
                    resolved_media_urls.append(staged_res_url)
                elif item.get("url"):
                    resolved_media_urls.append(item.get("url").strip())
    except Exception as me:
        return {
            "success": False,
            "phase": "media_staging",
            "errors": [{
                "field": "media",
                "message": f"Lỗi tải hình ảnh media: {str(me)}",
                "code": "MEDIA_STAGING_FAILED"
            }],
            "product": None
        }

    # Đảm bảo có ít nhất 1 media URL
    if not resolved_media_urls:
        return {
            "success": False,
            "phase": "media_staging",
            "errors": [{
                "field": "media",
                "message": "Không tìm thấy URL hình ảnh hợp lệ sau khi xử lý media.",
                "code": "NO_RESOLVED_MEDIA"
            }],
            "product": None
        }

    # 4. Xây dựng ProductSetInput
    product_set_input = build_product_set_input(payload, resolved_media_urls, idempotency_key=idempotency_key)

    # 5. Thực thi productSet mutation kèm identifier.customId (Strong Idempotency)
    mutation_vars = {
        "synchronous": True,
        "input": product_set_input
    }
    if idempotency_key:
        mutation_vars["identifier"] = {
            "customId": {
                "namespace": "custom",
                "key": "bulk_import_id",
                "value": str(idempotency_key).strip()
            }
        }

    try:
        res = execute_shopify_graphql(
            client_info, 
            PRODUCT_SET_MUTATION, 
            mutation_vars
        )
    except Exception as ge:
        return {
            "success": False,
            "phase": "shopify_graphql_execution",
            "errors": [{
                "field": "graphql",
                "message": f"Lỗi gửi yêu cầu tới Shopify: {str(ge)}",
                "code": "GRAPHQL_NETWORK_ERROR"
            }],
            "product": None
        }

    # 6. Phân tích kết quả từ Shopify
    if "errors" in res and res.get("errors"):
        top_errors = res.get("errors")
        err_list = []
        for te in top_errors:
            err_list.append({
                "field": "shopify",
                "message": te.get("message", "Lỗi GraphQL không xác định"),
                "code": "SHOPIFY_TOP_LEVEL_ERROR"
            })
        return {
            "success": False,
            "phase": "shopify_api_error",
            "errors": err_list,
            "product": None
        }

    data = res.get("data", {})
    product_set_result = data.get("productSet") or {}
    user_errors = product_set_result.get("userErrors") or []

    if user_errors:
        err_list = []
        for ue in user_errors:
            field_name = ".".join(ue.get("field") or ["product"])
            err_list.append({
                "field": field_name,
                "message": ue.get("message", "Lỗi tạo sản phẩm từ Shopify"),
                "code": ue.get("code") or "SHOPIFY_USER_ERROR"
            })
        return {
            "success": False,
            "phase": "shopify_user_errors",
            "errors": err_list,
            "product": None,
            "extensions": res.get("extensions")
        }

    created_product = product_set_result.get("product")
    if not created_product or not created_product.get("id"):
        return {
            "success": False,
            "phase": "shopify_unknown",
            "errors": [{
                "field": "product",
                "message": "Shopify không trả về ID sản phẩm sau khi thực thi productSet.",
                "code": "NO_PRODUCT_RETURNED"
            }],
            "product": None
        }

    return {
        "success": True,
        "phase": "complete",
        "errors": [],
        "product": created_product,
        "extensions": res.get("extensions")
    }
