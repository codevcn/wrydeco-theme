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
    
    # Fetch last 500 lines and grep for Exception, Error, Traceback, or 500
    stdin, stdout, stderr = ssh.exec_command("sudo -S journalctl -u shopify-admin-app.service -n 500 --no-pager | grep -i -E 'Exception|Traceback|Error|500'")
    stdin.write(password + '\n')
    stdin.flush()
    
    out = stdout.read().decode('utf-8')
    
    print("ERRORS FOUND:")
    print(out)
    
    ssh.close()
except Exception as e:
    print(f"LỖI: {e}")
