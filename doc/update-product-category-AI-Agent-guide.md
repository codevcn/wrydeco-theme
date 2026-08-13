# Hướng dẫn dành cho AI Agent: Cập nhật Product Category (Standard Product Taxonomy) trên Shopify

> **LƯU Ý:** Cập nhật "Product Category" ở đây nghĩa là thiết lập danh mục sản phẩm chuẩn (**Standard Product Taxonomy**) của Shopify, chứ KHÔNG phải là trường **Product Type** (loại sản phẩm tùy chỉnh). Hai khái niệm này hoàn toàn khác nhau.

**Mục đích:** Tài liệu này cung cấp các bước tiêu chuẩn để một AI Agent có thể gán danh mục sản phẩm chuẩn (Standard Product Taxonomy) cho các sản phẩm trên Shopify store một cách chính xác.

**LƯU Ý QUAN TRỌNG NHẤT:**

- **KHÔNG** sử dụng REST API (như việc update trường `product_type` hay `category`) để cập nhật Standard Product Category vì REST API có thể cập nhật không chính xác vào taxonomy mới của Shopify.
- **BẮT BUỘC** phải sử dụng GraphQL Admin API của Shopify để thực hiện truy vấn và cập nhật `category`.

---

## Bước 1: Chuẩn bị thông tin xác thực (Credentials)

- Thông tin xác thực (Shop, Access Token, API Version) luôn được cấu hình và lưu tại file `admin/.env` trong project.
- Cần đọc file `admin/.env` trước tiên. Nếu access token bị hết hạn (nhận mã lỗi `401`), hãy tham khảo file `doc/alias/access-token.md` (hoặc chạy script `admin/get_access_token.py` để tự động xin cấp token mới) sau đó cập nhật lại file `.env`.

---

## Bước 2: Tìm ID của Taxonomy Category phù hợp

Trước khi cập nhật category cho sản phẩm, AI Agent cần tìm chính xác `TaxonomyCategory ID` (ví dụ: `gid://shopify/TaxonomyCategory/fr-19-1`) phù hợp với nội dung/mô tả của sản phẩm.

Sử dụng GraphQL query sau để tìm kiếm taxonomy nodes theo từ khóa:

```graphql
query {
  taxonomy {
    categories(search: "TỪ_KHÓA_TÌM_KIẾM", first: 5) {
      edges {
        node {
          id
          name
          fullName
        }
      }
    }
  }
}
```

_Ví dụ:_ Nếu sản phẩm là kệ/giá sách bằng gỗ (bookshelf), AI Agent sẽ truyền vào `search: "bookcases"`. Kết quả trả về sẽ có node ID `gid://shopify/TaxonomyCategory/fr-19-1` tương ứng với chuỗi phân loại chuẩn là `Furniture > Shelving > Bookcases & Standing Shelves`.

---

## Bước 3: Gán Category cho Sản Phẩm thông qua Mutation `productUpdate`

Sau khi có được `TaxonomyCategory ID` hợp lý và danh sách các `Product ID` (ví dụ: `8376402083897`), AI Agent thực hiện GraphQL mutation `productUpdate`.

_Lưu ý:_ Bắt buộc định dạng tham số ID theo dạng chuỗi Global ID của Shopify:

- Product ID: `gid://shopify/Product/<id>`

**Cấu trúc Mutation:**

```graphql
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      category {
        name
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

**Variables `input` truyền vào:**

```json
{
  "input": {
    "id": "gid://shopify/Product/8376402083897",
    "category": "gid://shopify/TaxonomyCategory/fr-19-1"
  }
}
```

---

## Bước 4: Viết và chạy Script Python (Best Practice khi chạy hàng loạt)

Để đảm bảo sự ổn định và nhanh chóng khi cần cập nhật hàng loạt sản phẩm, AI Agent nên thiết lập một script Python nhỏ bằng thư viện `requests` thay vì sử dụng bash cURL.

**Nguyên tắc viết Script:**

1. Load credentials trực tiếp từ `.env`.
2. Setup headers mặc định: `{"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}`.
3. Gửi request POST tới endpoint: `https://{SHOP}/admin/api/{API_VERSION}/graphql.json`.
4. **Tránh bị Timeout / Rate limit:** Thêm cờ `timeout=10` cho `requests.post()` và đặt lệnh `time.sleep(0.5)` ở cuối mỗi vòng lặp nếu xử lý danh sách dài.
5. In ra kết quả (Success/Error) chi tiết cho từng sản phẩm và nhớ dùng `sys.stdout.flush()` (trong module `sys`) để luồng (log) xuất trực tiếp ra giao diện agent theo thời gian thực mà không bị kẹt buffer (đặc biệt quan trọng trên môi trường Windows).
