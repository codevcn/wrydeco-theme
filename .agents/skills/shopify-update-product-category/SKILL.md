---
name: shopify-update-product-category
description: Quy trình chuẩn hóa và cập nhật danh mục sản phẩm chuẩn (Shopify Standard Product Taxonomy) qua GraphQL Admin API (productUpdate). Bắt buộc phân tích dữ liệu thực tế của sản phẩm (title, handle, description, hình thái) để chọn category chính xác nhất, tuyệt đối không gán tùy tiện.
---

# Shopify Update Product Category (Standard Product Taxonomy)

## Mục tiêu

Skill này dùng để chuẩn hóa và gán danh mục sản phẩm chuẩn (**Shopify Standard Product Taxonomy**) cho các sản phẩm trên Shopify store:
1. Kết nối an toàn vào Shopify Admin API thông qua token trong `admin/.env` (tự động refresh bằng `admin/get_access_token.py` nếu hết hạn).
2. Lấy danh sách sản phẩm cần cập nhật bằng GraphQL Admin API.
3. **Phân tích kỹ lưỡng dữ liệu thực tế của sản phẩm** (`title`, `handle`, `descriptionHtml`, `tags`, công năng vật lý) để đối chiếu và tìm danh mục chính xác, tuyệt đối không phỏng đoán hay gán tùy tiện.
4. Tra cứu cây phân cấp Shopify Taxonomy bằng GraphQL (`taxonomy.categories`) để tìm ra leaf node (nhánh con sâu và đặc thù nhất).
5. Thực thi cập nhật an toàn bằng GraphQL mutation `productUpdate` (kèm rate-limit sleep và timeout).
6. Tự động kiểm tra xác minh lại (đảm bảo 100% sản phẩm có category hợp lệ, 0 lỗi) và dọn dẹp môi trường làm việc.

---

## 1. Nguyên tắc cốt lõi & Ràng buộc an toàn (Critical Guardrails)

> [!IMPORTANT]
> **1. BẮT BUỘC DỰA VÀO DỮ LIỆU SẢN PHẨM — TUYỆT ĐỐI KHÔNG GÁN TÙY TIỆN**
> - Phải đọc và phân tích toàn diện: **Title**, **Handle**, **Description**, **Tags** và hình thái/công năng thực tế của từng sản phẩm.
> - **Cảnh giác với `productType` cũ/thô:** Không bao giờ tin tưởng mù quáng vào trường `productType` vì dữ liệu từ crawler/scraper thường bị gán nhãn nhầm (ví dụ: bàn phụ `Accent Table` bị ghi nhầm là `floating-shelves`, hoặc kệ tường `Wall Shelf` bị ghi nhầm là `end-table`).
> - Phải chọn **Leaf Node** sâu nhất và chuyên biệt nhất trong Shopify Taxonomy (ví dụ: sản phẩm tủ đĩa than phải vào `Turntable Stands` chứ không dừng ở `Media Storage Cabinets & Racks` hay `Furniture`).

> [!WARNING]
> **2. CẤM SỬ DỤNG REST API ĐỂ CẬP NHẬT TAXONOMY CATEGORY**
> - **KHÔNG** sử dụng REST API (như gửi `PUT` cập nhật trường `category` hay `product_type` trên REST) vì REST API có thể map sai hoặc không tương thích với Shopify Standard Product Taxonomy mới.
> - **BẮT BUỘC** sử dụng **Shopify GraphQL Admin API** với Global ID dạng `gid://shopify/TaxonomyCategory/<category_id>`.

3. **Đồng bộ với Catalog hiện tại của Store:**
   - Trước khi gán cho nhóm sản phẩm mới, nên kiểm tra nhanh các sản phẩm tương tự đang có trên store để đảm bảo tính nhất quán của catalog.

4. **Kiểm soát Rate Limit & Timeout:**
   - Luôn thêm `timeout=15` cho các HTTP request.
   - Thêm `time.sleep(0.5)` giữa các vòng lặp mutation khi xử lý hàng loạt.
   - Sử dụng `sys.stdout.flush()` trên Windows để luồng log hiển thị trực tiếp theo thời gian thực.

5. **Dọn dẹp môi trường (Workspace Hygiene):**
   - Không commit các file script tạm, file JSON nháp trong thư mục `admin/`.
   - Giữ lại hoặc làm sạch theo quy định trong `admin/clean.py`.

---

## 2. Chuẩn bị thông tin xác thực (Credentials)

1. Đọc credentials từ file `admin/.env`:
   - `SHOPIFY_SHOP`: Domain store (ví dụ: `wrydeco.myshopify.com`).
   - `SHOPIFY_ADMIN_TOKEN`: Token Admin API (`shpat_...`).
   - `SHOPIFY_API_VERSION`: Phiên bản API ổn định (ví dụ: `2024-07`, `2026-07`).
2. Nếu token bị hết hạn (nhận mã lỗi `401`), chạy script cấp lại token:
   ```bash
   python admin/get_access_token.py
   ```

---

## 3. Quy trình thực hiện chuẩn 5 bước

### Bước 1: Truy vấn sản phẩm cần xử lý qua GraphQL
Truy vấn thông tin chi tiết của sản phẩm để phân tích:

