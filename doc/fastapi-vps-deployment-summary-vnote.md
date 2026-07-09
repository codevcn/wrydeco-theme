# FastAPI VPS Deployment Summary — `vnote.io.vn`

## 1. Mục tiêu

Build hoàn chỉnh một server **FastAPI** chạy trên **Ubuntu VPS**, có thể serve client/browser thông qua domain public.

Mục tiêu cuối cùng:

```txt
Client / Browser / Frontend
        ↓
https://vnote.io.vn
        ↓
Nginx Reverse Proxy
        ↓
FastAPI / Uvicorn chạy nội bộ trên port 8000
        ↓
Service chạy nền 24/7 bằng systemd
```

Kết quả hiện tại: **đã hoàn thành**.

---

## 2. Thông tin server hiện tại

```txt
VPS IP:      160.25.81.57
Domain:      vnote.io.vn
WWW domain:  www.vnote.io.vn
SSH user:    vmadmin
Project:     wrydeco-temp-server
Project dir: /var/www/wrydeco-temp-server
Runtime:     Python virtualenv .venv
App runner:  /var/www/wrydeco-temp-server/run.py
Internal port: 8000
Public HTTP:  80
Public HTTPS: 443
```

URL public đã dùng được:

```txt
https://vnote.io.vn/admin
https://www.vnote.io.vn/admin
```

---

## 3. Kiến trúc triển khai

### 3.1. DNS

Domain `vnote.io.vn` đã được trỏ về VPS:

```txt
vnote.io.vn → 160.25.81.57
```

Record DNS cần có:

```txt
@     A     160.25.81.57
www   A     160.25.81.57
```

Đã kiểm tra bằng Windows PowerShell:

```powershell
nslookup vnote.io.vn
```

Kết quả đúng:

```txt
Name:    vnote.io.vn
Address: 160.25.81.57
```

---

### 3.2. FastAPI app

FastAPI app đang nằm tại:

```bash
/var/www/wrydeco-temp-server
```

Server chạy bằng command logic trong `run.py`:

```bash
ENV=prod python run.py
```

Khi chạy thành công, Uvicorn log:

```txt
Uvicorn running on http://0.0.0.0:8000
```

Route đã xác nhận hoạt động:

```txt
GET /admin → 200 OK
```

Route `/` hiện trả:

```json
{ "detail": "Not Found" }
```

Điều này bình thường nếu trong FastAPI chưa khai báo route `/`.

---

### 3.3. systemd service

Để server chạy 24/7, app không được chạy trực tiếp trong terminal theo kiểu foreground. Đã tạo service systemd:

```txt
/etc/systemd/system/wrydeco-temp-server.service
```

Service hiện tại:

```txt
wrydeco-temp-server.service
```

Trạng thái đã xác nhận:

```txt
Active: active (running)
```

Service chạy process:

```txt
/var/www/wrydeco-temp-server/.venv/bin/python /var/www/wrydeco-temp-server/run.py
```

Ví dụ service file nên có dạng:

```ini
[Unit]
Description=Wrydeco Temp FastAPI Server
After=network.target

[Service]
User=vmadmin
Group=vmadmin
WorkingDirectory=/var/www/wrydeco-temp-server
Environment="ENV=prod"
ExecStart=/var/www/wrydeco-temp-server/.venv/bin/python /var/www/wrydeco-temp-server/run.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Các lệnh đã dùng:

```bash
sudo systemctl daemon-reload
sudo systemctl enable wrydeco-temp-server
sudo systemctl start wrydeco-temp-server
sudo systemctl status wrydeco-temp-server
```

Ý nghĩa:

- `enable`: service tự chạy lại sau khi VPS reboot.
- `start`: chạy service ngay.
- `Restart=always`: app crash thì systemd tự chạy lại.

---

### 3.4. Nginx Reverse Proxy

Ban đầu VPS chưa có Nginx. Khi chạy:

```bash
ls -la /etc/nginx
```

máy báo:

```txt
No such file or directory
```

Sau đó đã cài Nginx:

```bash
sudo apt install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

Trạng thái Nginx đã xác nhận:

```txt
Active: active (running)
```

Nginx config domain:

```txt
/etc/nginx/sites-available/vnote.io.vn
```

Symlink sang:

```txt
/etc/nginx/sites-enabled/vnote.io.vn
```

