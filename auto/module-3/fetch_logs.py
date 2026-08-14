import os
import sys
import paramiko
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('.vps.env')
host_user = os.getenv('VPS_SSH_CONNECT_COMMAND', '').strip("'")
password = os.getenv('VPS_SSH_CONNECT_PASSWORD', '').strip("'")
user, host = host_user.split('@', 1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)

stdin, stdout, stderr = ssh.exec_command(f"echo '{password}' | sudo -S journalctl -u shopify-admin-app.service -n 50 --no-pager")
print(stdout.read().decode())
print(stderr.read().decode(), file=sys.stderr)
ssh.close()
