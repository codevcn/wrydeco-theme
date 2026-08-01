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
    sftp.put("main.py", f"/home/{user}/shopify-admin-app/main.py")
    sftp.close()
    
    print("Đã upload main.py mới lên VPS.")
    
    stdin, stdout, stderr = ssh.exec_command(f"echo '{password}' | sudo -S systemctl restart shopify-admin-app.service")
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status == 0:
        print("Đã khởi động lại ứng dụng thành công!")
    else:
        print(f"Lỗi: {stderr.read().decode()}")
        
    ssh.close()
except Exception as e:
    print(f"LỖI: {e}")
