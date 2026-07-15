# API Documentation: Create Consultation

**Endpoint:** `POST /api/consultations`  
**Description:** API dùng để gửi yêu cầu tư vấn mới từ khách hàng, hỗ trợ kèm theo file đính kèm (hình ảnh, tài liệu).

---

## 1. Request Header
- `Content-Type`: `multipart/form-data`

---

## 2. Request Body (Form Data)
API yêu cầu dữ liệu gửi dưới dạng `multipart/form-data`.

### Các trường dữ liệu (Fields)

| Field name | Kiểu dữ liệu | Bắt buộc | Mô tả |
| :--- | :---: | :---: | :--- |
| `name` | `string` | **Có** | Tên của khách hàng. Phải tuân thủ giới hạn độ dài cho phép của hệ thống. |
| `phone_or_email` | `string` | **Có** | Số điện thoại hoặc địa chỉ email để liên hệ. Hệ thống sẽ tự động phân loại (classify) và chuẩn hóa thông tin này.<br>*(Lưu ý: Hỗ trợ fallback tương thích ngược thông qua việc đọc trường `email` hoặc `phone` nếu trường này trống).* |
| `message` | `string` | **Có** | Nội dung yêu cầu tư vấn ngắn từ khách hàng. Phải đáp ứng độ dài tối thiểu và tối đa. |
| `consultation_time` | `string` | Không | Lịch hẹn tư vấn dự kiến (tùy chọn). Nếu có, chuỗi sẽ được parse ra ngày và giờ ưu tiên (`preferred_date`, `preferred_time`). |

### Các file đính kèm (Attachments)
Bạn có thể đính kèm nhiều file trong request (các trường thuộc kiểu `File` có `filename`).

**Ràng buộc về File:**
- **Định dạng cho phép:** Chỉ chấp nhận `JPEG`, `PNG`, và `PDF`. (Hệ thống kiểm tra bằng MIME type sniffing thực tế, không chỉ dựa vào đuôi file).
- **Kích thước tối đa mỗi file:** 10 MB.
- **Tổng dung lượng tối đa:** 30 MB cho toàn bộ các file.
- **Số lượng file tối đa:** Được cấu hình bởi giới hạn hệ thống (ví dụ: tối đa 3-5 file).

---

## 3. Responses (Kết quả trả về)

API luôn trả về dữ liệu định dạng JSON.

### ✅ Thành công (201 Created)
Gửi yêu cầu tư vấn thành công.
```json
{
  "success": true
}
```

### ❌ Lỗi do định dạng Request (400 Bad Request)
Request không đúng chuẩn multipart/form-data.
```json
{
  "code": "MALFORMED_REQUEST",
  "message": "The multipart request is malformed."
}
```

### ❌ Lỗi xác thực dữ liệu (422 Unprocessable Entity)
Các trường thông tin không hợp lệ, bị bỏ trống, hoặc sai định dạng.
```json
{
  "code": "VALIDATION_ERROR",
  "message": "The consultation request contains invalid fields.",
  "errors": [
    {
      "field": "name",
      "code": "REQUIRED",
      "message": "Name is required."
    },
    {
      "field": "phone_or_email",
      "code": "INVALID_CONTACT",
      "message": "Enter a valid phone number or email address."
    }
  ]
}
```
*(Các mã lỗi `errors` chi tiết có thể gồm: `REQUIRED`, `INVALID_LENGTH`, `INVALID_CONTACT`...)*

### ❌ Lỗi về File upload (413 Payload Too Large)
Khi số lượng hoặc kích thước file vượt quá giới hạn.
- Vượt số lượng file: `TOO_MANY_FILES` ("At most X files are allowed.")
- File quá lớn: `FILE_TOO_LARGE` ("Each file must be at most 10MB.")
- Tổng dung lượng quá lớn: `REQUEST_TOO_LARGE` ("Total upload size exceeds 30MB.")

```json
{
  "code": "FILE_TOO_LARGE",
  "message": "Each file must be at most 10MB."
}
```

### ❌ Lỗi định dạng File không hỗ trợ (415 Unsupported Media Type)
Khi đính kèm file không phải là ảnh JPEG/PNG hoặc PDF.
```json
{
  "code": "UNSUPPORTED_FILE_TYPE",
  "message": "Only JPEG, PNG and PDF files are allowed."
}
```

### ❌ Lỗi máy chủ (500 Internal Server Error)
Có lỗi phát sinh trong quá trình lưu dữ liệu xuống Database hoặc lưu file vào ổ cứng.
```json
{
  "code": "INTERNAL_ERROR",
  "message": "Could not save the consultation request."
}
```