```graphql
query getProducts($first: Int!) {
  products(first: $first, sortKey: CREATED_AT, reverse: true) {
    edges {
      node {
        id
        title
        handle
        productType
        tags
        descriptionHtml
        category {
          id
          name
          fullName
        }
      }
    }
  }
}
```

### Bước 2: Phân tích dữ liệu & Tra cứu Taxonomy Category phù hợp
Sử dụng GraphQL query để tìm kiếm node danh mục chuẩn trong hệ thống Shopify:

```graphql
query searchTaxonomy($term: String!) {
  taxonomy {
    categories(search: $term, first: 10) {
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

Nếu cần khám phá các nhánh con chuyên sâu của một danh mục cha:
```graphql
query getDescendants($parent: ID!) {
  taxonomy {
    categories(descendantsOf: $parent, first: 50) {
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

**Bảng đối chiếu danh mục tiêu chuẩn thường gặp (ví dụ tham khảo):**
| Dữ liệu sản phẩm thực tế | Danh mục chuẩn Shopify (Leaf Node) | Taxonomy Category ID |
| :--- | :--- | :--- |
| Kệ nổi gắn tường, kệ cây cảnh mini, kệ mantel giả lò sưởi | `Furniture > Shelving > Wall Shelves & Ledges > Floating Wall Shelves & Ledges` | `gid://shopify/TaxonomyCategory/fr-19-2-2` |
| Tủ đĩa than, kệ máy hát, chân đặt máy quay đĩa | `Furniture > Cabinets & Storage > Media Storage Cabinets & Racks > Turntable Stands` | `gid://shopify/TaxonomyCategory/fr-4-10-1` |
| Kệ sách đứng hình cây gỗ | `Furniture > Shelving > Bookcases & Standing Shelves` | `gid://shopify/TaxonomyCategory/fr-19-1` |
| Bàn console sảnh / sau sofa | `Furniture > Tables > Accent Tables > Console Tables` | `gid://shopify/TaxonomyCategory/fr-24-1-4` |
| Cây treo áo khoác có kệ để giày sảnh | `Furniture > Benches > Storage & Entryway Benches > Coat Racks` | `gid://shopify/TaxonomyCategory/fr-3-2-2` |
| Giá để chai rượu hình cây | `Furniture > Cabinets & Storage > Wine Racks` | `gid://shopify/TaxonomyCategory/fr-4-16` |
| Bàn phụ góc, đôn gỗ trang trí | `Furniture > Tables > Accent Tables > End Tables` | `gid://shopify/TaxonomyCategory/fr-24-1-2` |

### Bước 3: Lập kế hoạch gán danh mục & Đối soát chéo
- Tạo danh sách đối chiếu `(Product ID, Title, Proposed Category ID, Rationale)`.
- Rà soát lại từng sản phẩm: Đảm bảo không có trường hợp mâu thuẫn giữa tên/công năng thực tế và danh mục được chọn.

### Bước 4: Thực thi cập nhật hàng loạt qua Mutation `productUpdate`
Viết script Python để chạy batch update:

```graphql
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
      category {
        id
        name
        fullName
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

Variables:
```json
{
  "input": {
    "id": "gid://shopify/Product/10376238628921",
    "category": "gid://shopify/TaxonomyCategory/fr-19-2-2"
  }
}
```

**Mẫu cấu trúc Script Python thực thi:**
```python
import os, sys, time, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
shop = os.getenv("SHOPIFY_SHOP")
token = os.getenv("SHOPIFY_ADMIN_TOKEN")
api_ver = os.getenv("SHOPIFY_API_VERSION", "2024-07")
headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
graphql_url = f"https://{shop}/admin/api/{api_ver}/graphql.json"

# Lặp qua từng item trong update plan
for item in plan:
    variables = {"input": {"id": item["id"], "category": item["categoryId"]}}
    res = requests.post(graphql_url, headers=headers, json={"query": mutation, "variables": variables}, timeout=15)
    # Kiểm tra userErrors, ghi log chi tiết
    sys.stdout.flush()
    time.sleep(0.5)
```

### Bước 5: Xác minh kết quả & Dọn dẹp
1. **Xác minh lại:** Chạy query lấy lại danh sách sản phẩm vừa cập nhật, đảm bảo:
   - `category != null` cho 100% sản phẩm.
   - Toàn bộ sản phẩm hiển thị đúng tên danh mục đã chọn.
2. **Dọn dẹp môi trường:**
   - Xóa các file script tạm, file JSON nháp phục vụ quá trình chạy.
   - Đảm bảo thư mục `admin/` sạch sẽ (chạy `python admin/clean.py` nếu cần).

---

## 4. Mẫu Báo cáo kết quả cho Người Dùng

Báo cáo hoàn thành cần có:
1. **Tổng số lượng:** Số sản phẩm đã quét và cập nhật thành công (tỷ lệ thành công, số lỗi).
2. **Bảng tổng hợp theo nhóm:** Danh sách phân loại, số lượng sản phẩm mỗi nhóm, đường dẫn danh mục đầy đủ và Taxonomy Category ID.
3. **Các điểm lưu ý/sửa đổi đặc biệt:** Chỉ rõ các sản phẩm từng bị gán sai `productType` trong dữ liệu thô và đã được nắn chỉnh về đúng danh mục thực tế.
