# AI Agent Deployment Guide

Tài liệu này là hướng dẫn chuẩn dành cho các AI Agent để thực hiện cập nhật mã nguồn (deploy updates) cho dự án Shopify Admin App lên VPS. Đọc kỹ và làm theo trình tự dưới đây.

## 1. Thông tin kết nối & Môi trường
- **File thông tin VPS**: `.vps.env` chứa biến `VPS_SSH_CONNECT_COMMAND` (username@IP, ví dụ: `vmadmin@160.25.81.57`) và `VPS_SSH_CONNECT_PASSWORD`.
- **Thư mục dự án trên VPS**: `/home/vmadmin/shopify-admin-app`
- **Systemd Service**: `shopify-admin-app.service` (Quản lý tiến trình FastAPI)

## 2. Quy trình Deploy Cập Nhật Code Thường Xuyên
Khi USER yêu cầu "deploy code", "đẩy code", "cập nhật lên VPS", hãy ưu tiên sử dụng script python có sẵn trong source code để tự động hóa:

1. **Chuẩn bị**: Đảm bảo toàn bộ logic code ở local (các file như `main.py`, `templates/*.html`, `static/*`, v.v.) đã hoàn tất và test ổn định.
2. **Kiểm tra script upload**: Mở file `upload_main.py` lên để xem qua logic. Script này hiện tại đã được cấu hình để upload tự động qua giao thức SFTP (paramiko) các file sau:
   - `main.py`
   - Toàn bộ thư mục `templates/`
   - Toàn bộ thư mục `static/`
3. **Thực thi script**:
   - Sử dụng tool `run_command` để chạy lệnh: `python upload_main.py`
   - Đặt `WaitMsBeforeAsync: 500` (hoặc giá trị phù hợp) và chờ task background trả về kết quả.
4. **Kiểm tra kết quả**: Script sẽ tự động gọi SSH để thực thi lệnh `sudo systemctl restart shopify-admin-app.service`. Nếu kết quả log (stdout) báo thành công, website đã được cập nhật. Hãy thông báo cho USER.

*(Lưu ý: Nếu bạn có thêm một file hoặc thư mục mới cần đẩy lên, hãy chủ động dùng tool sửa file `upload_main.py` để bổ sung lệnh `upload_file()` tương ứng trước khi chạy.)*

## 3. Quy trình Deploy Toàn Bộ (Full Deploy)
Nếu USER yêu cầu cài lại toàn bộ VPS, update các thư viện python mới (thay đổi `requirements.txt`), hoặc có thay đổi lớn:
- Sử dụng script `deploy_runner.py`.
- Lệnh: `python deploy_runner.py`.
- Chú ý đọc qua code của script này trước khi chạy vì nó sẽ reset lại virtual environment (`venv`) và ghi đè lại file service.

## 4. Xử lý Lỗi (Troubleshooting)
- Nếu sau khi deploy mà website bị lỗi `Internal Server Error` (Lỗi 500), hãy dùng `run_command` kết nối SSH vào VPS (`ssh vmadmin@<IP>`) và chạy lệnh `sudo journalctl -u shopify-admin-app.service -n 50 --no-pager` để lấy log lỗi báo cho USER.
- Nếu bị lỗi Nginx (Lỗi 502 Bad Gateway), kiểm tra trạng thái uvicorn thông qua SSH hoặc xem có xung đột port (8085) hay không.
