# WRYDECO Consultation Form — Backend API Requirements

## 1. Mục đích

Tài liệu này là contract mới nhất để backend triển khai API cho consultation form tại:

```text
/pages/customization
```

Form dùng để tiếp nhận lead cho dịch vụ tư vấn thiết kế và bespoke commission của
WRYDECO. Đây là luồng lead-generation cho một thương hiệu nội thất gỗ tự nhiên thủ công
cao cấp, vì vậy backend cần lưu dữ liệu an toàn, thông báo cho đội ngũ tư vấn và hỗ trợ
theo dõi lead sau khi khách gửi yêu cầu.

> Tài liệu này thay thế contract consultation cũ nếu có khác biệt với
> `doc/Wrydeco-Shopify-Consultation-Server-API.md`.

## 2. Tổng quan nghiệp vụ

Consultation form mới được tối giản để giảm friction. Khách chỉ cần cung cấp ba thông tin
bắt buộc:

1. Name.
2. Phone or email — khách được quyền nhập một trong hai phương thức liên hệ.
3. Short request.

Ngoài ba field trên, khách có thể tùy chọn:

- Chọn thời gian tư vấn online mong muốn.
- Đính kèm ảnh hoặc PDF mô tả không gian/dự án.

Mỗi lần submit hợp lệ phải tạo một consultation lead. Backend phải lưu được lead ngay cả
khi khách không chọn lịch và không gửi attachment.

## 3. Endpoint

Endpoint mặc định:

```http
POST https://vnote.io.vn/api/consultations
Content-Type: multipart/form-data; boundary=...
```

Endpoint có thể được thay đổi trong Shopify Theme Editor qua setting `api_endpoint` của
section `customization-consultation`.

Frontend dùng JavaScript `FormData`. Không được yêu cầu frontend tự set `Content-Type`, vì
browser phải tự tạo multipart boundary.

## 4. Request contract

### 4.1 Fields

| Field               | Kiểu   | Bắt buộc | Mô tả                                                                    |
| ------------------- | ------ | :------: | ------------------------------------------------------------------------ |
| `name`              | text   |    Có    | Họ tên khách hàng.                                                       |
| `phone_or_email`    | text   |    Có    | Một số điện thoại hoặc một địa chỉ email. Frontend dùng `type="text"`.   |
| `message`           | text   |    Có    | Short request về dự án, không gian, sản phẩm hoặc nhu cầu tư vấn.        |
| `consultation_time` | text   |  Không   | Preferred consultation time. Frontend gửi chuỗi rỗng nếu chưa chọn lịch. |
| `file`              | binary |  Không   | Attachment; key này có thể xuất hiện nhiều lần trong cùng request.       |

Frontend không còn gửi hai field `email` và `phone` riêng biệt. Backend mới phải đọc field
`phone_or_email`.

### 4.2 Ví dụ payload đầy đủ

```text
name=Jane Smith
phone_or_email=jane@example.com
message=I would like a sculptural console designed for my entryway.
consultation_time=01:55 PM, 15/07/2026
file=<entryway.jpg>
file=<floor-plan.pdf>
```

### 4.3 Ví dụ payload tối thiểu

```text
name=Jane Smith
phone_or_email=+1 415 555 0198
message=Please contact me about a custom dining table.
consultation_time=
```

`consultation_time` hiện luôn được frontend append. Backend vẫn nên coi field bị thiếu và
field có chuỗi rỗng là cùng một trường hợp để tương thích khi deploy.

## 5. Validation bắt buộc

Backend phải validate lại toàn bộ request. Không được tin validation phía browser.

### 5.1 `name`

- Bắt buộc.
- Trim whitespace.
- Không chấp nhận chuỗi chỉ có whitespace.
- Độ dài đề xuất: 2–255 ký tự.
- Lưu dưới dạng plain text và escape khi render trong HTML/email.

### 5.2 `phone_or_email`

- Bắt buộc.
- Kiểu string; không ép sang integer.
- Trim whitespace.
- Không chấp nhận chuỗi chỉ có whitespace.
- Tối đa 320 ký tự.
- Backend phải xác định input là email hay phone.

Quy tắc phân loại đề xuất:

1. Nếu input có cấu trúc email hợp lệ, normalize domain về lowercase và lưu
   `contact_type=email`.
2. Nếu không phải email, thử parse như số điện thoại; cho phép `+`, khoảng trắng, dấu
   ngoặc, dấu chấm và dấu gạch ngang; lưu `contact_type=phone`.
