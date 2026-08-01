# Kế Hoạch Triển Khai (Deploy) Lên Shared VPS

Kế hoạch này tập trung vào sự đơn giản, nhanh chóng nhưng vẫn đảm bảo không gây xung đột với các service hoặc process khác đang chạy trên hệ thống VPS.

## Bước 1: Tạo thư mục chứa mã nguồn riêng biệt
Sử dụng tài khoản mặc định `vmadmin` (được cấp quyền sudo).
- Tạo thư mục dành riêng cho dự án tại: `/home/vmadmin/shopify-admin-app`.
- Thư mục này sẽ chứa toàn bộ code và môi trường chạy để không ảnh hưởng đến các file khác trên VPS.

## Bước 2: Đưa mã nguồn lên VPS
- Sử dụng lệnh `scp` (hoặc `rsync`) từ máy tính local để copy thư mục dự án lên đường dẫn `/home/vmadmin/shopify-admin-app` trên VPS.
- Kiểm tra để đảm bảo file `.env` chứa token Shopify được upload đầy đủ.

## Bước 3: Thiết lập môi trường Python ảo (Virtual Environment)
Để không làm hỏng các thư viện Python của hệ điều hành hay các app khác:
- Khởi tạo venv tại: `/home/vmadmin/shopify-admin-app/venv` bằng lệnh `python3 -m venv venv`.
- Dùng `venv/bin/pip` cài đặt các thư viện cần thiết từ file `requirements.txt` (FastAPI, uvicorn, requests,...).

## Bước 4: Tạo Systemd Service để chạy ngầm
Tạo một service mới trên hệ thống để quản lý tiến trình FastAPI.
- Tạo file cấu hình bằng quyền sudo: `/etc/systemd/system/shopify-admin-app.service`.
- Service này sẽ chạy dưới quyền user `vmadmin`.
- Chọn một port an toàn chưa ai sử dụng (ví dụ: `8085`) để uvicorn lắng nghe. Lệnh khởi chạy sẽ là: `/home/vmadmin/shopify-admin-app/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8085`.
- Enable và start service bằng `systemctl`.

## Bước 5: Cấu hình Nginx
Nginx sẽ đóng vai trò Reverse Proxy để định tuyến yêu cầu từ ngoài internet vào ứng dụng.
- Thêm một file cấu hình Nginx mới: `/etc/nginx/sites-available/shopify-admin-app.conf`.
- Chuyển hướng traffic từ Domain/Subdomain (hoặc Port public) vào `http://127.0.0.1:8085`.
- Kiểm tra cú pháp (`sudo nginx -t`) để đảm bảo config an toàn tuyệt đối trước khi reload Nginx (`sudo systemctl reload nginx`).

## Bước 6: Kiểm tra hoạt động
- Truy cập vào Domain hoặc IP của VPS để thử nghiệm các tính năng của trang LocalAdmin.
- Theo dõi log của ứng dụng qua `sudo journalctl -u shopify-admin-app.service` để đảm bảo mọi thứ chạy trơn tru.

## Yêu cầu Đặc Biệt: Lưu vết thực thi và Báo cáo (Logging & Reporting)
- **Log toàn bộ thao tác**: Trong suốt quá trình thực thi các bước trên, toàn bộ các lệnh SSH được gọi và kết quả (output) trả về từ VPS phải được ghi chép đầy đủ vào file local `logs/vps-ssh.log`.
- **Báo cáo kết quả**: Sau khi hoàn thành quá trình deploy, phải tổng hợp và ghi một báo cáo chi tiết vào file `doc/agent-deploy-report.md`.
- **Xử lý lỗi**: Nếu gặp bất kỳ lỗi nào trong quá trình thực thi plan, tiến trình phải dừng lại ngay lập tức và toàn bộ thông tin về lỗi cũng như trạng thái hiện tại phải được ghi báo cáo vào file `doc/agent-deploy-report.md`.
- **Mục đích**: Giúp anh/chị có thể theo dõi tiến độ rõ ràng, nắm bắt kết quả tổng quan và xử lý nhanh nếu sự cố xảy ra.
