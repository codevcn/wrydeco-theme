import os, paramiko
from dotenv import load_dotenv

load_dotenv('.vps.env')
host_user = os.getenv('VPS_SSH_CONNECT_COMMAND', '').strip("'")
password = os.getenv('VPS_SSH_CONNECT_PASSWORD', '').strip("'")
user, host = host_user.split('@', 1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)
sftp = ssh.open_sftp()
sftp.get(f'/home/{user}/shopify-admin-app/main.py', 'main_remote.py')
sftp.close()
ssh.close()