3. Nếu không hợp lệ ở cả hai dạng, trả `422` cho field `phone_or_email`.

Không được yêu cầu khách phải cung cấp đồng thời cả email và phone.

Backend nên lưu:

- `contact_value_raw`: giá trị khách nhập sau khi trim.
- `contact_type`: `email` hoặc `phone`.
- `contact_value_normalized`: email/phone đã normalize để tìm kiếm và chống duplicate.

### 5.3 `message`

- Bắt buộc.
- Trim whitespace.
- Không chấp nhận chuỗi chỉ có whitespace.
- Độ dài đề xuất: 10–10.000 ký tự.
- Lưu plain text; không render trực tiếp thành HTML chưa escape.

## 6. Optional scheduler

### 6.1 Ý nghĩa nghiệp vụ

Scheduler là optional. Khách có thể submit form mà không chọn lịch.

Thời gian khách chọn chỉ là **preferred consultation time**, chưa phải booking đã được
WRYDECO xác nhận vì frontend hiện:

- Không gọi API availability.
- Không khóa slot.
- Không gửi timezone.

Backend không được tự động đặt trạng thái `schedule_confirmed`. Đội ngũ tư vấn cần xác
nhận availability và timezone với khách qua phương thức liên hệ trong `phone_or_email`.

### 6.2 Format

Giá trị hợp lệ:

```text
hh:mm AM|PM, dd/mm/yyyy
```

Ví dụ:

```text
09:00 AM, 12/07/2026
01:55 PM, 15/07/2026
```

Quy tắc:

- `hh`: `01`–`12`.
- `mm`: `00`–`55`, chia hết cho 5.
- Period: chỉ `AM` hoặc `PM`.
- Date phải tồn tại thực tế.
- Ngày đã qua phải bị từ chối.
- Chuỗi rỗng hoặc field bị thiếu nghĩa là không yêu cầu lịch.

Backend nên lưu:

- `consultation_time_raw`: raw string.
- `preferred_date`: nullable `DATE`.
- `preferred_time`: nullable `TIME`.
- `timezone`: nullable; frontend chưa cung cấp.
- `schedule_status`: `not_requested`, `requested`, `confirmed`, `reschedule_required` hoặc
  `cancelled`.

Không convert preferred time sang UTC khi timezone chưa được xác nhận.

## 7. Optional attachments

Frontend gửi mỗi attachment bằng cùng key:

```text
file
```

Một request có thể có nhiều part tên `file`.

Loại file frontend cho phép:

- `.jpg`
- `.jpeg`
- `.png`
- `.pdf`

Frontend giới hạn 10 MB cho mỗi file. Backend bắt buộc phải áp dụng lại validation này.

Yêu cầu backend:

1. Nhận zero, one hoặc multiple `file` parts.
2. Giới hạn 10 MB/file.
3. Khuyến nghị tối đa 10 file và 30 MB/request.
4. Chỉ chấp nhận MIME đã xác minh: `image/jpeg`, `image/png`, `application/pdf`.
5. Kiểm tra magic bytes/file signature, không chỉ tin extension và request MIME.
6. Sinh storage key bằng UUID/secure random; không dùng filename gốc làm path.
7. Lưu original filename đã sanitize, MIME, size và checksum.
8. Không public directory listing.
9. Download trong admin phải yêu cầu authentication hoặc signed URL có thời hạn.
10. Nên quét malware trước khi nhân viên tải file.

Nếu một attachment không hợp lệ, toàn request nên thất bại atomically; không tạo lead nửa
chừng hoặc orphan file.

## 8. Lead và schedule status

Trạng thái ban đầu:

- Không có lịch: `lead_status=new`, `schedule_status=not_requested`.
- Có lịch: `lead_status=new`, `schedule_status=requested`.

Các trạng thái lead có thể hỗ trợ:

- `new`
- `contacted`
- `qualified`
- `closed_won`
- `closed_lost`
- `spam`

Các trạng thái schedule:

- `not_requested`
- `requested`
- `confirmed`
- `reschedule_required`
- `cancelled`

## 9. Response contract

Frontend hiện chỉ kiểm tra `response.ok`; response JSON chưa được đọc. Backend vẫn cần
trả JSON ổn định để logging, admin và tích hợp sau này.

### 9.1 Thành công

Status: `201 Created`.

Không có lịch:

```json
{
  "success": true,
  "id": "con_01J...",
  "lead_status": "new",
  "schedule_status": "not_requested",
  "message": "Consultation request received."
}
```

