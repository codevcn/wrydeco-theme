# Wrydeco — Hướng dẫn & Báo cáo Thiết lập Native Browse Abandonment Automation

> **Mã tài liệu:** `doc/feature-implement/Wrydeco_Browse_Abandonment_Native_Setup_Guide.md`  
> **Áp dụng cho:** Shopify Store **WRYDECO** (`wrydeco.myshopify.com`)  
> **Tác giả:** AI Assistant  
> **Thời gian:** 07/10/2026  

---

## 1. Mục tiêu & Yêu cầu của Dự án

1. **Yêu cầu từ Leader:**
   - Thiết lập quy trình tự động hóa **Native "Browse Abandonment"** (gửi lại email cho khách hàng đã xem sản phẩm trên web nhưng rời đi mà chưa mua hàng).
   - **Tần suất gửi:** Định kỳ **2 – 3 ngày** gửi 1 mail (nhịp độ vừa phải, lịch thiệp, phù hợp phong cách luxury).
2. **Báo cáo kỹ thuật:**
   - Kiểm tra hiện trạng store thông qua Shopify Admin API (sử dụng Access Token tại `admin/access-token.md` / `admin/.env`).
   - Xây dựng tài liệu hướng dẫn kỹ thuật, cấu hình luồng, copywriting chuẩn định vị thương hiệu WRYDECO và quy trình kích hoạt.

---

## 2. Kết quả Khảo sát Hệ thống qua Shopify Admin API

Sử dụng Shopify Admin API (API Version `2026-07`), kết quả truy vấn GraphQL Admin API của store WRYDECO ghi nhận:

| Hạng mục kiểm tra | Trạng thái kỹ thuật | Chi tiết dữ liệu |
| :--- | :---: | :--- |
| **Store Plan** | ✅ Đạt điều kiện | `Basic App Development` (hỗ trợ đầy đủ Shopify Automations & Messaging) |
| **Shopify Messaging (Email)** | ✅ Đã cài đặt | `App ID: gid://shopify/App/2755583` (Shopify Messaging) |
| **Shopify Forms** | ✅ Đã cài đặt | `App ID: gid://shopify/App/6171699` |
| **Marketing Activities** | ⚪ Chưa kích hoạt | Danh sách `marketingActivities` hiện tại: `0` (chưa có automation nào chạy ngầm) |
| **Customer Newsletter Base** | ✅ Sẵn sàng | Đang có 10 hồ sơ khách hàng (8 hồ sơ ở trạng thái `emailMarketingConsent: SUBSCRIBED`) |

### Phân định kỹ thuật: API Token vs Shopify Admin UI
* **Quy định bảo mật của Shopify:** Shopify **không cung cấp GraphQL mutation công khai** để các Custom App Token bên ngoài tự động tạo hoặc click kích hoạt toàn bộ luồng *Shopify Flow / Marketing Automation*. Việc tạo và bật workflow automation được Shopify thiết kế để merchant / quản trị viên thực hiện trực tiếp trên giao diện **Shopify Admin UI**.
* **Ưu điểm lớn:** Do store **đã cài đặt sẵn app chính chủ Shopify Messaging**, store hoàn toàn sở hữu template native **"Convert abandoned product browse"** mà **không cần cài thêm app thứ 3 (Klaviyo / Omnisend)** và **không cần chèn thêm script ngoài gây chậm trang**.

---

## 3. Kiến trúc Luồng Automation chuẩn WRYDECO (2–3 Ngày)

### 3.1 Sơ đồ vận hành luồng (Workflow Diagram)

```
[Khách hàng đã Subscribe xem sản phẩm trên Store]
                        │
                        ▼
   [Khách rời website mà KHÔNG add-to-cart, KHÔNG mua]
                        │
                        ▼
             ⏳ CHỜ 24 GIỜ (1 NGÀY)
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
   [Đã mua hàng / Có đơn?]    [Chưa mua hàng]
           │                         │
      (DỪNG LUỒNG)                   ▼
                        📨 EMAIL 1: Gallery Follow-up
                        "A piece you recently explored"
                        (Hiển thị ảnh lớn sản phẩm đã xem)
                                     │
                                     ▼
                        ⏳ CHỜ 2 – 3 NGÀY (48 – 72 GIỜ)
                                     │
                        ┌────────────┴────────────┐
                        ▼                         ▼
                [Đã đặt hàng?]             [Vẫn chưa mua]
                        │                         │
                   (DỪNG LUỒNG)                   ▼
                                     📨 EMAIL 2: Studio Consultation
                                     "Tailoring to your space — Custom sizing"
                                     (Gợi ý tư vấn kích thước cùng Nghệ nhân)
                                                  │
                                                  ▼
                                            (KẾT THÚC LUỒNG)
```

