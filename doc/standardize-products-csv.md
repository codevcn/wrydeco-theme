# Standardize Products CSV

Tài liệu này cung cấp quy trình chuẩn (SOP) cho AI agent để xử lý và chuẩn hóa file CSV export từ Shopify trước khi import vào một store mới (ví dụ: chuyển từ store ngôn ngữ VN sang US), đảm bảo file ở trạng thái **ready to import**.

Hãy thực hiện tuần tự 3 bước sau bằng script Python:

## 1. Tắt Track Quantity (Theo dõi số lượng tồn kho)
Để không phải quản lý tồn kho ngay sau khi import, cần tắt tính năng theo dõi số lượng.

**Hướng dẫn thực hiện:**
- Tìm cột `Variant Inventory Tracker` trong file CSV. Chuyển tất cả các giá trị đang có (ví dụ: `shopify`) thành rỗng (`""`).
- Tìm cột `Variant Inventory Qty` và làm trống (clear) toàn bộ giá trị số lượng bên trong, vì không track thì số lượng không còn ý nghĩa.

---

## Ràng buộc về File Output (Bắt buộc tuân thủ)
- **Sao lưu**: Luôn tạo một file backup `.bak` của CSV gốc trước khi chạy script sửa đổi.
- **Tính toàn vẹn**: Số lượng dòng (lines) của file CSV sau khi sửa phải khớp 100% với file gốc. Chú ý giữ nguyên mọi nội dung ở các cột khác, đặc biệt là Description (Body HTML).
- **Format chuẩn Shopify**: Ghi file CSV lưu ý KHÔNG có BOM (Byte Order Mark), sử dụng line ending là LF (`\n`), và chỉ dùng quote (`""`) theo chuẩn `csv.QUOTE_MINIMAL`.
