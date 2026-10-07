import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

host = '20.222.21.81'
user = 'azureuser'
ssh_alias = 'wrydeco-vps'

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
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
    
    ssh.connect(
        hostname=host, 
        username=user, 
        key_filename=key_filename, 
        timeout=15,
        look_for_keys=True,
        allow_agent=True
    )
    
    stdin, stdout, stderr = ssh.exec_command("sudo journalctl -u shopify-admin-app.service -n 100 --no-pager")
    print(stdout.read().decode('utf-8', errors='replace'))
    err = stderr.read().decode('utf-8', errors='replace')
    if err:
        print("STDERR:", err)
    ssh.close()
except Exception as e:
    print(f"Lỗi: {e}")