Có lịch:

```json
{
  "success": true,
  "id": "con_01J...",
  "lead_status": "new",
  "schedule_status": "requested",
  "message": "Consultation request received."
}
```

### 9.2 Validation error

Status: `422 Unprocessable Entity`.

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "The consultation request contains invalid fields.",
  "errors": [
    {
      "field": "phone_or_email",
      "code": "INVALID_CONTACT",
      "message": "Enter a valid phone number or email address."
    }
  ]
}
```

### 9.3 HTTP statuses

| Status | Trường hợp                                          |
| ------ | --------------------------------------------------- |
| `201`  | Lead và optional attachments được lưu thành công.   |
| `400`  | Multipart request malformed.                        |
| `413`  | File hoặc request vượt giới hạn.                    |
| `415`  | File type không được hỗ trợ.                        |
| `422`  | Required field, contact hoặc schedule không hợp lệ. |
| `429`  | Vượt rate limit/spam threshold.                     |
| `500`  | Lỗi nội bộ; không để lộ stack trace/storage path.   |

## 10. Data model đề xuất

### 10.1 `consultation_requests`

| Column                     | Kiểu gợi ý   | Nullable | Ghi chú                           |
| -------------------------- | ------------ | :------: | --------------------------------- |
| `id`                       | UUID/ULID    |  Không   | Lead identifier.                  |
| `name`                     | varchar(255) |  Không   | Name đã trim.                     |
| `contact_value_raw`        | varchar(320) |  Không   | `phone_or_email` khách nhập.      |
| `contact_type`             | enum         |  Không   | `phone` hoặc `email`.             |
| `contact_value_normalized` | varchar(320) |  Không   | Dùng để liên hệ/tìm kiếm/dedupe.  |
| `message`                  | text         |  Không   | Short request.                    |
| `consultation_time_raw`    | varchar(64)  |    Có    | Raw optional schedule string.     |
| `preferred_date`           | date         |    Có    | Null nếu không chọn lịch.         |
| `preferred_time`           | time         |    Có    | Null nếu không chọn lịch.         |
| `timezone`                 | varchar(64)  |    Có    | Chưa có từ frontend.              |
| `lead_status`              | enum/varchar |  Không   | Mặc định `new`.                   |
| `schedule_status`          | enum/varchar |  Không   | `not_requested` hoặc `requested`. |
| `source`                   | varchar(64)  |  Không   | `shopify_customization_page`.     |
| `created_at`               | timestamptz  |  Không   | UTC.                              |
| `updated_at`               | timestamptz  |  Không   | UTC.                              |
| `contacted_at`             | timestamptz  |    Có    | SLA/CRM tracking.                 |

### 10.2 `consultation_attachments`

| Column               | Kiểu gợi ý   | Nullable | Ghi chú                         |
| -------------------- | ------------ | :------: | ------------------------------- |
| `id`                 | UUID/ULID    |  Không   | Attachment ID.                  |
| `consultation_id`    | FK           |  Không   | Parent consultation.            |
| `original_file_name` | varchar(512) |  Không   | Chỉ dùng hiển thị.              |
| `storage_key`        | varchar(512) |  Không   | Secure generated key.           |
| `mime_type`          | varchar(128) |  Không   | MIME đã xác minh.               |
| `size_bytes`         | bigint       |  Không   | File size thực tế.              |
| `checksum`           | varchar(128) |    Có    | Khuyến nghị SHA-256.            |
| `scan_status`        | enum/varchar |  Không   | `pending`, `clean`, `rejected`. |
| `created_at`         | timestamptz  |  Không   | UTC.                            |

## 11. Xử lý sau khi nhận lead

### 11.1 Notification nội bộ

Gửi email/CRM notification cho đội ngũ WRYDECO gồm:

- Lead ID.
- Name.
- Contact value và contact type.
- Short request.
- Preferred consultation time hoặc `Not requested`.
- Cảnh báo timezone chưa xác nhận nếu khách chọn lịch.
- Secure attachment links.
- Source và created timestamp.

Không attach trực tiếp file lớn vào email.

### 11.2 Phản hồi cho khách

- Nếu contact type là email, backend có thể gửi acknowledgement email tự động.
- Nếu contact type là phone, tạo task/notification để nhân viên gọi hoặc nhắn khách.
- Nếu có preferred time, nội dung phản hồi phải nói rõ WRYDECO sẽ xác nhận availability và
  timezone; không khẳng định lịch đã được đặt thành công.

## 12. CORS và security

API được gọi cross-origin từ Shopify storefront. Backend phải:

1. Whitelist production storefront origin cụ thể.
2. Cho phép `POST`, `OPTIONS`, `Content-Type`, `Accept`.
3. Chỉ whitelist `http://127.0.0.1:9292`/`http://localhost:9292` trong development.
4. Không dùng wildcard origin lỏng lẻo trong production.
5. Rate limit, ví dụ 5 request/10 phút/IP.
6. Chống duplicate do double submit/network retry bằng fingerprint trong cửa sổ 1–2 phút.
7. Escape dữ liệu khi render admin/email để chống stored XSS.
8. Không log đầy đủ contact value, message hoặc file content.
9. Bảo vệ admin/download bằng authentication và authorization.
10. Dùng HTTPS và không trả internal error detail ra storefront.
11. Có retention, deletion/export và backup policy phù hợp Privacy Policy.

