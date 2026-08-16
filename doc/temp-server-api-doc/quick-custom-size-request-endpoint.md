# Yêu cầu Tùy chỉnh Kích thước (Custom Size Requests)

Tài liệu này mô tả chi tiết endpoint xử lý tính năng "Quick Custom Size Request" để khách hàng có thể gửi yêu cầu tùy chỉnh kích thước sản phẩm nhanh chóng từ website.

## `POST /api/custom-size-requests`

Endpoint này nhận dữ liệu cấu trúc dạng `FormData` trên website và lưu trữ vào cơ sở dữ liệu để đội ngũ sản xuất xử lý.

### Input

**Content-Type:** `multipart/form-data`

| Field                     | Kiểu | Bắt buộc | Mô tả                                                  |
| ------------------------- | ---- | :------: | ------------------------------------------------------ |
| `product_id`              | text |    ✅    | ID của sản phẩm mà khách hàng muốn tùy chỉnh           |
| `product_handle`          | text |    ✅    | Handle (đường dẫn thân thiện) của sản phẩm             |
| `product_name`            | text |    ✅    | Tên sản phẩm                                           |
| `custom_size_description` | text |    ✅    | Mô tả kích thước tùy chỉnh mà khách hàng muốn          |
| `customer_contact`        | text |    ✅    | Email hoặc số điện thoại của khách hàng để liên hệ lại |

### Output — `201 Created`

**Content-Type:** `application/json`

| Field     | Kiểu    | Mô tả                                |
| --------- | ------- | ------------------------------------ |
| `success` | boolean | Luôn `true` khi lưu thành công       |
| `id`      | integer | ID của request vừa được tạo trong DB |
| `message` | string  | `"Custom size request received."`    |

```json
{
  "success": true,
  "id": 1,
  "message": "Custom size request received."
}
```

### Output lỗi — `422 Unprocessable Entity`

Trả về khi dữ liệu đầu vào không hợp lệ hoặc thiếu field bắt buộc (`product_id`, `product_handle`, `product_name`, `custom_size_description`, hoặc `customer_contact`).

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "The request contains invalid fields.",
  "errors": [
    {
      "field": "product_id",
      "code": "REQUIRED",
      "message": "Product ID is required."
    }
  ]
}
```

### Ví dụ (JavaScript / fetch)

```javascript
const formData = new FormData();
formData.append("product_id", "123456789");
formData.append("product_handle", "ao-thun-nam");
formData.append("product_name", "Áo thun nam Wrydeco");
formData.append("custom_size_description", "Cần tay áo dài thêm 2cm, ngực rộng thêm 1cm");
formData.append("customer_contact", "khachhang@example.com");

const res = await fetch("https://vnote.io.vn/api/custom-size-requests", {
  method: "POST",
  body: formData,
});
const data = await res.json(); // { success, id, message }
```
