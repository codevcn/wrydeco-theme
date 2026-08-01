import paramiko
import os
import sys
from dotenv import load_dotenv

load_dotenv('.vps.env')
host_user = os.getenv('VPS_SSH_CONNECT_COMMAND', '').strip("'")
password = os.getenv('VPS_SSH_CONNECT_PASSWORD', '').strip("'")

if not host_user or '@' not in host_user:
    print("Invalid VPS_SSH_CONNECT_COMMAND")
    sys.exit(1)

user, host = host_user.split('@', 1)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host} as {user}...")
    ssh.connect(host, username=user, password=password, timeout=10)
    print("Connection successful!")
    stdin, stdout, stderr = ssh.exec_command('uptime')
    print("Uptime:", stdout.read().decode('utf-8').strip())
    
    stdin, stdout, stderr = ssh.exec_command('lsb_release -a || cat /etc/os-release')
    os_info = stdout.read().decode('utf-8').strip()
    print("OS Info:\n" + os_info)
    
    ssh.close()
except Exception as e:
    print(f"Failed to connect: {e}")
