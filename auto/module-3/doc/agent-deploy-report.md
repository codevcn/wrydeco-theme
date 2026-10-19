# Báo Cáo Triển Khai (Deploy Report)

**Dự án:** Shopify Admin App (vnote.io.vn)
**Ngày hoàn thành:** 31/07/2026
**Trạng thái:** THÀNH CÔNG ✅
**Đường dẫn truy cập:** [https://shopify.vnote.io.vn](https://shopify.vnote.io.vn)

---

## 1. Tóm tắt Quá trình Triển khai ban đầu
- **Tạo môi trường cách ly:** Triển khai mã nguồn vào thư mục riêng biệt `/home/vmadmin/shopify-admin-app` trên VPS (`160.25.81.57`) để không xung đột với các dịch vụ khác.
- **Cài đặt thư viện:** Thiết lập môi trường ảo (`venv`) và cài đặt các dependencies (FastAPI, Uvicorn, Jinja2, requests,...).
- **Cấu hình Process Manager:** Tạo và kích hoạt systemd service có tên `shopify-admin-app.service` chạy ngầm ở port `8085`.
- **Cấu hình Nginx:** Viết cấu hình Reverse Proxy cho tên miền `shopify.vnote.io.vn` trỏ vào port `8085`.

---

## 2. Các sự cố phát sinh và Biện pháp khắc phục

Trong quá trình "Go Live", hệ thống đã gặp một số sự cố. Dưới đây là chi tiết nguyên nhân và cách Agent đã xử lý:

### Sự cố 1: Lỗi hiển thị trang Nginx mặc định & Không thể lấy chứng chỉ SSL (Lỗi 404)
- **Nguyên nhân:** Có sự bất đồng bộ giữa biến môi trường. File `.vps.env` cũ lưu IP `103.147.123.63` khiến user trỏ nhầm DNS, trong khi thực tế server kết nối và deploy thành công lại mang IP `160.25.81.57`. Đồng thời Nginx chưa bị xóa trang cấu hình `default`.
- **Cách khắc phục:** 
  - Hướng dẫn user đổi IP trong bản ghi DNS `shopify` về đúng `160.25.81.57`.
  - Kết nối vào server xóa bỏ file `/etc/nginx/sites-enabled/default` và chạy lại Certbot. Kết quả: SSL được cấp phát thành công, trang web tự động ép sang HTTPS.

### Sự cố 2: Lỗi "Internal Server Error" do Shopify Token (Lỗi 401 Unauthorized)
- **Nguyên nhân:** File `.env` chứa biến `SHOPIFY_API_VERSION=2026-07` không hợp lệ (version chưa ra mắt) và `SHOPIFY_ADMIN_TOKEN` cũ đã bị hết hạn/thu hồi.
- **Cách khắc phục:** Nhận thông tin cấu hình mới từ user, điều chỉnh lại API version về bản ổn định `2024-04` và thay token mới (`shpat_76c...`) vào file `.env` trên VPS. Khởi động lại service.

### Sự cố 3: Lỗi "Internal Server Error" do xung đột thư viện FastAPI (TypeError)
- **Nguyên nhân:** Giao diện bị sập với lỗi `TypeError: unhashable type: 'dict'` phát sinh ở hàm xử lý lỗi của Starlette. Nguyên nhân sâu xa là do cú pháp `templates.TemplateResponse("index.html", {...})` trong `main.py` không còn tương thích với phiên bản FastAPI/Starlette mới nhất cài trên server.
- **Cách khắc phục:** 
  - Viết một kịch bản bằng Regex (Python script) quét toàn bộ mã nguồn `main.py`.
  - Tự động thay thế hàng loạt cú pháp cũ sang chuẩn mới: `templates.TemplateResponse(request=request, name="index.html", context={...})`.
  - Tải lại file `main.py` lên server và restart `shopify-admin-app.service`.

---

## 3. Tổng kết
Tất cả các công việc từ upload code, cấu hình môi trường, cài đặt reverse proxy Nginx, lấy chứng chỉ bảo mật Let's Encrypt (HTTPS), cho đến việc debug mã nguồn và sửa lỗi trực tiếp trên server đều được hoàn thành và ghi chép lại đầy đủ.

Website hiện đã chạy mượt mà và an toàn tại `https://shopify.vnote.io.vn`. Toàn bộ nhật ký các lệnh SSH được lưu lại tại file `logs/vps-ssh.log`.

## 4. 2026-10-13 — Real Homes video playback repair (WRYDECO)

Confirmed on the live storefront with Playwright: a gallery video requested a private Shopify originals URL, which returned HTTP 403 / XML `AccessDenied`. The upload helper had accepted `originalSource` before processing completed and could also fall back to the staged resource URL.

Updated only the Real Homes upload/media functions on the active VPS at `/home/azureuser/shopify-admin-app/main.py`. Uploads now wait for `READY` and a public MP4 rendition, prefer 720p, and never return a private/staged URL as a fallback. Polling runs in a worker thread. Unrelated functions, templates, environment files, and Nginx configuration were preserved. The service restarted successfully; the subsequent readiness check returned HTTP 200 on port 8085.

Remote backup: `/home/azureuser/shopify-admin-app/main.py.video-fix-20261013T043513Z.bak`. Deployment hashes and commands are recorded in `logs/real-homes-video-fix-20261013T043513Z.json`. Original gallery values are retained in the repository's `admin/backups/` directory.

Replaced six private video URLs across four existing project entries, retaining gallery order, images, and posters. A later read-only audit found no remaining private URLs. Eight upload/source-selection regression tests passed. Playwright verified all nine currently listed videos across five projects at 1440×900 and 390×844 (18 playback checks: time advanced, readyState 4, no media errors). The requested Chrome browser also played the original affected project video and the single-video project through to their durations without media errors.
