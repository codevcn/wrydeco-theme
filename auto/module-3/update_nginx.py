import os
import sys
import paramiko
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv('.vps.env')
host_user = os.getenv('VPS_SSH_CONNECT_COMMAND', '').strip("'")
password = os.getenv('VPS_SSH_CONNECT_PASSWORD', '').strip("'")

user, host = host_user.split('@', 1)
domain = "shopify.vnote.io.vn"

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Đang kết nối SSH đến {user}@{host}...")
    ssh.connect(host, username=user, password=password, timeout=15)
    print("Kết nối SSH thành công!\n")
    
    def run_cmd(cmd, use_sudo=False):
        if use_sudo:
            cmd = f"echo '{password}' | sudo -S {cmd}"
        print(f"> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            raise Exception(f"Lệnh thất bại: {err}")
        return out
        
    sftp = ssh.open_sftp()
    
    # Cấu hình Nginx mới
    nginx_content = f"""server {{
    listen 80;
    server_name {domain};

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
        
    sftp.put("shopify-admin-app.conf", f"/home/{user}/shopify-admin-app.conf")
    
    run_cmd(f"mv /home/{user}/shopify-admin-app.conf /etc/nginx/sites-available/shopify-admin-app.conf", use_sudo=True)
    run_cmd("nginx -t", use_sudo=True)
    run_cmd("systemctl reload nginx", use_sudo=True)
    
    sftp.close()
    ssh.close()
    
    print("\nĐã cập nhật Nginx thành công. Sẵn sàng nhận traffic từ domain!")
except Exception as e:
    print(f"LỖI: {e}")
    sys.exit(1)
