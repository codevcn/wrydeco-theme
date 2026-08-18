import os, paramiko
from dotenv import load_dotenv

load_dotenv('.vps.env')
host_user = os.getenv('VPS_SSH_CONNECT_COMMAND', '').strip("'")
password = os.getenv('VPS_SSH_CONNECT_PASSWORD', '').strip("'")
user, host = host_user.split('@', 1)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=15)

script = """
import os, requests, json
from dotenv import load_dotenv

load_dotenv('/home/vmadmin/shopify-admin-app/.env')
SHOPIFY_SHOP = os.getenv('SHOPIFY_SHOP', 'wrydeco')
SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2024-04')
token = os.getenv('SHOPIFY_ADMIN_TOKEN')
url = f'https://{SHOPIFY_SHOP}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json'
headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}

query1 = '''
query getArticles {
  articles(first: 5, sortKey: PUBLISHED_AT, reverse: true) {
    edges {
      node {
        id
        title
        isPublished
        publishedAt
        createdAt
        updatedAt
        image {
          url
        }
        blog {
          title
        }
      }
    }
  }
}
'''
res = requests.post(url, json={'query': query1}, headers=headers)
print(json.dumps(res.json(), indent=2))
"""

with open("temp_article_test.py", "w", encoding="utf-8") as f:
    f.write(script)

sftp = ssh.open_sftp()
sftp.put("temp_article_test.py", "temp_article_test.py")
sftp.close()

stdin, stdout, stderr = ssh.exec_command("/home/vmadmin/shopify-admin-app/venv/bin/python temp_article_test.py")
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
