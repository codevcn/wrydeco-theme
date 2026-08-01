import os
import sys
import paramiko
from dotenv import load_dotenv
import traceback

sys.stdout.reconfigure(encoding='utf-8')

# Ensure logs dir exists
os.makedirs('logs', exist_ok=True)
os.makedirs('doc', exist_ok=True)
log_file = open('logs/vps-ssh.log', 'w', encoding='utf-8')
report_file_path = 'doc/agent-deploy-report.md'

def log(msg):
    print(msg)
    log_file.write(msg + '\n')
    log_file.flush()

def write_report(success, message):
    with open(report_file_path, 'w', encoding='utf-8') as f:
        f.write("# Báo Cáo Triển Khai (Deploy Report)\n\n")
        if success:
            f.write("## Trạng Thái: THÀNH CÔNG ✅\n\n")
        else:
            f.write("## Trạng Thái: THẤT BẠI ❌\n\n")
        f.write(message + "\n\n")
        f.write("Vui lòng xem chi tiết log trong file `logs/vps-ssh.log`.\n")

load_dotenv('.vps.env')
host_user = os.getenv('VPS_SSH_CONNECT_COMMAND', '').strip("'")
password = os.getenv('VPS_SSH_CONNECT_PASSWORD', '').strip("'")

if not host_user or '@' not in host_user:
    log("Invalid VPS_SSH_CONNECT_COMMAND")
    write_report(False, "Thiếu thông tin kết nối SSH trong `.vps.env`.")
    sys.exit(1)

user, host = host_user.split('@', 1)

try:
    log(f"--- Bắt đầu deploy lên {host} ---")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    log(f"Đang kết nối SSH đến {user}@{host}...")
    ssh.connect(host, username=user, password=password, timeout=15)
    log("Kết nối SSH thành công!\n")
    
    def run_cmd(cmd, use_sudo=False):
        # Tránh prompt hỏi password bằng cách truyền qua stdin
        if use_sudo:
            cmd = f"echo '{password}' | sudo -S {cmd}"
        log(f"> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        exit_status = stdout.channel.recv_exit_status()
        if out: log(out.strip())
        if err: log("STDERR: " + err.strip())
        log(f"[Exit Code: {exit_status}]\n")
        if exit_status != 0:
            # Lọc password khỏi log lỗi để bảo mật
            clean_err = err.replace(password, '***')
            raise Exception(f"Lệnh thất bại với exit code {exit_status}:\n{clean_err}")
        return out
        
    # Bước 1 & 2: Tạo thư mục và upload code
    app_dir = f"/home/{user}/shopify-admin-app"
    log("--- BƯỚC 1 & 2: TẠO THƯ MỤC VÀ UPLOAD CODE ---")
    run_cmd(f"mkdir -p {app_dir}")
    run_cmd(f"mkdir -p {app_dir}/templates")
    
    sftp = ssh.open_sftp()
    
    def upload_file(local_path, remote_path):
        log(f"Uploading {local_path} -> {remote_path}...")
        sftp.put(local_path, remote_path)
        
    upload_file("main.py", f"{app_dir}/main.py")
    upload_file("clean.py", f"{app_dir}/clean.py")
    upload_file("get_access_token.py", f"{app_dir}/get_access_token.py")
    upload_file("requirements.txt", f"{app_dir}/requirements.txt")
    if os.path.exists(".env"):
        upload_file(".env", f"{app_dir}/.env")
    
    for f in os.listdir("templates"):
        if f.endswith(".html"):
            upload_file(f"templates/{f}", f"{app_dir}/templates/{f}")
            
    log("\n--- BƯỚC 3: CÀI ĐẶT MÔI TRƯỜNG VENV ---")
    run_cmd(f"cd {app_dir} && python3 -m venv venv")
    run_cmd(f"cd {app_dir} && venv/bin/pip install -r requirements.txt")
    
    log("\n--- BƯỚC 4: THIẾT LẬP SYSTEMD SERVICE ---")
    service_content = f"""[Unit]
Description=Shopify Admin App FastAPI
After=network.target

[Service]
User={user}
WorkingDirectory={app_dir}
ExecStart={app_dir}/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8085
Restart=always

[Install]
WantedBy=multi-user.target
"""
    with open("shopify-admin-app.service", "w", encoding='utf-8') as f:
        f.write(service_content)
    upload_file("shopify-admin-app.service", f"/home/{user}/shopify-admin-app.service")
    run_cmd(f"mv /home/{user}/shopify-admin-app.service /etc/systemd/system/shopify-admin-app.service", use_sudo=True)
    run_cmd("systemctl daemon-reload", use_sudo=True)
    run_cmd("systemctl enable shopify-admin-app.service", use_sudo=True)
    run_cmd("systemctl restart shopify-admin-app.service", use_sudo=True)
    
    log("\n--- BƯỚC 5: CẤU HÌNH NGINX ---")
    # Sử dụng port 8086 an toàn để không đụng độ các web khác
    nginx_content = f"""server {{
    listen 8086;
    server_name _;

    location / {{
        proxy_pass http://127.0.0.1:8085;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    with open("shopify-admin-app.conf", "w", encoding='utf-8') as f:
        f.write(nginx_content)
    upload_file("shopify-admin-app.conf", f"/home/{user}/shopify-admin-app.conf")
    run_cmd(f"mv /home/{user}/shopify-admin-app.conf /etc/nginx/sites-available/shopify-admin-app.conf", use_sudo=True)
    run_cmd("ln -sf /etc/nginx/sites-available/shopify-admin-app.conf /etc/nginx/sites-enabled/", use_sudo=True)
    run_cmd("nginx -t", use_sudo=True)
    run_cmd("systemctl reload nginx", use_sudo=True)
    
    sftp.close()
    ssh.close()
    
    log("\n=== DEPLOY HOÀN TẤT THÀNH CÔNG ===")
    write_report(True, f"Đã thực thi toàn bộ script deploy thành công lên server.\n\n**Ứng dụng đã online tại port 8086**.\nBạn có thể truy cập qua: `http://{host}:8086/`")
    
except Exception as e:
    err_msg = traceback.format_exc()
    log(f"\nLỖI NGHIÊM TRỌNG: {e}\n{err_msg}")
    write_report(False, f"Gặp lỗi trong quá trình thực thi deploy.\n\nChi tiết lỗi:\n```\n{e}\n```\n\nVui lòng xem thêm file `logs/vps-ssh.log` để biết chính xác lệnh nào đã gây ra lỗi.")
    sys.exit(1)
