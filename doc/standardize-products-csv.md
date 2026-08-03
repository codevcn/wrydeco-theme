# Standardize Products CSV

Tài liệu này cung cấp quy trình chuẩn (SOP) cho AI agent để xử lý và chuẩn hóa file CSV export từ Shopify trước khi import vào một store mới (ví dụ: chuyển từ store ngôn ngữ VN sang US), đảm bảo file ở trạng thái **ready to import**.

Hãy thực hiện tuần tự 3 bước sau bằng script Python:

## 1. Fix Product Category (Chuẩn hóa ngôn ngữ Taxonomy)
Khi export từ store đang dùng giao diện tiếng Việt, cột `Product Category` sẽ chứa chuỗi đã bị dịch sang tiếng Việt (vd: `Đồ gỗ > Giá > Giá sách và kệ đứng`). Store US sẽ báo lỗi "invalid product category" và từ chối nhận các giá trị này. Cần phải đưa chúng về đúng chuẩn **Shopify Standard Product Taxonomy** bằng tiếng Anh.

**Hướng dẫn thực hiện:**
- **KHÔNG TỰ DỊCH TAY**: Các danh mục phải khớp 100% từng chữ cái với Taxonomy của Shopify.
- **Phương pháp khuyên dùng**: 
  - *Cách 1*: Lấy taxonomy chuẩn từ API của Shopify (hoặc query `category.fullName` qua GraphQL Admin API của store cũ) để lấy danh sách tiếng Anh chuẩn, sau đó đối chiếu.
  - *Cách 2*: Tải file `categories.json` cho locale `vi` và `en` từ GitHub của Shopify Product Taxonomy, map 1-1 qua ID, và thay thế vào CSV.
- **Cảnh báo (Bẫy tiền tố)**: Khi thực hiện thay thế (replace), luôn phải thay thế các chuỗi danh mục dài trước (các sub-category chi tiết), sau đó mới thay chuỗi ngắn (chuỗi cha). Ví dụ: phải replace `Đồ gỗ > Giá > Giá sách và kệ đứng > Tủ & kệ sách treo` trước khi replace `Đồ gỗ > Giá > Giá sách và kệ đứng`. Nếu làm ngược lại, các chuỗi dài sẽ bị cắt cụt sai lệch.

## 2. Gắn Product Category cho các sản phẩm chưa có
Một số sản phẩm trong file CSV có thể bị bỏ trống cột `Product Category`. Để tối ưu SEO và quản lý, cần bổ sung đầy đủ.

**Hướng dẫn thực hiện:**
- Lọc ra các dòng (sản phẩm) có cột `Product Category` đang trống.
- Đọc nội dung cột `Title` và `Body (HTML)` (description) của sản phẩm đó để hiểu sản phẩm là gì.
- Dựa vào danh sách Shopify Standard Product Taxonomy tiếng Anh, tự đề xuất category phù hợp nhất và điền vào cột `Product Category`.
- Đảm bảo điền chuỗi category đầy đủ (Full Path).

## 3. Tắt Track Quantity (Theo dõi số lượng tồn kho)
Để không phải quản lý tồn kho ngay sau khi import, cần tắt tính năng theo dõi số lượng.

**Hướng dẫn thực hiện:**
- Tìm cột `Variant Inventory Tracker` trong file CSV. Chuyển tất cả các giá trị đang có (ví dụ: `shopify`) thành rỗng (`""`).
- Tìm cột `Variant Inventory Qty` và làm trống (clear) toàn bộ giá trị số lượng bên trong, vì không track thì số lượng không còn ý nghĩa.

---

## Ràng buộc về File Output (Bắt buộc tuân thủ)
- **Sao lưu**: Luôn tạo một file backup `.bak` của CSV gốc trước khi chạy script sửa đổi.
- **Tính toàn vẹn**: Số lượng dòng (lines) của file CSV sau khi sửa phải khớp 100% với file gốc. Chú ý giữ nguyên mọi nội dung ở các cột khác, đặc biệt là Description (Body HTML).
- **Format chuẩn Shopify**: Ghi file CSV lưu ý KHÔNG có BOM (Byte Order Mark), sử dụng line ending là LF (`\n`), và chỉ dùng quote (`""`) theo chuẩn `csv.QUOTE_MINIMAL`.