## 13. Ví dụ cURL

### 13.1 Contact bằng email, có lịch và attachments

```bash
curl -X POST "https://vnote.io.vn/api/consultations" \
  -F "name=Jane Smith" \
  -F "phone_or_email=jane@example.com" \
  -F "message=I would like a sculptural console designed for my entryway." \
  -F "consultation_time=01:55 PM, 15/07/2026" \
  -F "file=@./entryway.jpg;type=image/jpeg" \
  -F "file=@./floor-plan.pdf;type=application/pdf"
```

### 13.2 Contact bằng phone, không lịch và không attachment

```bash
curl -X POST "https://vnote.io.vn/api/consultations" \
  -F "name=Jane Smith" \
  -F "phone_or_email=+1 415 555 0198" \
  -F "message=Please contact me about a custom dining table." \
  -F "consultation_time="
```

## 14. Migration từ API cũ

Backend cũ nhận `email` và `phone` riêng. Contract mới dùng duy nhất `phone_or_email`.

Yêu cầu migration:

1. Endpoint `/api/consultations` phải nhận `phone_or_email` bắt buộc.
2. Không yêu cầu frontend mới gửi `email` hoặc `phone`.
3. Trong giai đoạn deploy cuốn chiếu, backend có thể tạm nhận cả contract cũ và mới, nhưng
   response/data model phải normalize về `contact_type` và `contact_value_normalized`.
4. Sau khi frontend mới được publish ổn định, contract cũ nên được deprecate có kế hoạch.
5. Migration database không được làm mất lead/file cũ.
6. Attachment model phải hỗ trợ one-to-many.
7. `consultation_time` thiếu hoặc rỗng phải được xem là optional.

## 15. Acceptance criteria

- [ ] API nhận `multipart/form-data` từ Shopify storefront.
- [ ] Chỉ có ba business fields bắt buộc: `name`, `phone_or_email`, `message`.
- [ ] Không yêu cầu đồng thời cả phone và email.
- [ ] Phân loại và normalize đúng email hoặc phone.
- [ ] Từ chối contact không hợp lệ ở cả hai dạng.
- [ ] Chấp nhận request không có schedule và không có attachment.
- [ ] Chấp nhận `consultation_time` rỗng hoặc thiếu.
- [ ] Parse đúng `hh:mm AM|PM, dd/mm/yyyy`; minute phải chia hết cho 5.
- [ ] Không coi preferred time là confirmed booking.
- [ ] Nhận nhiều file cùng key `file`.
- [ ] Chặn file trên 10 MB và file signature/MIME không hợp lệ.
- [ ] Lưu lead và attachments atomically, không tạo orphan data.
- [ ] Trả `201` khi thành công và non-2xx khi thất bại.
- [ ] CORS hoạt động cho production origin và localhost QA theo environment.
- [ ] Có rate limit, duplicate protection và stored-XSS protection.
- [ ] Admin và attachment download được bảo vệ.
- [ ] Notification nội bộ phân biệt email/phone và schedule optional.
- [ ] Có automated tests cho email contact, phone contact, invalid contact, no schedule,
      valid schedule, malformed schedule, no file, multi-file, invalid MIME, oversized file,
      CORS, duplicate và rate limit.

## 16. Frontend source of truth

Contract được đối chiếu với:

```text
sections/customization-consultation.liquid
templates/page.customization.json
```

Nếu frontend thay đổi field name, scheduler format, attachment limits hoặc response handling,
backend và tài liệu này phải được cập nhật trong cùng release.
