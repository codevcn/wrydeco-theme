Đã tạo xong 2 file:

- [update_products.py](D:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/todo/SEO/update_products.py)
- [update_config.json](D:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/todo/SEO/update_config.json)

Script hiện tại làm đúng hướng an toàn:

- Đọc cấu hình từ `update_config.json`
- Match product bằng `Handle`
- Update mặc định 3 field:
  - `Final H1 / Product Title` -> `Title`
  - `Final SEO Title` -> `SEO Title`
  - `Final Meta Description` -> `SEO Description`
- Không sửa `Product Type` / `Type`
- Không sửa `Body (HTML)`
- Không sửa variant, price, inventory, image, tags, metafields
- Tạo `update_report.csv`
- Tạo `qa_report.txt`
- Tạo `shopify_import.csv` cùng cấu trúc header với file backup, chỉ chứa rows của các handles đã chọn

Mình cũng để config mặc định:

```json
"dry_run": true,
"handles_in_csv_to_update": []
```

Nên nếu chạy ngay thì script fail an toàn vì chưa có handle nào. Đã kiểm tra cú pháp Python pass bằng `py_compile`, và chạy config mặc định cho ra lỗi an toàn:

```text
ERROR: handles_in_csv_to_update is empty. Add at least one handle before running.
```

Khi muốn dùng, bạn chỉ cần điền handles vào `handles_in_csv_to_update`. Nếu muốn ghi thật vào file backup thì đổi:

```json
"dry_run": false
```