### 3.2 Cơ chế nhận diện khách hàng (Identity Resolution)
Hệ thống sẽ kích hoạt gửi email khi khách hàng thỏa mãn:
1. Đã đăng ký email qua form newsletter của store (`snippets/lead-capture-popup.liquid`).
2. Hoặc đã đăng nhập tài khoản / Shop Pay trên trình duyệt.
3. Hoặc đã click vào website thông qua một email marketing trước đó.
*(Nếu là khách vãng lai hoàn toàn ẩn danh, hệ thống tự động bỏ qua để đảm bảo tuân thủ quyền riêng tư GDPR).*

---

## 4. Hướng dẫn Từng Bước Kích hoạt trên Shopify Admin (Dưới 3 Phút)

Quản trị viên / Merchant thực hiện các bước sau trên trình duyệt:

### Bước 1: Mở mục Automations
Truy cập đường dẫn trực tiếp:
👉 `https://admin.shopify.com/store/wrydeco/marketing/automations`  
*(Hoặc vào menu bên trái: **Marketing** $\rightarrow$ **Automations**)*.

### Bước 2: Tạo Automation từ Template có sẵn
1. Nhấn nút **"Create automation"** (Tạo quy trình tự động) ở góc trên bên phải.
2. Tìm kiếm từ khóa: `browse` hoặc cuộn xuống tìm template:
   👉 **`Convert abandoned product browse`** (Chuyển đổi khách xem sản phẩm bị bỏ quên).
3. Nhấn **"Use template"** (Sử dụng mẫu này).

### Bước 3: Cấu hình Thời gian chờ (Wait Time)
1. Trong sơ đồ quy trình hiển thị, click vào khối **Wait** (Thời gian chờ).
2. Chỉnh sửa thời gian chờ theo đúng yêu cầu:
   - **Tùy chọn A (Đơn giản - 1 Email):** Đổi từ `2 hours` mặc định thành **`2 days`** hoặc **`3 days`**.
   - **Tùy chọn B (Tối ưu - 2 Email theo nhịp 2-3 ngày):** 
     - Khối Wait 1: Đặt **`24 hours`** (để gửi Email 1 khi khách còn nhớ sản phẩm).
     - Thêm khối Wait 2: Đặt **`2 days`** (48 hours) hoặc **`3 days`** trước khi gửi Email 2.

### Bước 4: Chỉnh sửa Nội dung Email (Visual Builder)
1. Click vào khối hành động **"Send marketing email"**.
2. Chọn **"Edit email"** để mở trình biên tập Shopify Email.
3. Kiểm tra dynamic section: Đảm bảo có block **"Abandoned browse"** (Shopify tự động lấy dữ liệu từ `abandoned_visit.products_viewed`).
4. Cập nhật tiêu đề và nội dung theo mẫu chuẩn Luxury bên dưới.

### Bước 5: Bật Automation
Nhấn **"Turn on automation"** ở góc trên cùng bên phải. Quy trình sẽ chính thức hoạt động 24/7.

---

## 5. Mẫu Nội dung Email chuẩn Định vị Luxury WRYDECO

Tuân thủ nghiêm ngặt **[PROJECT_CONTEXT.md](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/PROJECT_CONTEXT.md)**: Không giật tít giảm giá xả hàng, không dùng banner đồng hồ đếm ngược, giữ tone giọng Poetic, Serene và Craft-centered.