Default site đã được gỡ khỏi `sites-enabled` để tránh chiếm domain/IP:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

Config reverse proxy nên có dạng:

```nginx
server {
    listen 80;
    server_name vnote.io.vn www.vnote.io.vn;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Sau khi tạo config, đã test và reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Kết quả hợp lệ:

```txt
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

---

### 3.5. HTTPS / SSL bằng Certbot

Đã cài Certbot:

```bash
sudo apt install certbot python3-certbot-nginx -y
```

Đã cấp SSL cho cả domain gốc và `www`:

```bash
sudo certbot --nginx -d vnote.io.vn -d www.vnote.io.vn
```

Kết quả thành công:

```txt
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/vnote.io.vn/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/vnote.io.vn/privkey.pem
Congratulations! You have successfully enabled HTTPS on https://vnote.io.vn and https://www.vnote.io.vn
```

Certbot cũng đã setup auto-renew:

```txt
Certbot has set up a scheduled task to automatically renew this certificate in the background.
```

Từ thời điểm này, client/frontend nên gọi API bằng HTTPS:

```txt
https://vnote.io.vn/<api-route>
```

Không nên gọi HTTP nếu frontend đang chạy HTTPS, vì browser có thể chặn do lỗi mixed content.

---

## 4. Các lỗi đã gặp và cách xử lý

### 4.1. Lỗi `sudo source .venv/bin/activate`

Lỗi:

```txt
sudo: source: command not found
```

Nguyên nhân:

- `source` là shell builtin, không phải binary command để `sudo` chạy.

Cách đúng:

```bash
source .venv/bin/activate
```

Không dùng `sudo source`.

---

### 4.2. Lỗi Git `detected dubious ownership`

Lỗi:

```txt
fatal: detected dubious ownership in repository at '/var/www/wrydeco-temp-server'
```

Nguyên nhân:

- Repo từng bị tạo/chown bằng user khác như `root` hoặc `www-data`.
- User hiện tại `vmadmin` không được Git tin là owner hợp lệ.

Cách xử lý sạch:

```bash
sudo chown -R vmadmin:vmadmin /var/www/wrydeco-temp-server
```

Sau đó:

```bash
cd /var/www/wrydeco-temp-server
git pull origin main
```

Ghi chú: không nên chown project về `www-data` nếu bạn muốn deploy bằng user `vmadmin`.

---

### 4.3. Chạy `ENV=prod python run.py` bị giữ terminal

Command:

```bash
ENV=prod python run.py
```

Khi chạy trực tiếp sẽ giữ terminal vì server chạy foreground.

Thoát bằng:

```txt
Ctrl + C
```

Cách deploy đúng cho 24/7:

```bash
sudo systemctl start wrydeco-temp-server
```

---

### 4.4. VPS chưa có Nginx

Lỗi:

```txt
ls: cannot access '/etc/nginx': No such file or directory
```

Cách xử lý:

```bash
sudo apt install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
```

Sau khi cài, `/etc/nginx` xuất hiện và có cấu trúc:

```txt
conf.d
sites-available
sites-enabled
nginx.conf
snippets
```

---

### 4.5. PowerShell `curl -I` bị lỗi

Trên Windows PowerShell, `curl` có thể là alias của `Invoke-WebRequest`, nên command này lỗi:

```powershell
curl -I http://vnote.io.vn/admin
```

Cách đúng:

```powershell
curl.exe -I http://vnote.io.vn/admin
```

Hoặc:

```powershell
Invoke-WebRequest -Method Head -Uri "http://vnote.io.vn/admin"
```

---

### 4.6. `405 Method Not Allowed` khi dùng `curl -I`

Kết quả:

```txt
HTTP/1.1 405 Method Not Allowed
allow: GET
```

Nguyên nhân:

- `curl -I` gửi request `HEAD`.
- Route `/admin` của FastAPI chỉ cho phép `GET`.

Đây không phải lỗi Nginx/DNS.

Test đúng bằng GET:

```powershell
curl.exe -i http://vnote.io.vn/admin
```

Kết quả đúng là HTML trang Admin Manager hoặc `200 OK`.

---

## 5. Trạng thái xác nhận đã thành công

### 5.1. FastAPI chạy nội bộ

Trên VPS:

```bash
curl http://127.0.0.1:8000/admin
```

Đã trả về HTML:

```html
<title>Admin Manager Page</title>
```

