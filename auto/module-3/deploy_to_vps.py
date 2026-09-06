import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

# Thông tin VPS mới
host = '20.222.21.81'
user = 'azureuser'
ssh_alias = 'wrydeco-vps'

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Tự động đọc config từ file ~/.ssh/config (nếu có sử dụng alias wrydeco-vps)
    key_filename = None
    ssh_config_file = os.path.expanduser("~/.ssh/config")
    if os.path.exists(ssh_config_file):
        config = paramiko.SSHConfig()
        with open(ssh_config_file, encoding='utf-8') as f:
            config.parse(f)
        host_config = config.lookup(ssh_alias)
        if host_config:
            if 'hostname' in host_config:
                host = host_config['hostname']
            if 'user' in host_config:
                user = host_config['user']
            if 'identityfile' in host_config:
                key_filename = host_config['identityfile']
    
    print(f"Đang kết nối tới {user}@{host} bằng SSH Key...")
    ssh.connect(
        hostname=host, 
        username=user, 
        key_filename=key_filename, 
        timeout=15,
        look_for_keys=True,
        allow_agent=True
    )
    print("Kết nối thành công. Đang tải code lên...")
    
    app_dir = f"/home/{user}/shopify-admin-app"
    ssh.exec_command(f"mkdir -p {app_dir}/templates {app_dir}/static")
    
    sftp = ssh.open_sftp()
    
    def upload_file(local_path, remote_path):
        print(f"Uploading {local_path} -> {remote_path}...")
        sftp.put(local_path, remote_path)
    
    # Upload main.py
    upload_file("main.py", f"{app_dir}/main.py")
    
    # Upload templates
    for f in os.listdir("templates"):
        if f.endswith(".html"):
            upload_file(f"templates/{f}", f"{app_dir}/templates/{f}")
            
    # Upload static
    if os.path.exists("static"):
        for f in os.listdir("static"):
            if os.path.isfile(f"static/{f}"):
                upload_file(f"static/{f}", f"{app_dir}/static/{f}")

    sftp.close()
    print("Đã upload xong code.")
    
    # Khởi động lại dịch vụ
    print("Đang khởi động lại dịch vụ (dùng sudo không cần mật khẩu cho azureuser)...")
    stdin, stdout, stderr = ssh.exec_command(f"sudo systemctl restart shopify-admin-app.service")
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status == 0:
        print("Đã khởi động lại ứng dụng thành công!")
    else:
        err_msg = stderr.read().decode('utf-8')
        print(f"Lỗi khởi động dịch vụ: {err_msg}")
        
    ssh.close()

except Exception as e:
    print(f"LỖI: {e}")
