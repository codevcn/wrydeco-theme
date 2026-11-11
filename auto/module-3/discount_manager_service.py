"""
discount_manager_service.py
Service layer xử lý nghiệp vụ Quản lý Discount trên Shopify Admin Manager.
Tuân thủ Technical Direction & Review Criteria của Lead Architect:
- Polymorphic GraphQL union mapping cho 8 subtypes
- Capability-based resolution & strict readonly gating cho BXGY/App
- Patch-style mutation routing (Code Basic, Automatic Basic, Code FreeShipping, Automatic FreeShipping)
- Optimistic concurrency protection (updatedAt check -> HTTP 409 DISCOUNT_STALE)
- Giữ nguyên data integrity (appliesOnEachItem, context preservation)
- Hỗ trợ Context / Eligibility (All, CustomerSegments add/remove, Customers, Markets, Unknown)
- Graceful degradation khi thiếu quyền read_customers
- Retain đầy đủ GraphQL errors & userErrors
"""

from decimal import Decimal
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class DiscountException(Exception):
    def __init__(self, message: str, code: str = "DISCOUNT_ERROR", phase: str = "service", errors: list = None, refresh_required: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.phase = phase
        self.errors = errors or [{"field": [], "message": message, "code": code}]
        self.refresh_required = refresh_required

class DiscountStaleException(DiscountException):
    def __init__(self, message: str = "Discount đã được cập nhật bởi một người dùng khác hoặc trên Shopify Admin. Vui lòng tải lại trang."):
        super().__init__(message=message, code="DISCOUNT_STALE", phase="preflight", refresh_required=True)

class DiscountUnsupportedException(DiscountException):
    def __init__(self, message: str):
        super().__init__(message=message, code="DISCOUNT_UNSUPPORTED", phase="preflight", refresh_required=False)

class DiscountValidationException(DiscountException):
    def __init__(self, message: str, field: str = ""):
        errors = [{"field": [field] if field else [], "message": message, "code": "INVALID_VALUE"}]
        super().__init__(message=message, code="VALIDATION_ERROR", phase="validation", errors=errors, refresh_required=False)


# GraphQL Context Fragment
CONTEXT_FRAGMENT = """
    context {
      __typename
      ... on DiscountBuyerSelectionAll {
        all
      }
      ... on DiscountCustomerSegments {
        segments {
          id
          name
        }
      }
      ... on DiscountCustomers {
        customers {
          id
          displayName
        }
      }
      ... on DiscountMarkets {
        marketsCount
      }
      ... on DiscountContextUnknown {
        contextType
      }
    }
"""

# GraphQL Query Fragment cho tất cả 8 subtype
DISCOUNT_FRAGMENT = f"""
fragment DiscountFields on Discount {{
  __typename
  ... on DiscountCodeBasic {{
    title
    status
    summary
    startsAt
    endsAt
    updatedAt
    asyncUsageCount
    usageLimit
    appliesOncePerCustomer
    combinesWith {{
      orderDiscounts
      productDiscounts
      shippingDiscounts
    }}
    codes(first: 5) {{
      nodes {{
        code
      }}
    }}
    codesCount {{
      count
      precision
    }}
    customerGets {{
      value {{
        __typename
        ... on DiscountPercentage {{
          percentage
        }}
        ... on DiscountAmount {{
          amount {{
            amount
            currencyCode
          }}
          appliesOnEachItem
        }}
      }}
      items {{
        __typename
        ... on AllDiscountItems {{
          allItems
        }}
      }}
    }}
    minimumRequirement {{
      __typename
      ... on DiscountMinimumSubtotal {{
        greaterThanOrEqualToSubtotal {{
          amount
          currencyCode
        }}
      }}
      ... on DiscountMinimumQuantity {{
        greaterThanOrEqualToQuantity
      }}
    }}
{CONTEXT_FRAGMENT}
  }}
  ... on DiscountAutomaticBasic {{
    title
    status
    summary
    startsAt
    endsAt
    updatedAt
    asyncUsageCount
    combinesWith {{
      orderDiscounts
      productDiscounts
      shippingDiscounts
    }}
    customerGets {{
      value {{
        __typename
        ... on DiscountPercentage {{
          percentage
        }}
        ... on DiscountAmount {{
          amount {{
            amount
            currencyCode
          }}
          appliesOnEachItem
        }}
      }}
      items {{
        __typename
        ... on AllDiscountItems {{
          allItems
        }}
      }}
    }}
    minimumRequirement {{
      __typename
      ... on DiscountMinimumSubtotal {{
        greaterThanOrEqualToSubtotal {{
          amount
          currencyCode
        }}
      }}
      ... on DiscountMinimumQuantity {{
        greaterThanOrEqualToQuantity
      }}
    }}
{CONTEXT_FRAGMENT}
  }}
  ... on DiscountCodeFreeShipping {{
    title
    status
    summary
    startsAt
    endsAt
    updatedAt
    asyncUsageCount
    usageLimit
    appliesOncePerCustomer
    combinesWith {{
      orderDiscounts
      productDiscounts
      shippingDiscounts
    }}
    codes(first: 5) {{
      nodes {{
        code
      }}
    }}
    codesCount {{
      count
      precision
    }}
    minimumRequirement {{
      __typename
      ... on DiscountMinimumSubtotal {{
        greaterThanOrEqualToSubtotal {{
          amount
          currencyCode
        }}
      }}
      ... on DiscountMinimumQuantity {{
        greaterThanOrEqualToQuantity
      }}
    }}
{CONTEXT_FRAGMENT}
  }}
  ... on DiscountAutomaticFreeShipping {{
    title
    status
    summary
    startsAt
    endsAt
    updatedAt
    asyncUsageCount
    combinesWith {{
      orderDiscounts
      productDiscounts
      shippingDiscounts
    }}
    minimumRequirement {{
      __typename
      ... on DiscountMinimumSubtotal {{
        greaterThanOrEqualToSubtotal {{
          amount
          currencyCode
        }}
      }}
      ... on DiscountMinimumQuantity {{
        greaterThanOrEqualToQuantity
      }}
    }}
{CONTEXT_FRAGMENT}
  }}
  ... on DiscountCodeBxgy {{
    title
    status
    summary
    startsAt
    endsAt
    updatedAt
    asyncUsageCount
    usageLimit
    appliesOncePerCustomer
    combinesWith {{
      orderDiscounts
      productDiscounts
      shippingDiscounts
    }}
    codes(first: 5) {{
      nodes {{
        code
      }}
    }}
    codesCount {{
      count
      precision
    }}
{CONTEXT_FRAGMENT}
  }}
  ... on DiscountAutomaticBxgy {{
    title
    status
    summary
    startsAt
    endsAt
    updatedAt
    asyncUsageCount
    combinesWith {{
      orderDiscounts
      productDiscounts
      shippingDiscounts
    }}
{CONTEXT_FRAGMENT}
  }}
  ... on DiscountCodeApp {{
    title
    status
    startsAt
    endsAt
    updatedAt
    asyncUsageCount
    combinesWith {{
      orderDiscounts
      productDiscounts
      shippingDiscounts
    }}
    codes(first: 5) {{
      nodes {{
        code
      }}
    }}
    codesCount {{
      count
      precision
    }}
  }}
  ... on DiscountAutomaticApp {{
    title
    status
    startsAt
    endsAt
    updatedAt
    asyncUsageCount
    combinesWith {{
      orderDiscounts
      productDiscounts
      shippingDiscounts
    }}
  }}
}}
"""

QUERY_LIST_DISCOUNTS = f"""
query ListDiscounts($first: Int!, $after: String, $query: String) {{
  discountNodes(first: $first, after: $after, sortKey: CREATED_AT, reverse: true, query: $query) {{
    pageInfo {{
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }}
    edges {{
      cursor
      node {{
        id
        discount {{
          ...DiscountFields
        }}
      }}
    }}
  }}
}}
{DISCOUNT_FRAGMENT}
"""

QUERY_DISCOUNT_DETAIL = f"""
query GetDiscountDetail($id: ID!) {{
  discountNode(id: $id) {{
    id
    discount {{
      ...DiscountFields
    }}
  }}
}}
{DISCOUNT_FRAGMENT}
"""

# Mutations cho từng loại
MUTATION_CODE_BASIC_UPDATE = """
mutation UpdateDiscountCodeBasic($id: ID!, $basicCodeDiscount: DiscountCodeBasicInput!) {
  discountCodeBasicUpdate(id: $id, basicCodeDiscount: $basicCodeDiscount) {
    codeDiscountNode {
      id
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

MUTATION_AUTOMATIC_BASIC_UPDATE = """
mutation UpdateDiscountAutomaticBasic($id: ID!, $automaticBasicDiscount: DiscountAutomaticBasicInput!) {
  discountAutomaticBasicUpdate(id: $id, automaticBasicDiscount: $automaticBasicDiscount) {
    automaticDiscountNode {
      id
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

MUTATION_CODE_FREE_SHIPPING_UPDATE = """
mutation UpdateDiscountCodeFreeShipping($id: ID!, $freeShippingCodeDiscount: DiscountCodeFreeShippingInput!) {
  discountCodeFreeShippingUpdate(id: $id, freeShippingCodeDiscount: $freeShippingCodeDiscount) {
    codeDiscountNode {
      id
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

MUTATION_AUTOMATIC_FREE_SHIPPING_UPDATE = """
mutation UpdateDiscountAutomaticFreeShipping($id: ID!, $freeShippingAutomaticDiscount: DiscountAutomaticFreeShippingInput!) {
  discountAutomaticFreeShippingUpdate(id: $id, freeShippingAutomaticDiscount: $freeShippingAutomaticDiscount) {
    automaticDiscountNode {
      id
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

MUTATION_CODE_ACTIVATE = """
mutation discountCodeActivate($id: ID!) {
  discountCodeActivate(id: $id) {
    codeDiscountNode {
      id
      codeDiscount {
        ... on DiscountCodeBasic { status updatedAt }
        ... on DiscountCodeFreeShipping { status updatedAt }
        ... on DiscountCodeBxgy { status updatedAt }
        ... on DiscountCodeApp { status updatedAt }
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

MUTATION_CODE_DEACTIVATE = """
mutation discountCodeDeactivate($id: ID!) {
  discountCodeDeactivate(id: $id) {
    codeDiscountNode {
      id
      codeDiscount {
        ... on DiscountCodeBasic { status updatedAt }
        ... on DiscountCodeFreeShipping { status updatedAt }
        ... on DiscountCodeBxgy { status updatedAt }
        ... on DiscountCodeApp { status updatedAt }
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

MUTATION_AUTOMATIC_ACTIVATE = """
mutation discountAutomaticActivate($id: ID!) {
  discountAutomaticActivate(id: $id) {
    automaticDiscountNode {
      id
      automaticDiscount {
        ... on DiscountAutomaticBasic { status updatedAt }
        ... on DiscountAutomaticFreeShipping { status updatedAt }
        ... on DiscountAutomaticBxgy { status updatedAt }
        ... on DiscountAutomaticApp { status updatedAt }
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

MUTATION_AUTOMATIC_DEACTIVATE = """
mutation discountAutomaticDeactivate($id: ID!) {
  discountAutomaticDeactivate(id: $id) {
    automaticDiscountNode {
      id
      automaticDiscount {
        ... on DiscountAutomaticBasic { status updatedAt }
        ... on DiscountAutomaticFreeShipping { status updatedAt }
        ... on DiscountAutomaticBxgy { status updatedAt }
        ... on DiscountAutomaticApp { status updatedAt }
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



def resolve_discount_capabilities(typename: str, discount: dict) -> dict:
    """Xác định khả năng chỉnh sửa cho từng subtype."""
    if typename == "DiscountCodeBasic":
        code_count = 1
        if discount.get("codesCount"):
            code_count = discount["codesCount"].get("count", 1)
        elif discount.get("codes", {}).get("nodes"):
            code_count = len(discount["codes"]["nodes"])
        
        return {
            "editable": True,
            "can_edit_code": (code_count <= 1),
            "can_edit_title": True,
            "can_edit_discount_value": True,
            "can_edit_minimum_requirement": True,
            "can_edit_usage_limit": True,
            "can_edit_once_per_customer": True,
            "can_edit_combinations": True,
            "can_edit_schedule": True,
            "can_edit_eligibility": True,
            "readonly_reason": None,
            "is_automatic": False,
            "mutation_type": "discountCodeBasicUpdate"
        }
    elif typename == "DiscountAutomaticBasic":
        return {
            "editable": True,
            "can_edit_code": False,
            "can_edit_title": True,
            "can_edit_discount_value": True,
            "can_edit_minimum_requirement": True,
            "can_edit_usage_limit": False,
            "can_edit_once_per_customer": False,
            "can_edit_combinations": True,
            "can_edit_schedule": True,
            "can_edit_eligibility": True,
            "readonly_reason": None,
            "is_automatic": True,
            "mutation_type": "discountAutomaticBasicUpdate"
        }
    elif typename == "DiscountCodeFreeShipping":
        code_count = 1
        if discount.get("codesCount"):
            code_count = discount["codesCount"].get("count", 1)
        elif discount.get("codes", {}).get("nodes"):
            code_count = len(discount["codes"]["nodes"])
        return {
            "editable": True,
            "can_edit_code": (code_count <= 1),
            "can_edit_title": True,
            "can_edit_discount_value": False,
            "can_edit_minimum_requirement": True,
            "can_edit_usage_limit": True,
            "can_edit_once_per_customer": True,
            "can_edit_combinations": True,
            "can_edit_schedule": True,
            "can_edit_eligibility": True,
            "readonly_reason": None,
            "is_automatic": False,
            "mutation_type": "discountCodeFreeShippingUpdate"
        }
    elif typename == "DiscountAutomaticFreeShipping":
        return {
            "editable": True,
            "can_edit_code": False,
            "can_edit_title": True,
            "can_edit_discount_value": False,
            "can_edit_minimum_requirement": True,
            "can_edit_usage_limit": False,
            "can_edit_once_per_customer": False,
            "can_edit_combinations": True,
            "can_edit_schedule": True,
            "can_edit_eligibility": True,
            "readonly_reason": None,
            "is_automatic": True,
            "mutation_type": "discountAutomaticFreeShippingUpdate"
        }
    elif typename in ("DiscountCodeBxgy", "DiscountAutomaticBxgy"):
        return {
            "editable": False,
            "can_edit_code": False,
            "can_edit_title": False,
            "can_edit_discount_value": False,
            "can_edit_minimum_requirement": False,
            "can_edit_usage_limit": False,
            "can_edit_once_per_customer": False,
            "can_edit_combinations": False,
            "can_edit_schedule": False,
            "can_edit_eligibility": False,
            "readonly_reason": "Chương trình Mua X Tặng Y (BXGY) yêu cầu cấu hình điều kiện mua/nhận chuyên biệt, hiện hỗ trợ chế độ xem.",
            "is_automatic": "Automatic" in typename,
            "mutation_type": None
        }
    elif typename in ("DiscountCodeApp", "DiscountAutomaticApp"):
        return {
            "editable": False,
            "can_edit_code": False,
            "can_edit_title": False,
            "can_edit_discount_value": False,
            "can_edit_minimum_requirement": False,
            "can_edit_usage_limit": False,
            "can_edit_once_per_customer": False,
            "can_edit_combinations": False,
            "can_edit_schedule": False,
            "can_edit_eligibility": False,
            "readonly_reason": "Mã này do Ứng dụng/Shopify Function quản lý, không thể chỉnh sửa bằng biểu mẫu chuẩn.",
            "is_automatic": "Automatic" in typename,
            "mutation_type": None
        }
    else:
        return {
            "editable": False,
            "readonly_reason": f"Loại discount chưa hỗ trợ ({typename})",
            "is_automatic": False,
            "mutation_type": None
        }


def normalize_discount_node(node: dict) -> dict:
    """Chuẩn hóa một DiscountNode GraphQL thành Normalized DTO cho Client."""
    discount_id = node.get("id", "")
    discount = node.get("discount") or {}
    typename = discount.get("__typename", "Unknown")

    # 1. Method & Code info
    is_code = typename.startswith("DiscountCode")
    method = "CODE" if is_code else "AUTOMATIC"
    
    primary_code = ""
    code_count = 0
    codes_data = discount.get("codes", {}).get("nodes", [])
    if codes_data:
        primary_code = codes_data[0].get("code", "")
    
    if discount.get("codesCount"):
        code_count = discount["codesCount"].get("count", len(codes_data))
    else:
        code_count = len(codes_data)

    # 2. Status canonical (ACTIVE, EXPIRED, SCHEDULED)
    raw_status = discount.get("status", "ACTIVE")
    if raw_status not in ("ACTIVE", "EXPIRED", "SCHEDULED"):
        raw_status = "ACTIVE"

    # 3. Discount Type & Value
    discount_type = "UNKNOWN"
    discount_type_label = "Chưa rõ"
    value_type = "NONE" # PERCENTAGE, FIXED_AMOUNT, FREE_SHIPPING, OTHER
    value_number = 0.0
    value_formatted = ""
    applies_on_each_item = False

    if "FreeShipping" in typename:
        discount_type = "FREE_SHIPPING"
        discount_type_label = "Miễn phí vận chuyển"
        value_type = "FREE_SHIPPING"
        value_formatted = "Free Shipping"
    elif "Bxgy" in typename:
        discount_type = "BXGY"
        discount_type_label = "Mua X tặng Y"
        value_type = "OTHER"
        value_formatted = "Buy X Get Y"
    elif "App" in typename:
        discount_type = "APP"
        discount_type_label = "Ứng dụng/Function"
        value_type = "OTHER"
        value_formatted = "App Extension"
    else:
        # Basic discounts
        customer_gets = discount.get("customerGets", {})
        val = customer_gets.get("value", {})
        val_type = val.get("__typename")
        if val_type == "DiscountPercentage":
            discount_type = "PERCENTAGE"
            discount_type_label = "Giảm phần trăm"
            value_type = "PERCENTAGE"
            pct = float(val.get("percentage", 0.0))
            value_number = round(pct * 100.0, 4) # e.g. 0.15 -> 15.0%
            value_formatted = f"{int(value_number) if value_number.is_integer() else value_number}%"
        elif val_type == "DiscountAmount":
            discount_type = "FIXED_AMOUNT"
            discount_type_label = "Giảm số tiền cố định"
            value_type = "FIXED_AMOUNT"
            amt_info = val.get("amount", {})
            amt_str = amt_info.get("amount", "0")
            value_number = float(amt_str)
            value_formatted = f"${value_number:,.2f}"
            applies_on_each_item = bool(val.get("appliesOnEachItem", False))

    # 4. Minimum requirements
    min_req_type = "NONE" # NONE, MINIMUM_SUBTOTAL, MINIMUM_QUANTITY
    min_req_value = 0.0
    min_req_label = "Không có điều kiện tối thiểu"
    
    req_obj = discount.get("minimumRequirement")
    if req_obj:
        req_type = req_obj.get("__typename")
        if req_type == "DiscountMinimumSubtotal":
            min_req_type = "MINIMUM_SUBTOTAL"
            subtotal_info = req_obj.get("greaterThanOrEqualToSubtotal", {})
            min_req_value = float(subtotal_info.get("amount", "0"))
            min_req_label = f"Đơn hàng tối thiểu: ${min_req_value:,.2f}"
        elif req_type == "DiscountMinimumQuantity":
            min_req_type = "MINIMUM_QUANTITY"
            min_req_value = float(req_obj.get("greaterThanOrEqualToQuantity", 0))
            min_req_label = f"Số lượng tối thiểu: {int(min_req_value)} món"

    # 5. Combinations (Explicit canonical state, never ambiguous)
    combines_with = discount.get("combinesWith", {})
    order_comb = bool(combines_with.get("orderDiscounts", False))
    prod_comb = bool(combines_with.get("productDiscounts", False))
    ship_comb = bool(combines_with.get("shippingDiscounts", False))
    active_combs = []
    if order_comb: active_combs.append("Order")
    if prod_comb: active_combs.append("Product")
    if ship_comb: active_combs.append("Shipping")
    
    combinations = {
        "order_discounts": order_comb,
        "product_discounts": prod_comb,
        "shipping_discounts": ship_comb,
        "active_list": active_combs,
        "label": " • ".join(active_combs) if active_combs else "Không kết hợp",
        "has_combinations": bool(active_combs)
    }

    # 6. Usage & Limits
    usage_count = int(discount.get("asyncUsageCount") or 0)
    usage_limit = discount.get("usageLimit") # int or None
    applies_once_per_customer = bool(discount.get("appliesOncePerCustomer", False))

    # 7. Schedule
    starts_at = discount.get("startsAt")
    ends_at = discount.get("endsAt")
    updated_at = discount.get("updatedAt")

    # 8. Eligibility (Context-based)
    ctx = discount.get("context") or {}
    ctx_type = ctx.get("__typename")
    if ctx_type == "DiscountCustomerSegments":
        segs = ctx.get("segments", [])
        seg_names = [s.get("name") for s in segs if s.get("name")]
        label = f"Phân khúc: {', '.join(seg_names)}" if seg_names else (f"{len(segs)} phân khúc" if segs else "Phân khúc khách hàng")
        eligibility = {
            "type": "CUSTOMER_SEGMENTS",
            "label": label,
            "segments": segs
        }
    elif ctx_type == "DiscountCustomers":
        raw_cust = ctx.get("customers")
        cust_list = raw_cust if isinstance(raw_cust, list) else (raw_cust.get("nodes", []) if isinstance(raw_cust, dict) else [])
        names = [c.get("displayName") for c in cust_list if isinstance(c, dict) and c.get("displayName")]
        label = f"Khách hàng: {', '.join(names)}" if names else "Khách hàng được chọn"
        eligibility = {
            "type": "CUSTOMERS",
            "label": label,
            "customers": cust_list
        }
    elif ctx_type == "DiscountMarkets":
        mkts = ctx.get("markets", {}).get("nodes", []) if isinstance(ctx.get("markets"), dict) else []
        label = f"{len(mkts)} thị trường" if mkts else "Thị trường được chọn"
        eligibility = {
            "type": "MARKETS",
            "label": label,
            "markets": mkts
        }
    elif ctx_type == "DiscountContextUnknown":
        eligibility = {
            "type": "UNKNOWN",
            "label": f"Ngữ cảnh mở rộng ({ctx.get('contextType', 'Custom')})"
        }
    else:
        eligibility = {
            "type": "ALL",
            "label": "Tất cả khách hàng (All customers)"
        }

    capabilities = resolve_discount_capabilities(typename, discount)

    return {
        "id": discount_id,
        "resource_type": typename,
        "title": discount.get("title", ""),
        "summary": discount.get("summary", ""),
        "method": method,
        "primary_code": primary_code,
        "code_count": code_count,
        "status": raw_status,
        "discount_type": discount_type,
        "discount_type_label": discount_type_label,
        "value_type": value_type,
        "value_number": value_number,
        "value_formatted": value_formatted,
        "applies_on_each_item": applies_on_each_item,
        "minimum_requirement": {
            "type": min_req_type,
            "value": min_req_value,
            "label": min_req_label
        },
        "combinations": combinations,
        "usage_count": usage_count,
        "usage_limit": usage_limit,
        "applies_once_per_customer": applies_once_per_customer,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "updated_at": updated_at,
        "eligibility": eligibility,
        "capabilities": capabilities
    }


def get_discounts(execute_graphql_func, client_info: dict, first: int = 50, after: Optional[str] = None, query: Optional[str] = None) -> dict:
    """Lấy danh sách discount với phân trang con trỏ (cursor pagination)."""
    variables = {
        "first": min(max(first, 1), 100),
        "after": after,
        "query": query
    }
    
    resp = execute_graphql_func(client_info, QUERY_LIST_DISCOUNTS, variables)
    if not resp or "data" not in resp or not resp["data"]:
        errors = resp.get("errors", []) if resp else [{"message": "Empty response from Shopify"}]
        raise DiscountException(f"Lỗi khi tải danh sách discount: {errors}", errors=errors, phase="shopify")
    
    # Graceful handling nếu có partial field errors (như thiếu read_customers)
    if resp.get("errors"):
        logger.warning(f"GraphQL partial field warnings: {resp['errors']}")
    
    discount_nodes = resp["data"].get("discountNodes", {})
    edges = discount_nodes.get("edges", [])
    page_info = discount_nodes.get("pageInfo", {})
    
    items = []
    for edge in edges:
        node = edge.get("node")
        if node and node.get("discount"):
            items.append(normalize_discount_node(node))
            
    return {
        "items": items,
        "page_info": {
            "has_next_page": page_info.get("hasNextPage", False),
            "has_previous_page": page_info.get("hasPreviousPage", False),
            "start_cursor": page_info.get("startCursor"),
            "end_cursor": page_info.get("endCursor")
        },
        "total_fetched": len(items)
    }


def get_discount_detail(execute_graphql_func, client_info: dict, discount_node_id: str) -> dict:
    """Lấy chi tiết một discount cụ thể theo ID."""
    if not discount_node_id or not discount_node_id.startswith("gid://shopify/"):
        raise DiscountValidationException("ID discount không hợp lệ", field="id")
        
    variables = {"id": discount_node_id}
    resp = execute_graphql_func(client_info, QUERY_DISCOUNT_DETAIL, variables)
    
    if not resp or "data" not in resp or not resp["data"]:
        errors = resp.get("errors", []) if resp else [{"message": "Empty response from Shopify"}]
        raise DiscountException(f"Lỗi khi đọc chi tiết discount: {errors}", errors=errors, phase="shopify")
    
    if resp.get("errors"):
        logger.warning(f"GraphQL partial field warnings in detail: {resp['errors']}")
        
    node = resp["data"].get("discountNode")
    if not node or not node.get("discount"):
        raise DiscountException("Không tìm thấy discount với ID đã cung cấp", code="NOT_FOUND", phase="shopify")
        
    return normalize_discount_node(node)


def update_discount(
    execute_graphql_func, 
    client_info: dict, 
    discount_node_id: str, 
    loaded_updated_at: str, 
    changes: dict
) -> dict:
    """
    Cập nhật discount dạng Patch-style với optimistic concurrency protection.
    """
    if not discount_node_id or not discount_node_id.startswith("gid://shopify/"):
        raise DiscountValidationException("ID discount không hợp lệ", field="id")
        
    # Bước 1: Fetch fresh canonical detail từ Shopify
    fresh_detail = get_discount_detail(execute_graphql_func, client_info, discount_node_id)
    real_typename = fresh_detail["resource_type"]
    fresh_updated_at = fresh_detail.get("updated_at")
    
    # Bước 2: Concurrency stale check
    if loaded_updated_at and fresh_updated_at and loaded_updated_at != fresh_updated_at:
        raise DiscountStaleException(
            f"Dữ liệu discount đã thay đổi trên hệ thống (Lần lưu: {fresh_updated_at}, Dữ liệu bạn xem: {loaded_updated_at}). "
            f"Vui lòng tải lại trang để đảm bảo không ghi đè dữ liệu mới nhất."
        )

    # Bước 3: Kiểm tra capabilities của subtype
    capabilities = fresh_detail.get("capabilities", {})
    if not capabilities.get("editable"):
        reason = capabilities.get("readonly_reason") or "Loại discount này không hỗ trợ chỉnh sửa qua biểu mẫu."
        raise DiscountUnsupportedException(reason)

    # Bước 4: No-op check (Nếu không có thay đổi nào, trả về fresh_detail mà không gọi mutation)
    if not changes:
        return {
            "success": True,
            "message": "Không có thay đổi nào cần cập nhật",
            "discount": fresh_detail,
            "no_op": True
        }

    # Bước 5: Validation
    if "title" in changes and not str(changes["title"]).strip():
        raise DiscountValidationException("Tiêu đề discount không được để trống", field="title")

    if "code" in changes and capabilities.get("can_edit_code"):
        if not str(changes["code"]).strip():
            raise DiscountValidationException("Mã discount (Code) không được để trống", field="code")

    # Bước 6: Build Patch Input tùy subtype
    if real_typename == "DiscountCodeBasic":
        patch_input = {}
        
        if "title" in changes:
            patch_input["title"] = str(changes["title"]).strip()
        if "code" in changes and capabilities.get("can_edit_code"):
            patch_input["code"] = str(changes["code"]).strip()
            
        # Giá trị giảm giá (Discount value)
        if "discount_value" in changes and capabilities.get("can_edit_discount_value"):
            dv = changes["discount_value"]
            v_type = dv.get("type") # "PERCENTAGE" hoặc "FIXED_AMOUNT"
            v_amount = dv.get("amount")
            
            if v_type == "PERCENTAGE":
                val_dec = Decimal(str(v_amount))
                if val_dec <= 0 or val_dec > 100:
                    raise DiscountValidationException("Phần trăm giảm giá phải nằm trong khoảng từ 0.01 đến 100", field="percentage")
                # Serialize sang 0.0 - 1.0 (float)
                patch_input["customerGets"] = {
                    "value": {
                        "percentage": float(val_dec / Decimal(100))
                    }
                }
            elif v_type == "FIXED_AMOUNT":
                val_dec = Decimal(str(v_amount))
                if val_dec <= 0:
                    raise DiscountValidationException("Số tiền giảm giá phải lớn hơn 0", field="amount")
                # Giữ nguyên appliesOnEachItem của canonical
                orig_applies = fresh_detail.get("applies_on_each_item", False)
                patch_input["customerGets"] = {
                    "value": {
                        "discountAmount": {
                            "amount": str(val_dec),
                            "appliesOnEachItem": orig_applies
                        }
                    }
                }

        # Điều kiện tối thiểu (Minimum requirements)
        if "minimum_requirement" in changes:
            mr = changes["minimum_requirement"]
            mr_type = mr.get("type", "NONE")
            if mr_type == "NONE":
                patch_input["minimumRequirement"] = None
            elif mr_type == "MINIMUM_SUBTOTAL":
                subtotal_dec = Decimal(str(mr.get("amount", 0)))
                if subtotal_dec <= 0:
                    raise DiscountValidationException("Số tiền đơn hàng tối thiểu phải lớn hơn 0", field="minimum_subtotal")
                patch_input["minimumRequirement"] = {
                    "subtotal": {
                        "greaterThanOrEqualToSubtotal": str(subtotal_dec)
                    }
                }
            elif mr_type == "MINIMUM_QUANTITY":
                qty = int(mr.get("quantity", 0))
                if qty < 1:
                    raise DiscountValidationException("Số lượng sản phẩm tối thiểu phải lớn hơn hoặc bằng 1", field="minimum_quantity")
                patch_input["minimumRequirement"] = {
                    "quantity": {
                        "greaterThanOrEqualToQuantity": qty
                    }
                }

        # Giới hạn sử dụng (Usage limit)
        if "usage_limit" in changes:
            ul = changes["usage_limit"]
            if ul is None or ul == "":
                patch_input["usageLimit"] = None
            else:
                ul_int = int(ul)
                if ul_int < 1:
                    raise DiscountValidationException("Giới hạn sử dụng phải lớn hơn hoặc bằng 1", field="usage_limit")
                patch_input["usageLimit"] = ul_int

        if "applies_once_per_customer" in changes:
            patch_input["appliesOncePerCustomer"] = bool(changes["applies_once_per_customer"])

        # Combinations
        if "combinations" in changes:
            comb = changes["combinations"]
            patch_input["combinesWith"] = {
                "orderDiscounts": bool(comb.get("order_discounts", False)),
                "productDiscounts": bool(comb.get("product_discounts", False)),
                "shippingDiscounts": bool(comb.get("shipping_discounts", False))
            }

        # Schedule
        if "schedule" in changes:
            sch = changes["schedule"]
            if "starts_at" in sch and sch["starts_at"]:
                patch_input["startsAt"] = sch["starts_at"]
            if "ends_at" in sch:
                patch_input["endsAt"] = sch["ends_at"] if sch["ends_at"] else None

        # Eligibility (Context) - Chỉ đưa vào patch khi user chủ động đổi eligibility
        if "eligibility" in changes and capabilities.get("can_edit_eligibility"):
            el = changes["eligibility"]
            el_type = el.get("type", "ALL")
            if el_type == "ALL":
                patch_input["context"] = {"all": "ALL"}
            elif el_type == "CUSTOMER_SEGMENTS":
                add_segs = el.get("add_segments", [])
                rem_segs = el.get("remove_segments", [])
                patch_input["context"] = {
                    "customerSegments": {
                        "add": add_segs,
                        "remove": rem_segs
                    }
                }

        # Execute mutation
        mutation = MUTATION_CODE_BASIC_UPDATE
        variables = {
            "id": discount_node_id,
            "basicCodeDiscount": patch_input
        }
        res_key = "discountCodeBasicUpdate"

    elif real_typename == "DiscountAutomaticBasic":
        patch_input = {}
        if "title" in changes:
            patch_input["title"] = str(changes["title"]).strip()

        if "discount_value" in changes and capabilities.get("can_edit_discount_value"):
            dv = changes["discount_value"]
            v_type = dv.get("type")
            v_amount = dv.get("amount")
            if v_type == "PERCENTAGE":
                val_dec = Decimal(str(v_amount))
                if val_dec <= 0 or val_dec > 100:
                    raise DiscountValidationException("Phần trăm giảm giá phải từ 0.01 đến 100", field="percentage")
                patch_input["customerGets"] = {
                    "value": {
                        "percentage": float(val_dec / Decimal(100))
                    }
                }
            elif v_type == "FIXED_AMOUNT":
                val_dec = Decimal(str(v_amount))
                if val_dec <= 0:
                    raise DiscountValidationException("Số tiền giảm giá phải lớn hơn 0", field="amount")
                orig_applies = fresh_detail.get("applies_on_each_item", False)
                patch_input["customerGets"] = {
                    "value": {
                        "discountAmount": {
                            "amount": str(val_dec),
                            "appliesOnEachItem": orig_applies
                        }
                    }
                }

        if "minimum_requirement" in changes:
            mr = changes["minimum_requirement"]
            mr_type = mr.get("type", "NONE")
            if mr_type == "NONE":
                patch_input["minimumRequirement"] = None
            elif mr_type == "MINIMUM_SUBTOTAL":
                subtotal_dec = Decimal(str(mr.get("amount", 0)))
                patch_input["minimumRequirement"] = {
                    "subtotal": {
                        "greaterThanOrEqualToSubtotal": str(subtotal_dec)
                    }
                }
            elif mr_type == "MINIMUM_QUANTITY":
                qty = int(mr.get("quantity", 0))
                patch_input["minimumRequirement"] = {
                    "quantity": {
                        "greaterThanOrEqualToQuantity": qty
                    }
                }

        if "combinations" in changes:
            comb = changes["combinations"]
            patch_input["combinesWith"] = {
                "orderDiscounts": bool(comb.get("order_discounts", False)),
                "productDiscounts": bool(comb.get("product_discounts", False)),
                "shippingDiscounts": bool(comb.get("shipping_discounts", False))
            }

        if "schedule" in changes:
            sch = changes["schedule"]
            if "starts_at" in sch and sch["starts_at"]:
                patch_input["startsAt"] = sch["starts_at"]
            if "ends_at" in sch:
                patch_input["endsAt"] = sch["ends_at"] if sch["ends_at"] else None

        if "eligibility" in changes and capabilities.get("can_edit_eligibility"):
            el = changes["eligibility"]
            el_type = el.get("type", "ALL")
            if el_type == "ALL":
                patch_input["context"] = {"all": "ALL"}
            elif el_type == "CUSTOMER_SEGMENTS":
                patch_input["context"] = {
                    "customerSegments": {
                        "add": el.get("add_segments", []),
                        "remove": el.get("remove_segments", [])
                    }
                }

        mutation = MUTATION_AUTOMATIC_BASIC_UPDATE
        variables = {
            "id": discount_node_id,
            "automaticBasicDiscount": patch_input
        }
        res_key = "discountAutomaticBasicUpdate"

    elif real_typename == "DiscountCodeFreeShipping":
        patch_input = {}
        if "title" in changes:
            patch_input["title"] = str(changes["title"]).strip()
        if "code" in changes and capabilities.get("can_edit_code"):
            patch_input["code"] = str(changes["code"]).strip()
        if "usage_limit" in changes:
            ul = changes["usage_limit"]
            patch_input["usageLimit"] = int(ul) if ul else None
        if "applies_once_per_customer" in changes:
            patch_input["appliesOncePerCustomer"] = bool(changes["applies_once_per_customer"])
        if "combinations" in changes:
            comb = changes["combinations"]
            patch_input["combinesWith"] = {
                "orderDiscounts": bool(comb.get("order_discounts", False)),
                "productDiscounts": bool(comb.get("product_discounts", False)),
                "shippingDiscounts": bool(comb.get("shipping_discounts", False))
            }
        if "minimum_requirement" in changes:
            mr = changes["minimum_requirement"]
            mr_type = mr.get("type", "NONE")
            if mr_type == "NONE":
                patch_input["minimumRequirement"] = None
            elif mr_type == "MINIMUM_SUBTOTAL":
                subtotal_dec = Decimal(str(mr.get("amount", 0)))
                patch_input["minimumRequirement"] = {
                    "subtotal": {
                        "greaterThanOrEqualToSubtotal": str(subtotal_dec)
                    }
                }
            elif mr_type == "MINIMUM_QUANTITY":
                qty = int(mr.get("quantity", 0))
                patch_input["minimumRequirement"] = {
                    "quantity": {
                        "greaterThanOrEqualToQuantity": qty
                    }
                }
        if "schedule" in changes:
            sch = changes["schedule"]
            if "starts_at" in sch and sch["starts_at"]:
                patch_input["startsAt"] = sch["starts_at"]
            if "ends_at" in sch:
                patch_input["endsAt"] = sch["ends_at"] if sch["ends_at"] else None

        if "eligibility" in changes and capabilities.get("can_edit_eligibility"):
            el = changes["eligibility"]
            el_type = el.get("type", "ALL")
            if el_type == "ALL":
                patch_input["context"] = {"all": "ALL"}
            elif el_type == "CUSTOMER_SEGMENTS":
                patch_input["context"] = {
                    "customerSegments": {
                        "add": el.get("add_segments", []),
                        "remove": el.get("remove_segments", [])
                    }
                }

        mutation = MUTATION_CODE_FREE_SHIPPING_UPDATE
        variables = {
            "id": discount_node_id,
            "freeShippingCodeDiscount": patch_input
        }
        res_key = "discountCodeFreeShippingUpdate"

    elif real_typename == "DiscountAutomaticFreeShipping":
        patch_input = {}
        if "title" in changes:
            patch_input["title"] = str(changes["title"]).strip()
        if "combinations" in changes:
            comb = changes["combinations"]
            patch_input["combinesWith"] = {
                "orderDiscounts": bool(comb.get("order_discounts", False)),
                "productDiscounts": bool(comb.get("product_discounts", False)),
                "shippingDiscounts": bool(comb.get("shipping_discounts", False))
            }
        if "minimum_requirement" in changes:
            mr = changes["minimum_requirement"]
            mr_type = mr.get("type", "NONE")
            if mr_type == "NONE":
                patch_input["minimumRequirement"] = None
            elif mr_type == "MINIMUM_SUBTOTAL":
                subtotal_dec = Decimal(str(mr.get("amount", 0)))
                patch_input["minimumRequirement"] = {
                    "subtotal": {
                        "greaterThanOrEqualToSubtotal": str(subtotal_dec)
                    }
                }
            elif mr_type == "MINIMUM_QUANTITY":
                qty = int(mr.get("quantity", 0))
                patch_input["minimumRequirement"] = {
                    "quantity": {
                        "greaterThanOrEqualToQuantity": qty
                    }
                }
        if "schedule" in changes:
            sch = changes["schedule"]
            if "starts_at" in sch and sch["starts_at"]:
                patch_input["startsAt"] = sch["starts_at"]
            if "ends_at" in sch:
                patch_input["endsAt"] = sch["ends_at"] if sch["ends_at"] else None

        if "eligibility" in changes and capabilities.get("can_edit_eligibility"):
            el = changes["eligibility"]
            el_type = el.get("type", "ALL")
            if el_type == "ALL":
                patch_input["context"] = {"all": "ALL"}
            elif el_type == "CUSTOMER_SEGMENTS":
                patch_input["context"] = {
                    "customerSegments": {
                        "add": el.get("add_segments", []),
                        "remove": el.get("remove_segments", [])
                    }
                }

        mutation = MUTATION_AUTOMATIC_FREE_SHIPPING_UPDATE
        variables = {
            "id": discount_node_id,
            "freeShippingAutomaticDiscount": patch_input
        }
        res_key = "discountAutomaticFreeShippingUpdate"

    else:
        raise DiscountUnsupportedException(f"Chưa hỗ trợ mutation cho loại discount: {real_typename}")

    # Gửi mutation tới Shopify
    resp = execute_graphql_func(client_info, mutation, variables)
    if not resp or "data" not in resp or not resp["data"]:
        errors = resp.get("errors", []) if resp else [{"message": "Empty response from Shopify"}]
        raise DiscountException(f"Lỗi GraphQL khi cập nhật discount: {errors}", errors=errors, phase="shopify")

    mutation_payload = resp["data"].get(res_key, {})
    user_errors = mutation_payload.get("userErrors", [])
    if user_errors:
        err_messages = "; ".join([e.get("message", "") for e in user_errors])
        raise DiscountException(
            f"Shopify từ chối lưu thay đổi: {err_messages}",
            code="SHOPIFY_USER_ERRORS",
            phase="shopify",
            errors=user_errors
        )

    # Bước 7: Read-back canonical discount sau khi save
    updated_detail = get_discount_detail(execute_graphql_func, client_info, discount_node_id)
    return {
        "success": True,
        "message": "Cập nhật discount thành công",
        "discount": updated_detail
    }


def toggle_discount_status(
    execute_graphql_func,
    client_info: dict,
    discount_node_id: str,
    action: str
) -> dict:
    """Kích hoạt hoặc vô hiệu hóa một discount (Code hoặc Automatic).
    
    Args:
        execute_graphql_func: Hàm gửi GraphQL request.
        client_info: Thông tin kết nối shopify client.
        discount_node_id: ID GraphQL của discount (gid://shopify/DiscountCodeNode/... hoặc gid://shopify/DiscountAutomaticNode/...)
        action: 'activate' hoặc 'deactivate'
    """
    if not discount_node_id or not discount_node_id.startswith("gid://shopify/"):
        raise DiscountValidationException("ID discount không hợp lệ", field="id")
        
    action_norm = str(action).strip().lower()
    if action_norm not in ("activate", "deactivate"):
        raise DiscountValidationException("Hành động không hợp lệ, phải là 'activate' hoặc 'deactivate'", field="action")

    # Xác định loại node là Code hay Automatic
    is_code = "DiscountCodeNode" in discount_node_id
    is_auto = "DiscountAutomaticNode" in discount_node_id

    if not is_code and not is_auto:
        # Preflight check để lấy typename
        detail = get_discount_detail(execute_graphql_func, client_info, discount_node_id)
        is_code = (detail.get("method") == "CODE")

    if is_code:
        mutation = MUTATION_CODE_ACTIVATE if action_norm == "activate" else MUTATION_CODE_DEACTIVATE
        res_key = "discountCodeActivate" if action_norm == "activate" else "discountCodeDeactivate"
        node_key = "codeDiscountNode"
        sub_key = "codeDiscount"
    else:
        mutation = MUTATION_AUTOMATIC_ACTIVATE if action_norm == "activate" else MUTATION_AUTOMATIC_DEACTIVATE
        res_key = "discountAutomaticActivate" if action_norm == "activate" else "discountAutomaticDeactivate"
        node_key = "automaticDiscountNode"
        sub_key = "automaticDiscount"

    variables = {"id": discount_node_id}
    resp = execute_graphql_func(client_info, mutation, variables)

    if not resp or "data" not in resp or not resp["data"]:
        errors = resp.get("errors", []) if resp else [{"message": "Empty response from Shopify"}]
        raise DiscountException(f"Lỗi GraphQL khi đổi trạng thái discount: {errors}", errors=errors, phase="shopify")

    mutation_payload = resp["data"].get(res_key, {})
    user_errors = mutation_payload.get("userErrors", [])
    if user_errors:
        err_messages = "; ".join([e.get("message", "") for e in user_errors])
        raise DiscountException(
            f"Shopify từ chối cập nhật trạng thái: {err_messages}",
            code="SHOPIFY_USER_ERRORS",
            phase="shopify",
            errors=user_errors
        )

    # Lấy status mới trả về
    node_payload = mutation_payload.get(node_key) or {}
    sub_payload = node_payload.get(sub_key) or {}
    new_status = sub_payload.get("status")

    if not new_status:
        new_status = "ACTIVE" if action_norm == "activate" else "EXPIRED"

    action_label = "kích hoạt" if action_norm == "activate" else "vô hiệu hóa"
    return {
        "success": True,
        "message": f"Đã {action_label} discount thành công",
        "new_status": new_status,
        "discount_node_id": discount_node_id,
        "action": action_norm
    }