### 5.1 Email 1: Nhắc nhớ Tác phẩm đã chiêm ngưỡng (Gửi sau 24h)
* **Tiêu đề (Subject Line):** `A piece you recently explored | WRYDECO Gallery`
* **Xem trước (Preview Text):** `Individually sculpted from solid wood. Each contour tells a story.`
* **Bố cục nội dung:**
  * **Logo:** `WRYDECO` (Centered, tối giản).
  * **Lời dẫn:**
    > *Dear Collector,*  
    > *Thank you for visiting the WRYDECO gallery. We noticed your interest in our handcrafted woodwork.*
  * **Dynamic Product Section:**
    * Hiển thị ảnh lớn sản phẩm khách vừa xem (tự động render bởi Shopify).
    * Tên tác phẩm (*Artwork Title*) & Nghệ nhân chế tác.
  * **Đoạn văn thương hiệu:**
    > *Each piece is individually shaped from organic timber, honoring the natural grain and live edge that nature perfected over decades. No two creations are ever identical.*
  * **Nút bấm (Primary CTA):** `[ View the Piece ]` $\rightarrow$ Trỏ về trang chi tiết sản phẩm.
  * **Footer:** Địa chỉ studio, hotline và link unsubcribe tự động.

---

### 5.2 Email 2: Đề xuất Tư vấn Kích thước Riêng (Gửi sau 2–3 ngày tiếp theo)
* **Tiêu đề (Subject Line):** `Tailoring to your space — Custom sizing & consultation`
* **Xem trước (Preview Text):** `Have specific dimensions in mind? Our Master Artisans are here to assist.`
* **Bố cục nội dung:**
  * **Lời dẫn:**
    > *Finding the perfect statement piece for your home often requires exact spatial harmony.*
  * **Hình ảnh:** Ảnh không gian trưng bày phòng khách hoặc workshop chế tác.
  * **Thông điệp:**
    > *Whether you need an adapted height for your ceiling, custom branch contours, or a tailored wood finish to match your existing interior, our studio offers complimentary bespoke consultation.*
  * **Đặc quyền bậc chi tiêu (Nhắc khéo, không spam voucher):**
    > *As a valued gallery subscriber, your custom commission is also eligible for our Studio Courtesy tiered privilege (ranging from $100 up to $1,000 courtesy on qualifying orders).*
  * **Nút bấm (CTA):** `[ Consult with an Artisan ]` $\rightarrow$ Trỏ về `https://wrydeco.com/pages/customization`.

---

## 6. Danh mục Kiểm thử & Xác minh (Quality Assurance)

Sau khi merchant bật Automation, thực hiện kiểm tra 4 kịch bản để nghiệm thu:

| Kịch bản kiểm thử | Hành vi người dùng | Kết quả kỳ vọng |
| :--- | :--- | :--- |
| **Kịch bản 1 (Thành công)** | Khách đã đăng ký newsletter $\rightarrow$ Vào xem sản phẩm $\rightarrow$ Thoát web không mua. | Nhận Email 1 sau 24h và Email 2 sau 2-3 ngày. |
| **Kịch bản 2 (Chuyển đổi giỏ hàng)** | Khách xem sản phẩm $\rightarrow$ Thêm vào giỏ hàng (`Add to Cart`) $\rightarrow$ Thoát web. | **Không nhận** Browse email (Shopify chuyển sang luồng Abandoned Cart). |
| **Kịch bản 3 (Đã hoàn tất đơn)** | Khách xem sản phẩm $\rightarrow$ Tiến hành thanh toán thành công. | **Không nhận** bất kỳ email nhắc nhở nào. |
| **Kịch bản 4 (Khách ẩn danh)** | Khách mới lần đầu vào web $\rightarrow$ Không đăng ký newsletter $\rightarrow$ Thoát web. | **Không phát sinh lỗi**, không gửi email rác. |

---

## 7. Kết luận & Khuyến nghị Dài hạn

1. **Hiệu năng & Tối ưu:**
   - Việc sử dụng tính năng **Native của Shopify Messaging** giúp store WRYDECO giữ nguyên tốc độ load trang tối đa (không thêm script third-party nặng nề như Klaviyo.js hay Omnisend.js).
   - Popup thu thập email [snippets/lead-capture-popup.liquid](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/snippets/lead-capture-popup.liquid) hoạt động liền mạch với hệ thống automation này mà không cần sửa code.
2. **Kế hoạch tiếp theo:**
   - Khi lượng traffic và quy mô khách hàng B2B (Kiến trúc sư / Interior Designers) tăng trưởng mạnh mẽ, store có thể cân nhắc tích hợp Klaviyo để triển khai phân loại khách hàng chuyên sâu (Trade Program vs Homeowners).
