---
name: shopify-clean-variant-marketing-terms
description: Quét catalog Shopify, phát hiện và chuẩn hóa an toàn các từ ngữ marketing (Best Selling, Recommended, Best Choice...) khỏi option biến thể thông qua Admin GraphQL API (productOptionUpdate).
---

# Shopify Clean Variant Marketing Terms

## Mục tiêu

Skill này dùng để chuẩn hóa dữ liệu biến thể sản phẩm trên Shopify bằng cách:
1. Kết nối an toàn vào Shopify Admin API thông qua token trong `admin/.env` hoặc `admin/access-token.md`.
2. Quét toàn bộ catalog sản phẩm bằng GraphQL phân trang (Cursor Pagination).
3. Phát hiện tất cả các option values của biến thể bị gài từ ngữ marketing, badge khuyến mại, upsell suffixes (ví dụ: `- Best Selling`, `- Recommended`, `- Best Choice`).
4. Kiểm tra va chạm / xung đột (Collision Check) trước khi ghi để đảm bảo không sinh ra giá trị trùng lặp trong cùng một sản phẩm.
5. Cập nhật an toàn bằng GraphQL mutation `productOptionUpdate` (bảo toàn nguyên vẹn ID biến thể, tồn kho, giá bán, hình ảnh và SKU).
6. Tự động xác minh lại catalog (đảm bảo 0 sản phẩm sót lỗi) và dọn dẹp môi trường làm việc.

---

## 1. Nguồn Token & Chuẩn bị môi trường

### Đọc cấu hình
- File cấu hình: `admin/.env`
- Các biến môi trường:
  - `SHOPIFY_SHOP`: Domain của store (ví dụ: `wrydeco.myshopify.com`).
  - `SHOPIFY_ADMIN_TOKEN`: Token Admin API hiện tại (`shpat_...`).
  - `SHOPIFY_API_VERSION`: Phiên bản API ổn định (ưu tiên `2024-04`, `2024-07` trở lên).
  - `SHOPIFY_CLIENT_ID` & `SHOPIFY_CLIENT_SECRET`: Dùng để tự refresh token nếu token cũ hết hạn.

### Xác thực token
Chạy script kiểm tra token:
```bash
python admin/get_access_token.py
```
Nếu token hợp lệ, lấy token và tiếp tục. Nếu hết hạn, script sẽ tự động cấp token mới từ Client Credentials.

---

## 2. Nguyên tắc an toàn cốt lõi (Guardrails)

1. **Zero Collision (Không tạo biến thể trùng lặp):**
   - Trước khi cập nhật một option value từ `X - Suffix` thành `X`, BẮT BUỘC kiểm tra xem sản phẩm đó đã có sẵn giá trị `X` trong cùng option đó hay chưa.
   - Nếu đã tồn tại `X`, tuyệt đối không thực thi update tự động vì sẽ gây lỗi duplicate option value trong Shopify. Phải dừng lại và báo cáo để có phương án gộp biến thể (merge variants).

2. **Sử dụng đúng mutation `productOptionUpdate`:**
   - Cập nhật ở cấp độ Option Value (`OptionValueUpdateInput`).
   - Ưu điểm vượt trội so với cập nhật thủ công từng variant:
     - Shopify tự động cập nhật tên biến thể (`variant.title`) trên toàn bộ các biến thể liên quan.
     - Shopify tự động cập nhật thuộc tính lựa chọn (`selectedOptions`).
     - Bảo toàn 100% `variant.id`, giá (`price`), tồn kho (`inventoryQuantity`), SKU, hình ảnh đính kèm và metafields.

3. **Kiểm soát Rate Limit & Throttle:**
   - Dùng GraphQL cursor pagination: `first: 100, after: $cursor`.
   - Giãn cách nghỉ tối thiểu `0.2s - 0.4s` giữa các mutation cập nhật để không làm cạn kiệt leaky bucket của Shopify API.

4. **Dọn dẹp môi trường (Workspace Hygiene):**
   - Không commit các file script/data tạm phát sinh trong quá trình chạy.
   - Chạy `python admin/clean.py` ngay sau khi hoàn thành.

---

