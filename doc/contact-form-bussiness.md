Nghiệp vụ chuẩn của **Contact Form trong Shopify store** là: **kênh tiếp nhận yêu cầu hỗ trợ / tư vấn / đơn hàng**, không nên chỉ xem nó là “1 cái form gửi email”.

Shopify mặc định cho phép tạo trang Contact Us bằng template `page.contact`, và tất cả Shopify themes đều có contact form built-in để khách hỏi về sản phẩm, chính sách hoặc đơn hàng. Form native này gửi submission về **store sender email address** trong phần Notifications của Shopify Admin. ([Shopify Help Center][1])

## 1. Contact page nên phục vụ những mục đích gì?

Chuẩn nhất là chia contact form thành các nhóm request rõ ràng:

| Nhóm request               | Ví dụ                                                      |
| -------------------------- | ---------------------------------------------------------- |
| Hỏi về đơn hàng            | “Order của tôi đang ở đâu?”, “Muốn đổi địa chỉ giao hàng”  |
| Hỏi về sản phẩm            | “Sản phẩm này dùng gỗ gì?”, “Kích thước có phù hợp không?” |
| Return / refund / shipping | “Tôi muốn đổi trả”, “Bao lâu nhận hàng?”                   |
| Custom / consultation      | “Tôi muốn đặt thiết kế riêng”, “Cần tư vấn kích thước”     |
| Wholesale / partnership    | “Tôi muốn mua số lượng lớn”                                |
| Other                      | Các câu hỏi còn lại                                        |

Không nên để khách tự viết tất cả trong một ô message duy nhất, vì sau này rất khó phân loại và xử lý.

## 2. Field chuẩn nên có

Với store Shopify thông thường, nên có:

| Field                    |           Bắt buộc? | Ghi chú                                                                        |
| ------------------------ | ------------------: | ------------------------------------------------------------------------------ |
| Name                     |                  Có | Tên khách                                                                      |
| Email                    |                  Có | Shopify contact form cần `contact[email]` để submit thành công. ([Shopify][2]) |
| Phone                    |               Không | Chỉ nên optional                                                               |
| Request type             |                  Có | Dropdown: Order, Product Question, Shipping, Return, Custom Order, Other       |
| Order number             | Không / conditional | Chỉ hiện khi khách chọn Order / Return                                         |
| Message                  |                  Có | Dùng `contact[body]`                                                           |
| Preferred contact method |               Không | Email / phone / text                                                           |
| Consent checkbox         |        Tuỳ mục đích | Nếu dùng cho marketing thì phải tách riêng consent                             |

Trong Shopify Liquid, form chuẩn dùng `{% form 'contact' %}`, các field custom đặt theo format `name="contact[...]"`, ví dụ `contact[order_number]`, `contact[request_type]`. Shopify cũng cho phép thêm optional fields như dropdown, radio, checkbox nếu đặt name đúng format `contact[information_id]`. ([Shopify][3])

## 3. Flow xử lý sau khi khách submit

Nghiệp vụ chuẩn nên là:

Khách gửi form → hệ thống báo “đã gửi thành công” → email về store sender email → team phân loại request → phản hồi theo SLA → nếu là order issue thì xử lý trong Shopify Admin → nếu là custom/consultation thì chuyển sang quy trình tư vấn.

Ví dụ SLA nên hiển thị ngay trên page:

> We usually respond within 1–2 business days.

Với WRYDECO / store đồ gỗ custom, Contact Form nên ưu tiên thêm nhánh **Custom Furniture / Design Consultation**, vì khách có thể cần tư vấn kích thước, chất liệu, màu gỗ, không gian đặt sản phẩm.

## 4. Native Shopify Contact Form hay app?

Có 2 hướng chuẩn:

### Hướng 1: Native Shopify Contact Form

Phù hợp khi store nhỏ, volume thấp, chỉ cần nhận email.

Ưu điểm: đơn giản, không cần app, dễ custom trong theme bằng Liquid.

Nhược điểm: khó quản lý pipeline, khó phân team, khó lưu lead/custom inquiry thành hệ thống riêng. Form native gửi submission về store sender email, và Shopify cũng ghi rõ không đổi được subject line của email contact form native. ([Shopify Help Center][1])

### Hướng 2: Shopify Forms / app form / custom backend

Phù hợp khi cần lead, marketing, wholesale, custom request, lưu dữ liệu, segment khách hàng.

Shopify Forms hỗ trợ tạo inline/popup forms, thu thập lead, tag customer, dùng submission data để build customer profiles, và xem analytics. ([Cửa Hàng Ứng Dụng Shopify][4]) Shopify Forms cũng cho phép bật email notification cho từng form, hoặc dùng Shopify Flow để gửi internal email tới nhiều người nhận. ([Shopify Help Center][5])

Với store nghiêm túc, mình khuyên:

- **Contact Us thường**: dùng native contact form.
- **Customization / consultation form**: dùng custom backend hoặc Shopify Forms/app form.
- **Newsletter**: tách riêng, không gộp vào Contact Form.
- **File upload ảnh/mẫu thiết kế**: không nên cố ép vào native contact form; nên dùng app form hoặc backend riêng.

## 5. UX chuẩn của Contact page

Trang Contact không nên chỉ có mỗi form. Nên có layout như sau:

1. **Hero nhỏ**
   “Need help? We’re here to assist.”

2. **Quick help links**
   Shipping Policy, Return Policy, Track Order, FAQ.

3. **Contact form**
   Field rõ, ít nhưng đủ.

4. **Response expectation**
   “Response time: 1–2 business days.”

5. **Business info**
   Email support, business hours, address nếu có retail/workshop.

6. **Alternative contact**
   Social, phone, live chat nếu có.

Shopify cũng khuyến nghị có thể thêm thông tin như thời gian phản hồi, địa chỉ cửa hàng, số điện thoại hoặc nội dung thương hiệu phía trên contact form. ([Shopify Help Center][1])

## 6. Spam & validation

Shopify có spam filtering cho nội dung `contact[body]`. Nếu submission bị đánh dấu spam, email vẫn được gửi nhưng subject có prefix `[SPAM]`; Shopify khuyên có thể tạo email filter để tách nhóm email này. ([Shopify Help Center][1])

Nên làm thêm ở theme:

- Validate email.
- Required message.
- Không để quá nhiều field bắt buộc.
- Có honeypot field nếu custom backend.
- Có success state rõ ràng.
- Có error state rõ ràng, dùng `form.errors`.

Shopify Liquid form object có `form.errors` và `form.posted_successfully?` để xử lý lỗi và trạng thái gửi thành công. ([Shopify][6])

## Kết luận chuẩn

Với một Shopify store chuẩn, Contact Form nên được xem là **customer support intake system**:

> Thu đúng thông tin → phân loại đúng loại yêu cầu → gửi về đúng nơi xử lý → phản hồi đúng SLA → không lẫn với newsletter/marketing → có tracking và chống spam.

Với WRYDECO, mình đề xuất dùng **2 form riêng**:
**Contact Us** cho support chung, và **Design Consultation / Custom Request** cho khách muốn tư vấn đồ gỗ custom.
