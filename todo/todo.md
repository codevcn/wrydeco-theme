Field:

```text
[DKIM_PUBLIC_KEY_DO_CODE_VCN_CUNG_CAP]
```

là **public key DKIM được tạo sẵn trên VPS** khi bạn chạy lệnh tạo DKIM cho `chillgen.com`.

Nó nằm trong file:

```bash
/opt/mailserver/docker-data/dms/config/opendkim/keys/chillgen.com/mail.txt
```

SSH vào VPS rồi chạy:

```bash
sudo cat /opt/mailserver/docker-data/dms/config/opendkim/keys/chillgen.com/mail.txt
```

Kết quả thường có dạng:

```text
mail._domainkey IN TXT (
  "v=DKIM1; k=rsa; "
  "p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."
)
```

Bạn cần ghép toàn bộ phần nằm trong dấu ngoặc kép thành **một dòng duy nhất**, ví dụ:

```text
v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...
```

Sau đó gửi leader điền vào DNS:

```text
Type: TXT
Name: mail._domainkey
Value: v=DKIM1; k=rsa; p=...
```

Có thể lấy nhanh public key một dòng bằng lệnh:

```bash
sudo sed -n '/mail._domainkey/,/)/p' \
  /opt/mailserver/docker-data/dms/config/opendkim/keys/chillgen.com/mail.txt \
  | grep -o '"[^"]*"' \
  | tr -d '"\n'
```

Kiểm tra kết quả sau khi leader thêm DNS:

```bash
dig +short TXT mail._domainkey.chillgen.com
```

Hoặc:

```bash
nslookup -type=TXT mail._domainkey.chillgen.com
```

Lưu ý quan trọng: chỉ gửi **public key** trong file `mail.txt`. Không gửi hoặc công khai file private key như:

```text
mail.private
```

Vị trí file và quy trình lấy DKIM này đã được ghi trong kế hoạch triển khai mail server. 

### DKIM Public Key (Extracted)
```text
v=DKIM1; h=sha256; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkDZwv8dgCulB2Mj8ZUckR7L1TH/dDAAaFpOljzy0MGB52k4OzB3puR1D3fWC8voVxcG3bpkMOYYuFhxnU4kkdDyR9HbIsMdNsrh1HxD/XoTrj+uKAzjSvuhPnCde2z4+KRhCfoi08+Vsv5tlO7FD4K9+bv1SAQz9aPMJIN6bV6pnf5L4LVfeYcM47O0+jTdjgjINHW2p6M9Ara6VsV00AFT0G5V834sl0d8C0ufypTCNb6BQjbkJ5GIZLMFEIgtmW4dbobwI3aqWX1Dov5ivMxQbqoa8yGuhUCLKI3qEi99Q7/aGqgOlt6fCOkULwN3G0uSJvBIxBtVkTvy471x8EQIDAQAB
```
