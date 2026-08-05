import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("160.25.81.57", username="vmadmin", password="F8_OwEyj_Cod")
stdin, stdout, stderr = ssh.exec_command("sudo -S journalctl -u shopify-admin-app.service -n 100 --no-pager")
stdin.write("F8_OwEyj_Cod\n")
stdin.flush()
print(stdout.read().decode())
print(stderr.read().decode())
