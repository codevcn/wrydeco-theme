"""
product_create_service.py
Service subsystem phụ trách tạo sản phẩm mới cho WRYDECO Store thông qua Shopify GraphQL Admin API.
Kiến trúc cốt lõi:
- Đảm bảo Proxy Safety Gate tuyệt đối (bắt buộc qua proxy cho Custom Store WRYDECO).
- Sử dụng mutation nguyên tử productSet(synchronous: true, input: $input) để tạo đồng thời:
  title, description, productType, category, status, vendor, tags, seo, productOptions,
  variants (kèm price, compareAtPrice, sku, barcode riêng từng biến thể), metafields.
- Gắn media riêng qua productUpdate và xác minh toàn bộ ảnh READY trước khi báo thành công.
- Kiểm tra toàn vẹn server-side (Cartesian reconstruction, uniqueness check, whitelist validation).
- Xử lý upload media đa nguồn (local device qua stagedUploadsCreate + external image URLs).
"""

import os
import sys
import json
import uuid
import mimetypes
import itertools
import logging
import time
import hashlib
from typing import Dict, Any, List, Tuple, Optional

import requests
import product_media_service as media_import
from proxy_manager import (
    get_shopify_client, 
    execute_shopify_graphql, 
    ProxySafetyException,
    get_shopify_request_proxies
)

logger = logging.getLogger(__name__)

PRODUCT_MEDIA_FIELDS = """
  id
  mediaContentType
  status
  mediaErrors { code message }
  ... on MediaImage { image { url } }
"""

ADD_PRODUCT_MEDIA_MUTATION = """
mutation AddCreatedProductMedia($product: ProductUpdateInput!, $media: [CreateMediaInput!]!) {
  productUpdate(product: $product, media: $media) {
    product {
      id
      media(first: 250) { nodes { """ + PRODUCT_MEDIA_FIELDS + """ } }
    }
    userErrors { field message }
  }
}
"""

PRODUCT_MEDIA_QUERY = """
query CreatedProductMedia($id: ID!) {
  product(id: $id) {
    id
    media(first: 250) { nodes { """ + PRODUCT_MEDIA_FIELDS + """ } }
  }
}
"""


def wait_for_product_media(
    client_info: Dict[str, Any],
    product_id: str,
    expected_count: int,
    initial_product: Optional[Dict[str, Any]] = None,
    max_attempts: int = 45,
    poll_interval: float = 2.0,
) -> Dict[str, Any]:
    """Verify every image is attached, READY, and has a public URL before success."""
    product = initial_product or {}
    nodes = []
    for attempt in range(max_attempts):
        if attempt or not initial_product:
            try:
                response = execute_shopify_graphql(client_info, PRODUCT_MEDIA_QUERY, {"id": product_id})
            except Exception as exc:
                return {"success": False, "phase": "media_processing", "errors": [
                    {"field": "media", "code": "MEDIA_VERIFICATION_FAILED", "message": str(exc)}
                ]}
            if response.get("errors"):
                return {"success": False, "phase": "media_processing", "errors": [
                    {"field": "media", "code": "MEDIA_VERIFICATION_FAILED", "message": e.get("message", "Không thể kiểm tra ảnh trên Shopify.")}
                    for e in response["errors"]
                ]}
            product = (response.get("data") or {}).get("product") or {}
        nodes = (product.get("media") or {}).get("nodes") or []
        errors = []
        for index, node in enumerate(nodes):
            if node.get("status") == "FAILED" or node.get("mediaErrors"):
                details = node.get("mediaErrors") or [{"message": "Shopify không xử lý được ảnh."}]
                errors.extend({
                    "field": f"media.{index}", "code": "MEDIA_PROCESSING_FAILED",
                    "message": f"Ảnh #{index + 1}: {e.get('message') or e.get('code') or 'Media processing failed'}"
                } for e in details)
        if errors:
            return {"success": False, "phase": "media_processing", "errors": errors, "media": {"nodes": nodes}}
        if len(nodes) == expected_count and all(
            n.get("status") == "READY" and (n.get("image") or {}).get("url") for n in nodes
        ):
            return {"success": True, "media": {"nodes": nodes}, "errors": []}
        if attempt < max_attempts - 1:
            time.sleep(poll_interval)
    ready_count = sum(n.get("status") == "READY" and bool((n.get("image") or {}).get("url")) for n in nodes)
    return {"success": False, "phase": "media_processing", "media": {"nodes": nodes}, "errors": [{
        "field": "media", "code": "MEDIA_PROCESSING_TIMEOUT",
        "message": f"Ảnh chưa hoàn tất trên Shopify: {ready_count}/{expected_count} ảnh sẵn sàng. Vui lòng kiểm tra sản phẩm đã tạo trước khi thử lại."
    }]}


