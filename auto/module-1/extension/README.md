# 🪵 Wrydeco Amazon Scraper - Chrome Extension (Manifest V3)

Extension chuyên dụng dành cho quy trình tự động hóa cập nhật sản phẩm từ Amazon lên Shopify Store của Wrydeco (`auto/module-1`).

---

## 🌟 Tính Năng Nổi Bật

1. **Hỗ trợ 2 Chế độ Cào Dữ Liệu Chuyên Biệt**:
   - **Preset Tier Mode (Đồ gỗ Wrydeco chuẩn)**: Tự động trích xuất tiêu đề, mô tả (bullet points), bộ ảnh gallery kích thước lớn, A+ Content (Rich Description) từ Amazon, kết hợp tự sinh bảng kích thước & giá cố định theo 3 phân loại:
     - `corner`: Corner Bookshelf (Kệ góc) — Tiers: `LUXURY`, `PREM`, `LOW`.
     - `standing`: Standing Bookshelf (Kệ đứng) — Tiers: `PREM`, `LOW`.
     - `floating`: Floating Bookshelf (Kệ treo) — Tiers: `PREM`, `LOW`.
     *(Base price tự động đặt là `0`, toàn bộ giá tính vào `additional_price` của từng biến thể)*.
   - **Dynamic Mode (Amazon Customization)**: Cào động các tùy chọn từ form tùy biến của Amazon (hỗ trợ `#gc-iframe`), tự động mở rộng các mục bị thu gọn, loại bỏ các trường ghi chú seller (`IGNORE_TYPES`), loại bỏ option mặc định không tăng giá (`VARIANT_FOR_DEFAULT_OPTION_TO_IGNORE`) và tính toán toàn bộ tổ hợp biến thể Cartesian product.

2. **Cấu Trúc Dữ Liệu Chuẩn Khớp 100%**:
   - Output xuất ra chuẩn cấu trúc `product` của `auto/module-1/config.prepare.json` và `config.json`.
   - Các trường cào được: `product_title`, `product_description`, `product_images`, `base_price`, `variant_data`, `product_rich_description`, `product_amazon_link`.

3. **Tiện Ích & Trải Nghiệm Người Dùng**:
   - **Tự động sao chép JSON vào Clipboard** ngay khi cào xong.
   - **Tải file `config.prepare.json`** trực tiếp chỉ với 1 click để đặt vào thư mục `auto/module-1`.
   - **Nút "Copy product JSON" nổi** ở góc dưới màn hình trang Amazon giúp copy nhanh ngay cả khi popup extension đóng.
   - **Hộp nhật ký tiến trình (Status Logs)** hiển thị từng bước cào chi tiết với thời gian thực.
   - **Ghi nhớ cấu hình & dữ liệu lần cào gần nhất** qua `chrome.storage.local`.

---

## 🚀 Hướng Dẫn Cài Đặt (Chrome Extension Unpacked)

1. Mở trình duyệt Chrome hoặc Edge / Brave / Cốc Cốc.
2. Truy cập vào trang quản lý tiện ích: `chrome://extensions/`
3. Bật công tắc **"Chế độ dành cho nhà phát triển" (Developer mode)** ở góc trên bên phải.
4. Bấm vào nút **"Tải tiện ích đã giải nén" (Load unpacked)** ở góc trên bên trái.
5. Chọn thư mục:
   ```
   d:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-app\auto\module-1\extension
   ```
6. Tiện ích **"Wrydeco Amazon Scraper"** sẽ xuất hiện trên thanh công cụ trình duyệt. Bấm vào biểu tượng ghim (Pin) để tiện sử dụng.

---

## 🛠️ Quy Trình Sử Dụng với Module-1

1. Truy cập vào trang sản phẩm Amazon cần lấy dữ liệu (ví dụ: `https://www.amazon.com/dp/...`).
2. Nhấp vào icon **Wrydeco Scraper** trên thanh công cụ trình duyệt:
   - **Nếu dùng Preset Tier**: Chọn loại kệ (`corner` / `standing` / `floating`) và phân cấp giá (`LUXURY` / `PREM` / `LOW`). Bảng kích thước xem trước sẽ hiển thị ngay bên dưới.
   - **Nếu dùng Dynamic Mode**: Mở form "Customize Now" trên trang Amazon (hoặc extension sẽ tự động kích hoạt), chọn chiến lược giá (`error`, `min`, hoặc `max`).
3. Bấm **"🚀 Bắt đầu cào dữ liệu"**.
4. Theo dõi log tiến trình chạy. Khi hoàn tất:
   - Dữ liệu JSON đã tự động được sao chép vào Clipboard.
   - Bạn có thể bấm **"💾 Tải config.prepare.json"** và lưu đè vào thư mục `auto/module-1/config.prepare.json`.
5. Tiếp tục quy trình module-1:
   ```cmd
   prepare_config.cmd
   run.cmd
   ```

---

## 📁 Danh Sách Tệp Trong Thư Mục Extension

```
auto/module-1/extension/
├── manifest.json         # Cấu hình Manifest V3 cho Chrome Extension
├── popup.html            # Giao diện điều khiển Popup
├── popup.css             # Giao diện Dark theme hiện đại, responsive
├── popup.js              # Xử lý tương tác, chuyển mode, lưu cấu hình, tải JSON
├── content.js            # Script cào dữ liệu DOM Amazon (cả Dynamic & Preset Tier)
├── background.js         # Service worker quản lý vòng đời & download
├── icons/                # Bộ icon đa kích thước tạo từ extension-logo.png
│   ├── icon16.png
│   ├── icon32.png
│   ├── icon48.png
│   └── icon128.png
├── extension-logo.png    # Ảnh logo gốc
└── README.md             # Tài liệu hướng dẫn sử dụng
```
