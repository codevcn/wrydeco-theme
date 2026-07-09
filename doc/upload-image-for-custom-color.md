Dưới đây là API doc cho route mới, bạn có thể copy vào `doc/API.md`.

````md
## Upload Image API

Upload một file ảnh lên server và nhận lại URL public để xem ảnh trên trình duyệt.

---

### Endpoint

```txt
POST /api/upload-image
```
````

Production URL:

```txt
https://vnote.io.vn/api/upload-image
```

---

### Mục đích

Route này dùng để:

- Nhận 1 file ảnh từ client.
- Lưu ảnh vào server trong thư mục upload.
- Trả về `image_url`.
- `image_url` có thể mở trực tiếp trên browser để xem ảnh.

Ví dụ ảnh sau khi upload có thể xem tại:

```txt
https://vnote.io.vn/uploads/images/<stored_file_name>
```

---

### Request

Content-Type:

```txt
multipart/form-data
```

Field bắt buộc:

| Field   | Type | Required | Mô tả               |
| ------- | ---- | -------: | ------------------- |
| `image` | File |      Yes | File ảnh cần upload |

---

### File hợp lệ

Server chỉ chấp nhận các loại ảnh sau:

| MIME type    | Extension |
| ------------ | --------- |
| `image/jpeg` | `.jpg`    |
| `image/png`  | `.png`    |
| `image/webp` | `.webp`   |
| `image/gif`  | `.gif`    |

Giới hạn dung lượng mặc định trong code:

```txt
10MB / ảnh
```

Lưu ý: Nginx cũng có giới hạn tổng request bằng:

```nginx
client_max_body_size 50M;
```

---

### Response thành công

Status:

```txt
201 Created
```

Response body:

```json
{
  "image_url": "https://vnote.io.vn/uploads/images/8fd9c6f0b4f742dca7d8e2d6bdf4d2a1.jpg"
}
```

Field:

| Field       | Type   | Mô tả                                       |
| ----------- | ------ | ------------------------------------------- |
| `image_url` | string | URL public dùng để xem ảnh trên trình duyệt |

---

### Response lỗi

#### 1. Không gửi file ảnh

Status:

```txt
400 Bad Request
```

Response:

```json
{
  "detail": "Image file is required."
}
```

---

#### 2. File không phải ảnh hợp lệ

Status:

```txt
400 Bad Request
```

Response:

```json
{
  "detail": "Only jpg, png, webp, and gif images are allowed."
}
```

---

#### 3. Ảnh vượt quá giới hạn dung lượng

Status:

```txt
413 Payload Too Large
```

Response:

```json
{
  "detail": "Image exceeds 10MB limit."
}
```

---

### Ví dụ dùng cURL

```bash
curl -i -X POST https://vnote.io.vn/api/upload-image \
  -F "image=@/path/to/your-image.jpg"
```

Ví dụ thực tế:

```bash
curl -i -X POST https://vnote.io.vn/api/upload-image \
  -F "image=@./sample.jpg"
```

---

### Ví dụ dùng JavaScript

```js
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];

const formData = new FormData();
formData.append("image", file);

const response = await fetch("https://vnote.io.vn/api/upload-image", {
  method: "POST",
  body: formData,
});

const data = await response.json();

console.log(data.image_url);
```

---

### Ví dụ HTML + JS

```html
<input type="file" id="image-upload" accept="image/*" />
<button type="button" id="upload-btn">Upload image</button>

<script>
  document.getElementById("upload-btn").addEventListener("click", async () => {
    const input = document.getElementById("image-upload");

    if (!input.files.length) {
      alert("Please choose an image first.");
      return;
    }

    const formData = new FormData();
    formData.append("image", input.files[0]);

    const response = await fetch("https://vnote.io.vn/api/upload-image", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      console.error(data);
      alert(data.detail || "Upload failed.");
      return;
    }

    console.log("Uploaded image URL:", data.image_url);
    window.open(data.image_url, "_blank");
  });
</script>
```

---

### Ghi chú bảo mật

Hiện tại ảnh upload xong là public.

Ai có `image_url` đều có thể xem ảnh:

```txt
https://vnote.io.vn/uploads/images/<file-name>
```
