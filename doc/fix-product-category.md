# Hướng dẫn AI Agent: Fix lỗi Product Category khi Export/Import CSV trên Shopify

## 1. Bối cảnh & Vấn đề

Khi export sản phẩm từ một store Shopify có cài đặt ngôn ngữ địa phương (VD: Tiếng Việt), cột `Product Category` trong file CSV thường bị dịch sang ngôn ngữ đó (ví dụ: `Đồ gỗ > Giá > Giá sách và kệ đứng`).
Khi import file CSV này sang một store Shopify khác (đặc biệt là store mặc định tiếng Anh), hệ thống sẽ báo lỗi **"invalid product category… will not be set"** vì Shopify Standard Product Taxonomy yêu cầu chuỗi danh mục phải chuẩn xác bằng tiếng Anh.

## 2. Mục tiêu

Sửa lại giá trị của cột `Product Category` trong file CSV từ ngôn ngữ địa phương sang chuỗi chuẩn tiếng Anh của Shopify, đảm bảo **không làm thay đổi hay ảnh hưởng đến bất kỳ dữ liệu nào khác** (như Product Title, Description, Line Endings, v.v.).

## 3. Quy tắc cốt lõi (Bắt buộc tuân thủ)

- **KHÔNG tự dịch tay:** Các danh mục phải khớp 100% với Shopify Standard Product Taxonomy. Việc tự dịch dễ dẫn đến sai lệch.
- **KHÔNG dùng `replace()` dạng raw text:** Việc tìm và thay thế chuỗi trên toàn bộ file text sẽ dẫn đến nguy cơ (1) vô tình thay đổi nội dung mô tả/tên sản phẩm, (2) lỗi tiền tố (ví dụ: chuỗi ngắn bị thay thế trước làm hỏng chuỗi dài).
- **CHỈ SỬA ĐÚNG 1 CỘT:** File CSV sau khi sửa phải giữ nguyên hoàn toàn số dòng, các giá trị ở cột khác, và cấu trúc quote/line ending (thường là LF).

## 4. Quy trình xử lý chuẩn dành cho AI Agent

Dưới đây là phương pháp tự động, an toàn và chuẩn xác nhất:

### Bước 1: Truy vấn API để lấy danh mục tiếng Anh gốc

Sử dụng Shopify Admin API (GraphQL) của store gốc để lấy danh sách `handle` và `category.fullName`. API luôn trả về taxonomy chuẩn tiếng Anh bất kể ngôn ngữ hiển thị của store.

```graphql
query ($cursor: String) {
  products(first: 250, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        handle
        category {
          fullName
        }
      }
    }
  }
}
```

_Lưu kết quả truy vấn thành một mapping dictionary (ví dụ: `api_categories[handle] = "Furniture > Shelving > Bookcases & Standing Shelves"`)._

### Bước 2: Dùng thư viện phân tích CSV chuẩn để sửa file

Viết một script Python sử dụng thư viện `csv` tích hợp sẵn. Đọc file, lấy header, định vị cột `Handle` và `Product Category`.

```python
import csv
import io

csv_path = "path/to/products_export.csv"

# Đọc nội dung, bỏ BOM nếu có, giữ nguyên newline
with open(csv_path, 'r', encoding='utf-8', newline='') as f:
    content = f.read()
    if content.startswith('\ufeff'):
        content = content[1:]

reader = csv.reader(io.StringIO(content))
headers_row = next(reader)

handle_idx = headers_row.index('Handle')
cat_idx = headers_row.index('Product Category')

rows = []
for row in reader:
    handle = row[handle_idx]
    old_cat = row[cat_idx]

    # Chỉ ghi đè nếu ô Product Category hiện tại có dữ liệu và handle có trong mapping
    if old_cat and handle in api_categories:
        row[cat_idx] = api_categories[handle]

    rows.append(row)
```

### Bước 3: Ghi lại file CSV tuân thủ chuẩn của Shopify

Shopify CSV thường lưu dưới định dạng không có BOM, sử dụng line ending là `LF` (`\n`), và chỉ dùng quote (`""`) khi thực sự cần thiết (tương đương `csv.QUOTE_MINIMAL`).

```python
with open(csv_path, 'w', encoding='utf-8', newline='\n') as f:
    writer = csv.writer(f, lineterminator='\n')
    writer.writerow(headers_row)
    writer.writerows(rows)
```

## 5. Xác minh kết quả

Sau khi chạy script, AI Agent cần:

1. Đếm lại số dòng của file CSV cũ và mới, đảm bảo **số dòng giữ nguyên**.
2. Kiểm tra số lượng ô bị thay đổi, phải khớp chính xác với số lượng sản phẩm có category.
3. Luôn sao lưu (backup) file CSV gốc trước khi thao tác (vd: tạo bản copy `.bak`).