def attach_created_product_media(
    client_info: Dict[str, Any], product_id: str, media_inputs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Use productUpdate's media pipeline; productSet file processing can fail later."""
    try:
        response = execute_shopify_graphql(
            client_info, ADD_PRODUCT_MEDIA_MUTATION,
            {"product": {"id": product_id}, "media": media_inputs},
        )
    except Exception as exc:
        return {"success": False, "phase": "media_creation", "errors": [
            {"field": "media", "code": "MEDIA_CREATION_FAILED", "message": str(exc)}
        ]}
    result = (response.get("data") or {}).get("productUpdate") or {}
    errors = response.get("errors") or result.get("userErrors") or []
    if errors:
        return {"success": False, "phase": "media_creation", "errors": [{
            "field": ".".join(e.get("field") or ["media"]),
            "code": "MEDIA_CREATION_FAILED", "message": e.get("message", "Không thể gắn ảnh vào sản phẩm.")
        } for e in errors]}
    if not result.get("product") or result["product"].get("id") != product_id:
        return {"success": False, "phase": "media_creation", "errors": [{
            "field": "media", "code": "MEDIA_CREATION_FAILED",
            "message": "Shopify không trả về sản phẩm khi gắn ảnh."
        }]}
    return wait_for_product_media(
        client_info, product_id, len(media_inputs), initial_product=result.get("product")
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
    Xác thực cấu trúc Variation (hỗ trợ cả Full Cartesian Matrix lẫn Valid Non-Exhaustive / Sparse Variants):
    - 1 <= len(options) <= 3
    - Tên options không trùng lặp, không rỗng
    - Các giá trị trong mỗi option không rỗng, không trùng lặp
    - 1 <= len(variants) <= 2048 (tập con hợp lệ của tích Descartes, không trùng tổ hợp)
    - Mọi giá trị khai báo trong từng option phải được sử dụng bởi ít nhất 1 biến thể (không có orphaned option value)
    - Mỗi biến thể bắt buộc có: Price (>= 0), Compare-at price (> Price), SKU (không trùng), Barcode (không trùng)
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

    # Tính kích thước tích Descartes lý thuyết
    cartesian_size = 1
    for opt in cleaned_options:
        cartesian_size *= len(opt["values"])

    variants_list = variants if isinstance(variants, list) else []
    actual_count = len(variants_list)

    if actual_count > 2048 or (actual_count == 0 and cartesian_size > 2048):
        exceeded = actual_count if actual_count > 2048 else cartesian_size
        add_err("variants", f"Tổng số lượng biến thể ({exceeded}) vượt quá giới hạn tối đa của Shopify (2048 biến thể).")
        return (False, errors)

    if actual_count == 0:
        add_err("variants", "Danh sách biến thể không được rỗng.")
        return (False, errors)

    if actual_count > cartesian_size:
        add_err("variants", f"Số lượng biến thể được gửi ({actual_count}) vượt quá số tổ hợp tối đa ({cartesian_size}).")

    # Từ điển tra cứu giá trị hợp lệ theo từng option (case-insensitive -> canonical label)
    allowed_values_per_opt = [
        {v.lower(): v for v in opt["values"]}
        for opt in cleaned_options
    ]
    used_values_per_opt = [set() for _ in cleaned_options]

    # Bản đồ kiểm tra tính duy nhất của SKU, Barcode và tổ hợp biến thể
    seen_skus = set()
    seen_barcodes = set()
    matched_combinations = set()

    for v_idx, v in enumerate(variants_list):
        row_label = f"Biến thể #{v_idx + 1}"
        
        # 1. Trích xuất option values của row
        opt_values_input = v.get("optionValues") or []
        raw_tuple_vals = []

        if isinstance(opt_values_input, list):
            # Format: [{"optionName": "...", "name": "..."}]
            name_map = {}
            for item in opt_values_input:
                if isinstance(item, dict):
                    name_map[item.get("optionName", "").strip().lower()] = item.get("name", "").strip()
            
            for opt in cleaned_options:
                raw_tuple_vals.append(name_map.get(opt["name"].lower(), ""))

        elif isinstance(opt_values_input, dict):
            lower_dict = {str(k).strip().lower(): str(val).strip() for k, val in opt_values_input.items()}
            for opt in cleaned_options:
                raw_tuple_vals.append(lower_dict.get(opt["name"].lower(), ""))

        if len(raw_tuple_vals) == len(cleaned_options):
            is_comb_valid = True
            canonical_vals = []
            for opt_idx, raw_val in enumerate(raw_tuple_vals):
                val_lower = raw_val.lower()
                if not raw_val or val_lower not in allowed_values_per_opt[opt_idx]:
                    is_comb_valid = False
                    canonical_vals.append(raw_val or "?")
                else:
                    canonical_vals.append(allowed_values_per_opt[opt_idx][val_lower])
                    used_values_per_opt[opt_idx].add(val_lower)

            comb_display = " / ".join(canonical_vals)
            comb_key = tuple(val.lower() for val in canonical_vals)

            if not is_comb_valid:
                add_err(f"variants[{v_idx}]", f"{row_label}: Tổ hợp biến thể {comb_display} không hợp lệ (không tồn tại trong ma trận tùy chọn).")
            elif comb_key in matched_combinations:
                add_err(f"variants[{v_idx}]", f"{row_label}: Tổ hợp biến thể {comb_display} bị khai báo lặp lại.")
            else:
                matched_combinations.add(comb_key)
        else:
            add_err(f"variants[{v_idx}]", f"{row_label}: Thiếu thông tin giá trị tùy chọn (optionValues).")

        # 2. Price ($) - Bắt buộc
        raw_price = str(v.get("price") if v.get("price") is not None else "").strip()
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
        raw_compare = str(v.get("compareAtPrice") if v.get("compareAtPrice") is not None else "").strip()
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

    # Kiểm tra không có giá trị tùy chọn mồ côi (Orphaned option values):
    # Mọi giá trị khai báo trong options đều phải được sử dụng bởi ít nhất 1 biến thể thực tế
    for opt_idx, opt in enumerate(cleaned_options):
        unused_vals = [val for val in opt["values"] if val.lower() not in used_values_per_opt[opt_idx]]
        if unused_vals:
            add_err(
                f"options[{opt_idx}].values",
                f"Giá trị tùy chọn ({', '.join(unused_vals)}) trong '{opt['name']}' không được sử dụng bởi bất kỳ biến thể nào."
            )

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
    upload_resp = requests.post(upload_url, data=form_data, files=files_payload,
                                proxies=client_info.get("proxies"), timeout=60)
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

    # Options (kèm map chuẩn hóa chữ hoa/thường để khớp 100% với Shopify productOptions)
    raw_options = payload.get("options") or []
    product_options = []
    canonical_opt_map: Dict[str, Dict[str, Any]] = {}
    for opt in raw_options:
        opt_name = opt["name"].strip()
        opt_values = []
        val_map: Dict[str, str] = {}
        for v in opt.get("values", []):
            label = v.get("label") or v.get("name") if isinstance(v, dict) else str(v)
            clean_label = label.strip()
            opt_values.append({"name": clean_label})
            val_map[clean_label.lower()] = clean_label
        product_options.append({
            "name": opt_name,
            "values": opt_values
        })
        canonical_opt_map[opt_name.lower()] = {
            "name": opt_name,
            "values": val_map
        }

    # Variants (hỗ trợ cả Full Cartesian lẫn Sparse / Non-Exhaustive Variants)
    raw_variants = payload.get("variants") or []
    variants = []
    for v in raw_variants:
        opt_vals = []
        for item in v.get("optionValues", []):
            raw_opt_name = item["optionName"].strip()
            raw_val_name = item["name"].strip()
            opt_entry = canonical_opt_map.get(raw_opt_name.lower())
            canon_opt_name = opt_entry["name"] if opt_entry else raw_opt_name
            canon_val_name = opt_entry["values"].get(raw_val_name.lower(), raw_val_name) if opt_entry else raw_val_name
            opt_vals.append({
                "optionName": canon_opt_name,
                "name": canon_val_name
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
        "metafields": metafields
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
    idempotency_key: Optional[str] = None,
    resume_product_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quy trình thực thi tạo sản phẩm hoàn chỉnh:
    1. Validate toàn diện payload ở server-side.
    2. Khởi tạo Shopify Client qua Proxy Safety Gate (Bảo vệ tuyệt đối cho Custom Store WRYDECO).
    3. Tải các file local lên Cloud Storage qua Staged Upload, kết hợp cùng external image URLs.
    4. Xây dựng ProductSetInput.
    5. Thực thi mutation productSet(synchronous: true, input: $input).
    6. Gắn ảnh qua productUpdate và chờ đủ ảnh READY cùng URL công khai.
    7. Giữ đầy đủ userErrors và ID sản phẩm nếu bước xử lý ảnh thất bại.
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

    for item in payload.get("media") or []:
        index = item.get("fileIndex")
        if item.get("kind") == "device" and isinstance(index, int) and uploaded_file_tuples and 0 <= index < len(uploaded_file_tuples):
            item["contentHash"] = hashlib.sha256(uploaded_file_tuples[index][1]).hexdigest()
    owned_import = media_import.find_owned_import(payload, store_type)
    if resume_product_id:
        if owned_import and owned_import["product_id"] != resume_product_id:
            return {"success": False, "phase": "validation", "product": None,
                    "errors": [{"field": "product", "code": "IMPORT_RECEIPT_MISMATCH", "message": "ID sản phẩm không khớp bản import đã lưu."}]}
        owned_import = owned_import or {"product_id": resume_product_id, "manifest": {}}

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
                    media_import.cache_image(staged_res_url, content)
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

    # 5. Thực thi productSet mutation
    mutation_vars = {
        "synchronous": True,
        "input": product_set_input
    }

    media_inputs = [{"originalSource": url, "mediaContentType": "IMAGE",
                     "alt": str(raw_media_items[index].get("alt") or payload.get("title") or "")}
                    for index, url in enumerate(resolved_media_urls)]
    resumed = None
    if owned_import:
        try:
            resumed = media_import._nodes(client_info, owned_import["product_id"], len(media_inputs))
        except media_import.MissingImportedProduct:
            # A deliberately deleted import may be recreated; a different product is protected.
            owned_import = None
            if check_shopify_product_exists_by_handle(str(payload.get("handle") or ""), store_type):
                return {"success": False, "phase": "validation", "product": None,
                        "errors": [{"field": "handle", "code": "HANDLE_EXISTS", "message": "Handle đang thuộc sản phẩm khác; đã chặn tạo trùng."}]}
        except Exception as exc:
            return {"success": False, "phase": "media_processing", "product": None,
                    "errors": [{"field": "media", "code": "MEDIA_VERIFICATION_FAILED", "message": str(exc)}]}
    if not owned_import:
        try:
            media_import.preflight_images(client_info, media_inputs)
        except Exception as exc:
            return {"success": False, "phase": "media_staging", "product": None,
                    "errors": [{"field": "media", "code": "IMAGE_PREFLIGHT_FAILED", "message": str(exc)}]}
    try:
        if owned_import:
            if resumed.get("handle") != str(payload.get("handle") or "").strip():
                raise ValueError("Handle không khớp sản phẩm đã tạo; đã dừng để tránh sửa nhầm.")
            resumed["title"] = payload.get("title", "")
            res = {"data": {"productSet": {"product": resumed, "userErrors": []}}}
        else:
            # Validate/cache all source bytes before creating any product shell.
            res = execute_shopify_graphql(client_info, PRODUCT_SET_MUTATION, mutation_vars,
                                          retry_ambiguous=False)
    except Exception as ge:
        return {
            "success": False,
            "phase": "shopify_graphql_execution",
            "errors": [{
                "field": "graphql",
                "message": f"Lỗi gửi yêu cầu tới Shopify: {str(ge)}",
                "code": "GRAPHQL_NETWORK_ERROR"
            }],
            "product": None,
            "resolved_media_urls": resolved_media_urls
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
            "product": None,
            "resolved_media_urls": resolved_media_urls
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
            "extensions": res.get("extensions"),
            "resolved_media_urls": resolved_media_urls
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
            "product": None,
            "resolved_media_urls": resolved_media_urls
        }

    manifest = (owned_import or {}).get("manifest") or {}
    def save_progress(value):
        media_import.save_receipt(payload, store_type, created_product["id"], value)
    try:
        save_progress(manifest)
        created_product["media"] = media_import.ensure_product_media(
            client_info, created_product, media_inputs, manifest, save_progress,
            stage_and_upload_local_file,
        )
    except Exception as exc:
        return {"success": False, "phase": "media_processing", "product": created_product,
                "product_created": True, "extensions": res.get("extensions"),
                "resolved_media_urls": resolved_media_urls, "errors": [{
                    "field": "media", "code": "MEDIA_IMPORT_INCOMPLETE",
                    "message": f"Sản phẩm {created_product['id'].split('/')[-1]} đã được tạo; ảnh chưa hoàn tất. {exc} Có thể chạy lại cùng dữ liệu để tiếp tục, không tạo sản phẩm trùng."
                }]}

    return {
        "success": True,
        "phase": "complete",
        "errors": [],
        "product": created_product,
        "extensions": res.get("extensions"),
        "resolved_media_urls": resolved_media_urls
    }