## 3. Quy trình thực hiện chuẩn 5 bước

### Bước 1: Quét danh mục sản phẩm qua GraphQL

Truy vấn toàn bộ sản phẩm cùng các `options` và `optionValues`:

```graphql
query getProducts($cursor: String) {
  products(first: 100, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      title
      handle
      status
      options {
        id
        name
        position
        values
        optionValues {
          id
          name
        }
      }
    }
  }
}
```

### Bước 2: Nhận diện từ ngữ marketing & lập danh sách làm sạch

Danh sách các regex pattern thường gặp cần loại bỏ:
```python
PATTERNS = [
    r"\s*-\s*Best\s*Selling\b",
    r"\s*-\s*Recommended\b",
    r"\s*-\s*Best\s*Choice\b",
    r"\s*-\s*Top\s*Rated\b",
    r"\s*-\s*Most\s*Popular\b",
]
```

Với mỗi option value, áp dụng regex để tính toán giá trị làm sạch:
```python
cleaned_name = val_name
for pat in PATTERNS:
    cleaned_name = re.sub(pat, "", cleaned_name, flags=re.IGNORECASE).strip()
```

### Bước 3: Phân tích va chạm (Conflict / Collision Check)

Trước khi gửi bất kỳ mutation nào, chạy kiểm tra:
```python
conflicts = []
for p in matched_products:
    for opt in p["options"]:
        current_values = opt["values"]
        for ov in opt["optionValues"]:
            # nếu cleaned_name != ov["name"] và cleaned_name đã tồn tại trong current_values
            if cleaned_name != ov["name"] and cleaned_name in current_values:
                conflicts.append((p["title"], opt["name"], ov["name"], cleaned_name))

if conflicts:
    raise RuntimeError(f"Phát hiện {len(conflicts)} xung đột trùng lặp! Dừng xử lý để bảo vệ dữ liệu.")
```

### Bước 4: Thực thi cập nhật hàng loạt (Batch Mutation)

Sử dụng mutation `productOptionUpdate`:

```graphql
mutation updateOption(
  $productId: ID!
  $option: OptionUpdateInput!
  $optionValuesToUpdate: [OptionValueUpdateInput!]
) {
  productOptionUpdate(
    productId: $productId
    option: $option
    optionValuesToUpdate: $optionValuesToUpdate
  ) {
    userErrors {
      field
      message
      code
    }
    product {
      id
      title
    }
  }
}
```

Payload mẫu cho biến số:
```json
{
  "productId": "gid://shopify/Product/10344740683833",
  "option": {
    "id": "gid://shopify/ProductOption/13280865386553"
  },
  "optionValuesToUpdate": [
    {
      "id": "gid://shopify/ProductOptionValue/7535378497593",
      "name": "24\"W x 28\"H x 14\"D"
    }
  ]
}
```

### Bước 5: Xác minh kết quả & Dọn dẹp

1. **Xác minh (Verification):**
   - Quét lại toàn bộ sản phẩm bằng GraphQL query tương tự Bước 1.
   - Kiểm tra `option.values`, `variant.title`, `variant.selectedOptions`.
   - Kết quả bắt buộc: `0` sản phẩm còn chứa các từ ngữ marketing mục tiêu.

2. **Dọn dẹp (Cleanup):**
   - Chạy lệnh dọn dẹp:
     ```bash
     python admin/clean.py
     ```
   - Đảm bảo thư mục `admin/` chỉ còn giữ lại các file tiêu chuẩn (`.env`, `access-token.md`, `clean.py`, `get_access_token.py`...).

---

## 4. Báo cáo kết quả cuối cùng

Báo cáo cho người dùng cần tuân theo định dạng rõ ràng:
1. **Tổng quan:** Tổng số sản phẩm đã quét, tổng số sản phẩm đã cập nhật thành công (tỷ lệ 100%, 0 lỗi).
2. **Bảng đối chiếu:** Liệt kê các giá trị trước và sau khi làm sạch cùng số lượng sản phẩm áp dụng.
3. **Trạng thái hệ thống:** Xác nhận không còn xung đột, các biến thể hiển thị sạch trên storefront và thư mục admin đã được dọn sạch.
