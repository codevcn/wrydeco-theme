import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

# Thông tin VPS mới
host = '20.89.43.225'
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
    ssh.exec_command(f"mkdir -p {app_dir}/templates {app_dir}/static {app_dir}/assets {app_dir}/backups {app_dir}/data")
    
    sftp = ssh.open_sftp()
    
    def upload_file(local_path, remote_path):
        print(f"Uploading {local_path} -> {remote_path}...")
        sftp.put(local_path, remote_path)
    
    # Upload main.py
    upload_file("main.py", f"{app_dir}/main.py")
    
    # Upload proxy_manager.py
    if os.path.exists("proxy_manager.py"):
        upload_file("proxy_manager.py", f"{app_dir}/proxy_manager.py")

    # Upload product_create_service.py
    if os.path.exists("product_create_service.py"):
        upload_file("product_create_service.py", f"{app_dir}/product_create_service.py")

    # Upload bulk product creation services & worker
    if os.path.exists("bulk_product_job_store.py"):
        upload_file("bulk_product_job_store.py", f"{app_dir}/bulk_product_job_store.py")

    if os.path.exists("bulk_product_job_service.py"):
        upload_file("bulk_product_job_service.py", f"{app_dir}/bulk_product_job_service.py")

    if os.path.exists("bulk_product_worker.py"):
        upload_file("bulk_product_worker.py", f"{app_dir}/bulk_product_worker.py")

    if os.path.exists("run_bulk_worker.py"):
        upload_file("run_bulk_worker.py", f"{app_dir}/run_bulk_worker.py")

    # Upload variant_manager_service.py
    if os.path.exists("variant_manager_service.py"):
        upload_file("variant_manager_service.py", f"{app_dir}/variant_manager_service.py")

    # Upload discount_manager_service.py
    if os.path.exists("discount_manager_service.py"):
        upload_file("discount_manager_service.py", f"{app_dir}/discount_manager_service.py")
    
    # Upload requirements.txt
    if os.path.exists("requirements.txt"):
        upload_file("requirements.txt", f"{app_dir}/requirements.txt")

    # Upload .env
    if os.path.exists(".env"):
        upload_file(".env", f"{app_dir}/.env")
    
    # Upload proxy_config.json
    if os.path.exists("proxy_config.json"):
        upload_file("proxy_config.json", f"{app_dir}/proxy_config.json")

    # Upload logo_updater_config.json
    if os.path.exists("logo_updater_config.json"):
        upload_file("logo_updater_config.json", f"{app_dir}/logo_updater_config.json")

    # Upload notes.json if not present on remote
    if os.path.exists("notes.json"):
        try:
            sftp.stat(f"{app_dir}/notes.json")
        except (FileNotFoundError, IOError):
            upload_file("notes.json", f"{app_dir}/notes.json")

    # Upload config.json if not present on remote
    if os.path.exists("config.json"):
        try:
            sftp.stat(f"{app_dir}/config.json")
        except (FileNotFoundError, IOError):
            upload_file("config.json", f"{app_dir}/config.json")
    
    # Upload templates
    for f in os.listdir("templates"):
        if f.endswith(".html"):
            upload_file(f"templates/{f}", f"{app_dir}/templates/{f}")
            
    # Upload static
    if os.path.exists("static"):
        for f in os.listdir("static"):
            if os.path.isfile(f"static/{f}"):
                upload_file(f"static/{f}", f"{app_dir}/static/{f}")

    # Upload assets
    if os.path.exists("assets"):
        for f in os.listdir("assets"):
            if os.path.isfile(f"assets/{f}"):
                upload_file(f"assets/{f}", f"{app_dir}/assets/{f}")

    sftp.close()
    print("Đã upload xong code.")

    # Cấu hình systemd unit cho bulk worker daemon
    worker_service_unit = """[Unit]
Description=WRYDECO Shopify Bulk Product Creation Worker Daemon
After=network.target shopify-admin-app.service

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/shopify-admin-app
ExecStart=/home/azureuser/shopify-admin-app/venv/bin/python3 /home/azureuser/shopify-admin-app/run_bulk_worker.py --daemon
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    print("Đang cấu hình shopify-bulk-product-worker.service...")
    setup_cmd = f"""
cat << 'EOF' | sudo tee /etc/systemd/system/shopify-bulk-product-worker.service > /dev/null
{worker_service_unit}
EOF
sudo systemctl daemon-reload
sudo systemctl enable shopify-bulk-product-worker.service
sudo systemctl restart shopify-admin-app.service
sudo systemctl restart shopify-bulk-product-worker.service
"""
    stdin, stdout, stderr = ssh.exec_command(setup_cmd)
    stdout.channel.recv_exit_status()

    # Kiểm tra trạng thái worker service
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active shopify-bulk-product-worker.service")
    worker_status = stdout.read().decode('utf-8').strip()
    print(f"Trạng thái shopify-bulk-product-worker.service: {worker_status}")

    # Khởi động lại dịch vụ chính
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active shopify-admin-app.service")
    app_status = stdout.read().decode('utf-8').strip()
    print(f"Trạng thái shopify-admin-app.service: {app_status}")
        
    ssh.close()

except Exception as e:
    print(f"LỖI: {e}")