---

### 5.2. Browser gọi domain thành công

Log service ghi nhận request từ client thật:

```txt
GET /admin HTTP/1.1" 200 OK
```

Điều này chứng minh luồng sau đã hoạt động:

```txt
Browser → vnote.io.vn → Nginx → FastAPI → /admin
```

---

### 5.3. HTTPS đã bật thành công

Certbot báo:

```txt
Congratulations! You have successfully enabled HTTPS on https://vnote.io.vn and https://www.vnote.io.vn
```

URL hiện dùng được:

```txt
https://vnote.io.vn/admin
```

---

## 6. Quy trình deploy lại sau này

Mỗi lần sửa code và push lên GitHub, SSH vào VPS rồi chạy:

```bash
cd /var/www/wrydeco-temp-server
sudo chown -R vmadmin:vmadmin /var/www/wrydeco-temp-server
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart wrydeco-temp-server
sudo systemctl status wrydeco-temp-server
```

Kiểm tra logs nếu có lỗi:

```bash
sudo journalctl -u wrydeco-temp-server -f
```

Thoát log:

```txt
Ctrl + C
```

---

## 7. Các lệnh quản trị quan trọng

### 7.1. FastAPI service

```bash
sudo systemctl status wrydeco-temp-server
sudo systemctl restart wrydeco-temp-server
sudo systemctl stop wrydeco-temp-server
sudo systemctl start wrydeco-temp-server
sudo journalctl -u wrydeco-temp-server -f
sudo journalctl -u wrydeco-temp-server -n 100 --no-pager
```

---

### 7.2. Nginx

```bash
sudo systemctl status nginx
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl restart nginx
sudo nginx -T | grep -n "vnote.io.vn"
```

---

### 7.3. Test từ VPS

```bash
curl http://127.0.0.1:8000/admin
curl -i http://vnote.io.vn/admin
curl -i https://vnote.io.vn/admin
```

---

### 7.4. Test từ Windows 11

```powershell
nslookup vnote.io.vn
curl.exe -i https://vnote.io.vn/admin
```

---

## 8. Cách client/frontend nên gọi API

Nếu client là website HTTPS, ví dụ Shopify storefront, client nên gọi:

```js
fetch("https://vnote.io.vn/your-api-route", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    example: "data",
  }),
});
```

Không dùng:

```js
fetch("http://vnote.io.vn/your-api-route");
```

vì dễ bị browser chặn mixed content.

---

## 9. CORS cho FastAPI nếu frontend khác domain

Nếu frontend nằm ở domain khác, ví dụ:

```txt
https://wrydeco.com
```

và gọi API:

```txt
https://vnote.io.vn
```

thì cần bật CORS trong FastAPI.

Ví dụ:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://wrydeco.com",
        "https://www.wrydeco.com",
        "https://vnote.io.vn",
        "https://www.vnote.io.vn",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Sau khi sửa code:

```bash
cd /var/www/wrydeco-temp-server
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart wrydeco-temp-server
```

---

## 10. Việc nên làm tiếp theo

### 10.1. Tạo route health check

Nên thêm route:

```txt
GET /health
```

Ví dụ response:

```json
{ "ok": true }
```

Để kiểm tra server nhanh:

```bash
curl https://vnote.io.vn/health
```

---

### 10.2. Tạo route `/`

Hiện tại `/` trả `Not Found`. Có thể thêm route đơn giản:

```python
@app.get("/")
def root():
    return {"service": "wrydeco-temp-server", "status": "ok"}
```

---

### 10.3. Bảo vệ trang `/admin`

Trang `/admin` hiện public. Nếu có dữ liệu thật, nên thêm ít nhất một lớp bảo vệ:

- Basic Auth qua Nginx.
- Login trong FastAPI.
- Token-based access.
- Chỉ allow IP cụ thể nếu admin chỉ dùng nội bộ.

---

### 10.4. Quản lý biến môi trường

Hiện đang dùng:

```bash
ENV=prod
```

Nên cân nhắc dùng file `.env` hoặc khai báo trong systemd:

```ini
Environment="ENV=prod"
Environment="DATABASE_URL=..."
Environment="SECRET_KEY=..."
```

Không commit secret lên GitHub.

---

### 10.5. Reboot VPS khi có thời gian

