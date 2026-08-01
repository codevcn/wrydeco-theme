import os
import sys
import paramiko
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv('.vps.env')
host_user = os.getenv('VPS_SSH_CONNECT_COMMAND', '').strip("'")
password = os.getenv('VPS_SSH_CONNECT_PASSWORD', '').strip("'")

user, host = host_user.split('@', 1)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password, timeout=15)
    
    sftp = ssh.open_sftp()
    sftp.put(".env", f"/home/{user}/shopify-admin-app/.env")
    sftp.close()
    
    print("Đã upload file .env mới lên VPS.")
    
    # Khởi động lại service
    stdin, stdout, stderr = ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart shopify-admin-app.service")
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status == 0:
        print("Đã khởi động lại ứng dụng thành công!")
    else:
        print(f"Lỗi khi restart: {err}")
        
    ssh.close()
except Exception as e:
    print(f"LỖI: {e}")
