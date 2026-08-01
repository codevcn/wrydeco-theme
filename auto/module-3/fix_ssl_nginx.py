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
            print(f"Lệnh thất bại (Exit {exit_status}): {err}")
            # Đừng throw error liền để certbot có cơ hội chạy nếu apt bị lỗi chút ít
        return out, err
        
    print("--- XÓA TRANG NGINX MẶC ĐỊNH ---")
    run_cmd("rm -f /etc/nginx/sites-enabled/default", use_sudo=True)
    run_cmd("systemctl reload nginx", use_sudo=True)
    
    print("\n--- CÀI ĐẶT CERTBOT & SSL ---")
    run_cmd("apt-get update", use_sudo=True)
    run_cmd("apt-get install -y certbot python3-certbot-nginx", use_sudo=True)
    
    # Chạy certbot
    print("\nĐang sinh chứng chỉ SSL tự động...")
    certbot_cmd = f"certbot --nginx -d {domain} --non-interactive --agree-tos -m admin@{domain} --redirect"
    out, err = run_cmd(certbot_cmd, use_sudo=True)
    
    if "Congratulations!" in out or "Successfully received certificate" in out or "Certificate not yet due for renewal" in out or "Deploying certificate" in out:
        print("\n===> CÀI ĐẶT SSL THÀNH CÔNG! <===")
    else:
        print("\n===> CÓ THỂ CÓ LỖI KHI CÀI SSL <===")
        print("Output:", out)
        print("Error:", err)
    
    ssh.close()
except Exception as e:
    print(f"LỖI: {e}")
    sys.exit(1)