Trong log có cảnh báo pending kernel upgrade. Không bắt buộc reboot ngay, nhưng nên reboot khi có thời gian rảnh:

```bash
sudo reboot
```

Sau reboot, kiểm tra:

```bash
sudo systemctl status wrydeco-temp-server
sudo systemctl status nginx
```

Vì cả hai service đã được enable, chúng sẽ tự chạy lại.

---

## 11. Checklist cuối cùng

Server được xem là deploy hoàn chỉnh khi các lệnh sau đều ổn:

```bash
sudo systemctl status wrydeco-temp-server
sudo systemctl status nginx
sudo nginx -t
curl http://127.0.0.1:8000/admin
curl -i https://vnote.io.vn/admin
```

Trạng thái hiện tại của setup này:

```txt
DNS:       OK
FastAPI:   OK
systemd:   OK
Nginx:     OK
HTTPS:     OK
Browser:   OK
```

---

## 12. Kết luận

Từ một project FastAPI nằm trên VPS, hiện hệ thống đã trở thành một backend server production cơ bản:

- Có domain public.
- Có reverse proxy Nginx.
- Có HTTPS hợp lệ.
- Có service chạy nền 24/7.
- Có khả năng tự chạy lại sau reboot.
- Browser/client đã gọi vào được endpoint `/admin` thành công.

Luồng hoạt động cuối cùng:

```txt
https://vnote.io.vn/admin
        ↓
Nginx SSL termination + reverse proxy
        ↓
http://127.0.0.1:8000/admin
        ↓
FastAPI app
        ↓
HTML Admin Manager Page
```

---

## 13. Restart server đúng cách sau khi pull code mới

Server FastAPI hiện đang chạy nền bằng `systemd` service:

```txt
wrydeco-temp-server.service
```

Không nên chạy lại server thủ công bằng:

```bash
python run.py
```

vì cách đó sẽ giữ terminal và không phù hợp cho production.

---

### 1. SSH vào VPS

```bash
ssh vmadmin@160.25.81.57
```

---

### 2. Đi vào thư mục project

```bash
cd /var/www/wrydeco-temp-server
```

---

### 3. Pull code mới nhất

```bash
git pull origin main
```

---

### 4. Đảm bảo quyền file đúng user deploy

```bash
sudo chown -R vmadmin:vmadmin /var/www/wrydeco-temp-server
```

---

### 5. Cài lại dependencies nếu có thay đổi `requirements.txt`

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 6. Restart FastAPI service

```bash
sudo systemctl restart wrydeco-temp-server
```

---

### 7. Kiểm tra trạng thái service

```bash
sudo systemctl status wrydeco-temp-server
```

Kết quả đúng cần thấy:

```txt
Active: active (running)
```

---

### 8. Test server nội bộ trên VPS

```bash
curl http://127.0.0.1:8000/admin
```

Nếu route `/admin` hoạt động, server sẽ trả về HTML admin page.

---

### 9. Test domain public HTTPS

```bash
curl -i https://vnote.io.vn/admin
```

Kết quả đúng cần có HTTP status `200 OK`.

---

### 10. Xem log nếu restart bị lỗi

Xem 100 dòng log gần nhất:

```bash
sudo journalctl -u wrydeco-temp-server -n 100 --no-pager
```

Xem log realtime:

```bash
sudo journalctl -u wrydeco-temp-server -f
```

Thoát log realtime:

```txt
Ctrl + C
```

---

### 11. Khi nào cần reload Nginx?

Chỉ cần reload Nginx nếu có sửa config Nginx, ví dụ file:

```txt
/etc/nginx/sites-available/vnote.io.vn
```

Khi đó chạy:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Nếu chỉ pull code FastAPI mới thì không cần reload Nginx.

---

## Lệnh rút gọn thường dùng

Sau khi đã pull code về, thường chỉ cần chạy:

```bash
cd /var/www/wrydeco-temp-server
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart wrydeco-temp-server
sudo systemctl status wrydeco-temp-server
```

---

## Ghi nhớ

Luồng production hiện tại là:

```txt
https://vnote.io.vn
        ↓
Nginx Reverse Proxy
        ↓
http://127.0.0.1:8000
        ↓
FastAPI / Uvicorn
        ↓
systemd service: wrydeco-temp-server
```

Vì vậy, cách restart đúng là restart service:

```bash
sudo systemctl restart wrydeco-temp-server
```
