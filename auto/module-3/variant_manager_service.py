"""
variant_manager_service.py
Quản lý chi tiết biến thể sản phẩm Shopify (Variant Matrix, Row Edit, Add Option/Value, Pricing Delta).
Tuân thủ nghiêm ngặt:
- Định hướng kiến trúc của Lead Architect (ChatGPT Web).
- Shopify Admin GraphQL API 2026-10.
- Module Proxy US Safety Gate (fail-closed cho Custom Store).
- Tính toán tiền tệ chính xác bằng Decimal.
"""

from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional
import os
import sys

from main import get_shopify_client, execute_shopify_graphql
from proxy_manager import ProxySafetyException


def _normalize_gid(entity_type: str, raw_id: Any) -> str:
    s = str(raw_id).strip()
    if s.startswith("gid://shopify/"):
        return s
    clean_num = s.split("/")[-1]
    return f"gid://shopify/{entity_type}/{clean_num}"


def get_variant_matrix(product_id: str, store_type: str = "default") -> Dict[str, Any]:
    """
    Lấy toàn bộ thông tin Options và Ma trận Biến thể (Variants) của sản phẩm.
    Hỗ trợ phân trang đầy đủ (first: 250, cursor) để không bỏ sót bất kỳ biến thể nào (tối đa 2048).
    """
    norm_store = "custom" if str(store_type or "").strip().lower() == "custom" else "default"
    client_info = get_shopify_client(store_type=norm_store)
    gid = _normalize_gid("Product", product_id)

    query = """
    query getProductVariantMatrix($id: ID!, $cursor: String) {
      product(id: $id) {
        id
        title
        handle
        options {
          id
          name
          position
          values
        }
        variants(first: 250, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          edges {
            node {
              id
              title
              sku
              barcode
              price
              compareAtPrice
              image {
                url
              }
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

    cursor = None
    all_variants_nodes = []
    product_meta = {}

    while True:
        vars_payload = {"id": gid, "cursor": cursor}
        res = execute_shopify_graphql(client_info, query, variables=vars_payload)
        
        if not res or "data" not in res:
            err_msg = "Không thể lấy dữ liệu từ Shopify GraphQL"
            if res and "errors" in res:
                err_msg = "; ".join([e.get("message", "") for e in res["errors"]])
            return {"success": False, "message": err_msg}

        prod_data = res["data"].get("product")
        if not prod_data:
            return {"success": False, "message": f"Không tìm thấy sản phẩm có ID: {product_id}"}

        if not product_meta:
            product_meta = {
                "id": prod_data.get("id"),
                "title": prod_data.get("title"),
                "handle": prod_data.get("handle"),
                "options": prod_data.get("options") or []
            }

        variants_conn = prod_data.get("variants") or {}
        edges = variants_conn.get("edges") or []
        for edge in edges:
            node = edge.get("node")
            if node:
                all_variants_nodes.append(node)

        page_info = variants_conn.get("pageInfo") or {}
        if page_info.get("hasNextPage") and page_info.get("endCursor"):
            cursor = page_info["endCursor"]
        else:
            break

    # Build clean variant list
    variants_clean = []
    for node in all_variants_nodes:
        v_id = node.get("id", "")
        clean_num = v_id.split("/")[-1] if v_id else ""
        variants_clean.append({
            "id": clean_num,
            "gid": v_id,
            "title": node.get("title") or "",
            "price": str(node.get("price") or "0.00"),
            "compare_at_price": str(node.get("compareAtPrice") or "") if node.get("compareAtPrice") else "",
            "sku": node.get("sku") or "",
            "barcode": node.get("barcode") or "",
            "image_url": node.get("image", {}).get("url") if node.get("image") else None,
            "selected_options": node.get("selectedOptions") or []
        })

    return {
        "success": True,
        "store_type": norm_store,
        "product": {
            "id": product_meta.get("id"),
            "title": product_meta.get("title"),
            "handle": product_meta.get("handle"),
            "option_count": len(product_meta.get("options") or []),
            "variant_count": len(variants_clean)
        },
        "options": product_meta.get("options") or [],
        "variants": variants_clean
    }


def update_variant_row(
    product_id: str,
    variant_id: str,
    option_name_changes: Optional[List[Dict[str, Any]]] = None,
    option_value_changes: Optional[List[Dict[str, Any]]] = None,
    price: Optional[str] = None,
    compare_at_price: Optional[str] = None,
    store_type: str = "default"
) -> Dict[str, Any]:
    """
    Cập nhật dữ liệu cho 1 dòng biến thể (Option Name global, Option Value row-specific, Price, Compare-at Price).
    Tuân thủ đúng semantics của Shopify:
    1. Option Name: Thuộc tính cấp Product Option -> dùng productOptionUpdate với variantStrategy: LEAVE_AS_IS.
    2. Option Value: Row-specific reassignment -> Nếu value mới chưa có, tạo trước qua productOptionUpdate(optionValuesToAdd), sau đó dùng productVariantsBulkUpdate.
    3. Price / Compare-at: Kiểm tra logic và cập nhật qua productVariantsBulkUpdate.
    4. Kiểm tra chống trùng lặp tổ hợp biến thể (Duplicate combination check).
    """
    norm_store = "custom" if str(store_type or "").strip().lower() == "custom" else "default"
    client_info = get_shopify_client(store_type=norm_store)
    p_gid = _normalize_gid("Product", product_id)
    v_gid = _normalize_gid("ProductVariant", variant_id)

    # 1. Validate và chuẩn hóa giá tiền bằng Decimal
    parsed_price = None
    if price is not None and str(price).strip() != "":
        try:
            d_price = Decimal(str(price).strip())
            if d_price < Decimal("0"):
                return {"success": False, "message": "Giá bán của biến thể không được là số âm."}
            parsed_price = f"{d_price:.2f}"
        except InvalidOperation:
            return {"success": False, "message": f"Giá bán '{price}' không hợp lệ."}

    parsed_compare_at = None
    if compare_at_price is not None and str(compare_at_price).strip() != "":
        try:
            d_compare = Decimal(str(compare_at_price).strip())
            if d_compare < Decimal("0"):
                return {"success": False, "message": "Giá so sánh không được là số âm."}
            if parsed_price is not None and d_compare <= Decimal(parsed_price):
                return {"success": False, "message": f"Giá so sánh (${d_compare:.2f}) phải lớn hơn giá bán (${parsed_price})."}
            parsed_compare_at = f"{d_compare:.2f}"
        except InvalidOperation:
            return {"success": False, "message": f"Giá so sánh '{compare_at_price}' không hợp lệ."}

    # 2. Xử lý đổi Option Name (Global Product Option) nếu có
    partial_applied = False
    if option_name_changes and isinstance(option_name_changes, list):
        for chg in option_name_changes:
            opt_id = chg.get("option_id")
            from_name = str(chg.get("from", "")).strip()
            to_name = str(chg.get("to", "")).strip()

            if opt_id and to_name and from_name.lower() != to_name.lower():
                opt_gid = _normalize_gid("ProductOption", opt_id)
                rename_mutation = """
                mutation renameProductOption($productId: ID!, $option: OptionUpdateInput!, $variantStrategy: ProductOptionUpdateVariantStrategy) {
                  productOptionUpdate(productId: $productId, option: $option, variantStrategy: $variantStrategy) {
                    userErrors {
                      field
                      message
                    }
                    product {
                      id
                      options {
                        id
                        name
                        values
                      }
                    }
                  }
                }
                """
                rename_vars = {
                    "productId": p_gid,
                    "option": {"id": opt_gid, "name": to_name},
                    "variantStrategy": "LEAVE_AS_IS"
                }
                res_rename = execute_shopify_graphql(client_info, rename_mutation, variables=rename_vars)
                user_errs = (res_rename or {}).get("data", {}).get("productOptionUpdate", {}).get("userErrors") or []
                if user_errs:
                    err_msg = "; ".join([e.get("message", "") for e in user_errs])
                    return {"success": False, "message": f"Lỗi đổi tên Tùy chọn: {err_msg}", "partial_applied": partial_applied, "refresh_required": partial_applied}
                partial_applied = True

    # 3. Lấy ma trận hiện tại để kiểm tra Duplicate combination và Option Value tồn tại
    matrix_res = get_variant_matrix(product_id, store_type=norm_store)
    if not matrix_res.get("success"):
        return {**matrix_res, "partial_applied": partial_applied, "refresh_required": partial_applied}

    current_options = matrix_res.get("options") or []
    current_variants = matrix_res.get("variants") or []

    # Tìm variant hiện tại
    target_variant = None
    for v in current_variants:
        if v.get("gid") == v_gid or v.get("id") == str(variant_id):
            target_variant = v
            break

    if not target_variant:
        return {"success": False, "message": f"Không tìm thấy biến thể {variant_id} trên sản phẩm.", "partial_applied": partial_applied, "refresh_required": partial_applied}

    # Tính toán target selected options sau khi user sửa
    new_selected_map = {so.get("name"): so.get("value") for so in target_variant.get("selected_options") or []}

    option_values_payload = []
    if option_value_changes and isinstance(option_value_changes, list):
        for val_chg in option_value_changes:
            opt_id = val_chg.get("option_id")
            opt_name = val_chg.get("option_name")
            new_val_name = str(val_chg.get("to_name", "")).strip()

            if not new_val_name:
                continue

            # Tìm option trong current_options
            matching_opt = None
            for opt in current_options:
                if (opt_id and opt.get("id") == _normalize_gid("ProductOption", opt_id)) or (opt_name and opt.get("name").lower() == opt_name.lower()):
                    matching_opt = opt
                    break

            if not matching_opt:
                continue

            real_opt_name = matching_opt.get("name")
            real_opt_gid = matching_opt.get("id")
            existing_values = matching_opt.get("values") or []

            # Cập nhật map
            new_selected_map[real_opt_name] = new_val_name

            # Nếu value mới chưa tồn tại trên Shopify, tạo value trước bằng productOptionUpdate
            if new_val_name not in existing_values:
                add_val_mutation = """
                mutation addOptionValueToOption($productId: ID!, $option: OptionUpdateInput!, $optionValuesToAdd: [OptionValueCreateInput!], $variantStrategy: ProductOptionUpdateVariantStrategy) {
                  productOptionUpdate(productId: $productId, option: $option, optionValuesToAdd: $optionValuesToAdd, variantStrategy: $variantStrategy) {
                    userErrors {
                      field
                      message
                    }
                    product {
                      id
                      options {
                        id
                        name
                        values
                      }
                    }
                  }
                }
                """
                add_val_vars = {
                    "productId": p_gid,
                    "option": {"id": real_opt_gid},
                    "optionValuesToAdd": [{"name": new_val_name}],
                    "variantStrategy": "LEAVE_AS_IS"
                }
                res_add_val = execute_shopify_graphql(client_info, add_val_mutation, variables=add_val_vars)
                add_val_errs = (res_add_val or {}).get("data", {}).get("productOptionUpdate", {}).get("userErrors") or []
                if add_val_errs:
                    err_msg = "; ".join([e.get("message", "") for e in add_val_errs])
                    return {"success": False, "message": f"Lỗi thêm giá trị biến thể mới: {err_msg}", "partial_applied": partial_applied, "refresh_required": partial_applied}
                partial_applied = True

            option_values_payload.append({
                "optionId": real_opt_gid,
                "name": new_val_name
            })

    # 4. Kiểm tra Duplicate Combination Protection
    # So sánh new_selected_map với tất cả các variants khác
    for other_v in current_variants:
        if other_v.get("gid") == v_gid or other_v.get("id") == str(variant_id):
            continue
        other_map = {so.get("name"): so.get("value") for so in other_v.get("selected_options") or []}
        if other_map and new_selected_map and len(other_map) == len(new_selected_map):
            is_dup = True
            for k, val in new_selected_map.items():
                if other_map.get(k, "").strip().lower() != val.strip().lower():
                    is_dup = False
                    break
            if is_dup:
                dup_comb_str = " / ".join([f"{k}: {v}" for k, v in new_selected_map.items()])
                return {
                    "success": False,
                    "code": "VARIANT_COMBINATION_EXISTS",
                    "message": f"Tổ hợp biến thể [{dup_comb_str}] đã tồn tại ở một biến thể khác trên sản phẩm. Không thể tạo trùng lặp.",
                    "partial_applied": partial_applied,
                    "refresh_required": partial_applied
                }

    # 5. Cập nhật Variant qua productVariantsBulkUpdate
    variant_input: Dict[str, Any] = {"id": v_gid}
    if parsed_price is not None:
        variant_input["price"] = parsed_price
    if parsed_compare_at is not None:
        variant_input["compareAtPrice"] = parsed_compare_at
    if option_values_payload:
        variant_input["optionValues"] = option_values_payload

    bulk_update_mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        userErrors {
          field
          message
        }
        productVariants {
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
    """
    bulk_vars = {
      "productId": p_gid,
      "variants": [variant_input]
    }
    res_bulk = execute_shopify_graphql(client_info, bulk_update_mutation, variables=bulk_vars)
    bulk_errs = (res_bulk or {}).get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors") or []
    if bulk_errs:
        err_msg = "; ".join([e.get("message", "") for e in bulk_errs])
        return {
            "success": False,
            "message": f"Lỗi cập nhật biến thể: {err_msg}",
            "partial_applied": partial_applied,
            "refresh_required": partial_applied
        }

    # 6. Read-back variant đã cập nhật thành công
    updated_variants = (res_bulk or {}).get("data", {}).get("productVariantsBulkUpdate", {}).get("productVariants") or []
    updated_node = updated_variants[0] if updated_variants else None

    return {
        "success": True,
        "message": "Đã lưu cập nhật biến thể thành công!",
        "partial_applied": False,
        "refresh_required": False,
        "variant": updated_node
    }


def add_variant_option_or_value(
    product_id: str,
    option_name: str,
    option_value: str,
    base_price: str = "0",
    store_type: str = "default"
) -> Dict[str, Any]:
    """
    Thêm một bộ biến thể mới: Option Name, Option Value và Option Base Price (Price Delta).
    Xử lý:
    - Nếu Option Name chưa tồn tại:
      + Kiểm tra số lượng Options < 3.
      + Tạo Option mới bằng productOptionsCreate(variantStrategy: LEAVE_AS_IS).
      + Các biến thể hiện có được gán option value này, giữ nguyên Variant ID.
      + Nếu base_price != 0, cộng delta vào giá của các biến thể hiện có.
    - Nếu Option Name đã tồn tại:
      + Thêm Option Value mới bằng productOptionUpdate(optionValuesToAdd, variantStrategy: LEAVE_AS_IS).
      + Tạo các tổ hợp mới liên quan bằng productVariantsBulkCreate với giá = source_variant.price + base_price_delta.
      + Kiểm tra giới hạn tối đa 2048 biến thể.
    """
    norm_store = "custom" if str(store_type or "").strip().lower() == "custom" else "default"
    client_info = get_shopify_client(store_type=norm_store)
    p_gid = _normalize_gid("Product", product_id)

    opt_name = str(option_name or "").strip()
    opt_val = str(option_value or "").strip()

    if not opt_name:
        return {"success": False, "message": "Vui lòng nhập Tên tùy chọn (Option Name)."}
    if not opt_val:
        return {"success": False, "message": "Vui lòng nhập Giá trị tùy chọn (Option Value)."}

    # Parse base price delta
    try:
        base_price_delta = Decimal(str(base_price or "0").strip())
    except InvalidOperation:
        return {"success": False, "message": f"Option Base Price '{base_price}' không hợp lệ."}

    # 1. Đọc matrix hiện tại
    matrix_res = get_variant_matrix(product_id, store_type=norm_store)
    if not matrix_res.get("success"):
        return matrix_res

    current_options = matrix_res.get("options") or []
    current_variants = matrix_res.get("variants") or []

    # Tìm xem option_name đã tồn tại chưa
    existing_opt = None
    for opt in current_options:
        if opt.get("name", "").strip().lower() == opt_name.lower():
            existing_opt = opt
            break

    # CASE A: Option Name MỚI hoàn toàn
    if not existing_opt:
        if len(current_options) >= 3:
            return {
                "success": False,
                "message": "Shopify chỉ hỗ trợ tối đa 3 Tùy chọn (Options) cho mỗi sản phẩm. Không thể thêm tùy chọn thứ 4."
            }

        # Gọi productOptionsCreate với LEAVE_AS_IS
        create_opt_mutation = """
        mutation productOptionsCreate($productId: ID!, $options: [OptionCreateInput!]!, $variantStrategy: ProductOptionCreateVariantStrategy) {
          productOptionsCreate(productId: $productId, options: $options, variantStrategy: $variantStrategy) {
            userErrors {
              field
              message
            }
            product {
              id
              options {
                id
                name
                values
              }
            }
          }
        }
        """
        create_opt_vars = {
            "productId": p_gid,
            "options": [{"name": opt_name, "values": [{"name": opt_val}]}],
            "variantStrategy": "LEAVE_AS_IS"
        }
        res_create_opt = execute_shopify_graphql(client_info, create_opt_mutation, variables=create_opt_vars)
        errs = (res_create_opt or {}).get("data", {}).get("productOptionsCreate", {}).get("userErrors") or []
        if errs:
            err_msg = "; ".join([e.get("message", "") for e in errs])
            return {"success": False, "message": f"Lỗi tạo Tùy chọn mới: {err_msg}", "partial_applied": False, "refresh_required": False}

        # Đã tạo Option thành công -> structural_applied = True
        # Nếu base_price_delta != 0, cập nhật giá cho các biến thể hiện tại
        if base_price_delta != Decimal("0") and current_variants:
            variants_to_update = []
            for v in current_variants:
                try:
                    cur_p = Decimal(str(v.get("price") or "0"))
                    new_p = max(Decimal("0"), cur_p + base_price_delta)
                    v_item: Dict[str, Any] = {
                        "id": v.get("gid"),
                        "price": f"{new_p:.2f}"
                    }
                    if v.get("compare_at_price"):
                        cur_comp = Decimal(str(v.get("compare_at_price")))
                        v_item["compareAtPrice"] = f"{max(Decimal('0'), cur_comp + base_price_delta):.2f}"
                    variants_to_update.append(v_item)
                except Exception:
                    pass

            if variants_to_update:
                bulk_update_mutation = """
                mutation updateVariantPrices($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    userErrors { field message }
                  }
                }
                """
                res_bulk_p = execute_shopify_graphql(client_info, bulk_update_mutation, variables={"productId": p_gid, "variants": variants_to_update})
                p_errs = (res_bulk_p or {}).get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors") or []
                if p_errs:
                    err_msg = "; ".join([e.get("message", "") for e in p_errs])
                    return {
                        "success": False,
                        "message": f"Tùy chọn mới '{opt_name}' đã được tạo trên Shopify, nhưng cập nhật giá biến thể thất bại: {err_msg}",
                        "partial_applied": True,
                        "refresh_required": True,
                        "phase": "price_bulk_update",
                        "errors": p_errs
                    }

        return {
            "success": True,
            "message": f"Đã thêm Tùy chọn mới '{opt_name}: {opt_val}' thành công! Các biến thể hiện có đã được gán giá trị này.",
            "partial_applied": False,
            "refresh_required": False,
            "is_new_option": True
        }

    # CASE B: Option Name ĐÃ TỒN TẠI -> Thêm Option Value mới và sinh các biến thể mới
    opt_gid = existing_opt.get("id")
    opt_existing_values = existing_opt.get("values") or []

    # Kiểm tra value đã có chưa
    for val in opt_existing_values:
        if str(val).strip().lower() == opt_val.lower():
            return {
                "success": False,
                "message": f"Giá trị '{opt_val}' đã tồn tại trong tùy chọn '{existing_opt.get('name')}'."
            }

    # Thêm value mới vào option qua productOptionUpdate
    add_val_mutation = """
    mutation addOptionValueToExistingOption($productId: ID!, $option: OptionUpdateInput!, $optionValuesToAdd: [OptionValueCreateInput!], $variantStrategy: ProductOptionUpdateVariantStrategy) {
      productOptionUpdate(productId: $productId, option: $option, optionValuesToAdd: $optionValuesToAdd, variantStrategy: $variantStrategy) {
        userErrors { field message }
      }
    }
    """
    res_add_val = execute_shopify_graphql(client_info, add_val_mutation, variables={
        "productId": p_gid,
        "option": {"id": opt_gid},
        "optionValuesToAdd": [{"name": opt_val}],
        "variantStrategy": "LEAVE_AS_IS"
    })
    val_errs = (res_add_val or {}).get("data", {}).get("productOptionUpdate", {}).get("userErrors") or []
    if val_errs:
        err_msg = "; ".join([e.get("message", "") for e in val_errs])
        return {"success": False, "message": f"Lỗi thêm giá trị biến thể: {err_msg}", "partial_applied": False, "refresh_required": False}

    # Đã thêm Option Value vào Option thành công trên Shopify -> structural_applied = True
    structural_applied = True

    # Tính toán các tổ hợp mới cần tạo
    # Nhóm các biến thể theo các options khác (trừ existing_opt)
    target_opt_name = existing_opt.get("name")
    
    # Tập hợp các tổ hợp của các options còn lại từ current_variants
    # Map key: tuple of (other_opt_name, other_opt_val), value: source_variant (để lấy base price)
    unique_other_combos: Dict[tuple, Dict[str, Any]] = {}
    for v in current_variants:
        other_pairs = []
        for so in v.get("selected_options") or []:
            if so.get("name") != target_opt_name:
                other_pairs.append((so.get("name"), so.get("value")))
        key = tuple(sorted(other_pairs))
        if key not in unique_other_combos:
            unique_other_combos[key] = v

    # Nếu chỉ có duy nhất 1 option trên sản phẩm:
    if not unique_other_combos:
        # Lấy 1 biến thể bất kỳ làm source variant
        src_v = current_variants[0] if current_variants else {}
        unique_other_combos[()] = src_v

    # Kiểm tra giới hạn 2048 variants
    projected_count = len(current_variants) + len(unique_other_combos)
    if projected_count > 2048:
        return {
            "success": False,
            "message": f"Số lượng biến thể sau khi thêm ({projected_count}) vượt quá giới hạn tối đa 2048 biến thể của Shopify.",
            "partial_applied": structural_applied,
            "refresh_required": structural_applied
        }

    # Tạo payload cho productVariantsBulkCreate
    new_variants_payload = []
    for combo_key, src_v in unique_other_combos.items():
        # Tính price & compareAtPrice từ source variant + base_price_delta
        src_price = Decimal(str(src_v.get("price") or "0"))
        new_price = max(Decimal("0"), src_price + base_price_delta)
        
        opt_values_item = [{"optionName": target_opt_name, "name": opt_val}]
        for opt_n, opt_v in combo_key:
            opt_values_item.append({"optionName": opt_n, "name": opt_v})

        variant_item: Dict[str, Any] = {
            "price": f"{new_price:.2f}",
            "optionValues": opt_values_item
        }
        if src_v.get("compare_at_price"):
            try:
                src_comp = Decimal(str(src_v.get("compare_at_price")))
                variant_item["compareAtPrice"] = f"{max(Decimal('0'), src_comp + base_price_delta):.2f}"
            except Exception:
                pass
        
        new_variants_payload.append(variant_item)

    if new_variants_payload:
        bulk_create_mutation = """
        mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkCreate(productId: $productId, variants: $variants) {
            userErrors {
              field
              message
            }
            productVariants {
              id
              title
              price
            }
          }
        }
        """
        res_create = execute_shopify_graphql(client_info, bulk_create_mutation, variables={
            "productId": p_gid,
            "variants": new_variants_payload
        })
        create_errs = (res_create or {}).get("data", {}).get("productVariantsBulkCreate", {}).get("userErrors") or []
        if create_errs:
            err_msg = "; ".join([e.get("message", "") for e in create_errs])
            return {
                "success": False,
                "message": f"Giá trị tùy chọn '{opt_val}' đã được tạo trên Shopify, nhưng sinh các tổ hợp biến thể mới thất bại: {err_msg}",
                "partial_applied": True,
                "refresh_required": True,
                "phase": "variant_bulk_create",
                "errors": create_errs
            }

    return {
        "success": True,
        "message": f"Đã thêm giá trị '{opt_val}' vào tùy chọn '{target_opt_name}' và sinh {len(new_variants_payload)} tổ hợp biến thể mới thành công!",
        "partial_applied": False,
        "refresh_required": False,
        "created_variants_count": len(new_variants_payload)
    }
