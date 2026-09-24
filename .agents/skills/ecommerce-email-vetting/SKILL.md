---
name: ecommerce-email-vetting
description: Dùng Playwright MCP để truy cập webmail WRYDECO, đăng nhập hộp thư, kiểm tra email mới và phân loại email thành khách hàng thật, cảnh báo hệ thống, thư mồi, chào dịch vụ, scam hoặc phishing.
---

---

# E-commerce Email Vetting

## Mục tiêu

Skill này dùng để:

1. Mở hộp thư WRYDECO bằng Playwright MCP.
2. Đăng nhập vào webmail.
3. Kiểm tra các email mới hoặc chưa xử lý.
4. Đọc đầy đủ nội dung email và thread liên quan.
5. Phân loại email.
6. Xác định email nào cần ưu tiên xử lý và email nào cần bỏ qua hoặc cảnh báo.

Không kết luận email trước khi đã đọc đủ thông tin cần thiết.

---

# 1. Truy cập Webmail bằng Playwright MCP

Luôn bắt đầu bằng Playwright MCP.

Truy cập:

```text
https://webmail.wrydeco.com
```

Thông tin đăng nhập không được hard-code trong skill này.

Nguồn credential:

```text
D:\D-Documents\Sensitive\Credentials\shopify\wrydeco\credentials.md
```

Trước khi mở webmail:

1. Đọc file credential ở đường dẫn trên bằng công cụ đọc file / filesystem hiện có của Agent.
2. Tìm đúng thông tin đăng nhập dành cho **WRYDECO webmail**.
3. Lấy giá trị **username/email** và **password** từ file.
4. Chỉ giữ credential trong ngữ cảnh cần thiết để thực hiện đăng nhập.
5. Không in username/password ra terminal, log, screenshot, report hoặc câu trả lời cuối.
6. Không ghi credential trở lại `SKILL.md`, source code, Git repository hoặc file tạm.
7. Nếu file không tồn tại, không truy cập được, hoặc không xác định chắc chắn credential nào thuộc WRYDECO webmail thì dừng và báo lỗi. Không tự đoán credential.

Quy trình:

```text
Read credentials file
→ Locate WRYDECO webmail username/email
→ Locate WRYDECO webmail password
→ Open browser with Playwright MCP
→ Navigate to https://webmail.wrydeco.com
→ Wait until login form is ready
→ Fill username using the value read from credentials.md
→ Fill password using the value read from credentials.md
→ Submit login form
→ Wait for mailbox home page
→ Confirm Inbox is accessible
```

Nếu đăng nhập thất bại:

1. Kiểm tra trang có load hoàn chỉnh không.
2. Kiểm tra field username/password có nhập đúng không.
3. Kiểm tra có thông báo lỗi đăng nhập không.
4. Retry tối đa 2 lần nếu lỗi có vẻ do UI hoặc page load.
5. Nếu vẫn thất bại thì dừng nghiệp vụ check mail và báo rõ lỗi.

Không tiếp tục phân tích email khi chưa vào được trang chính của hộp thư.

---

# 2. Mở Inbox và xác định email cần kiểm tra

Sau khi đăng nhập thành công:

```text
Mailbox Home
→ Inbox
→ Identify unread/new emails
→ Open email
→ Read sender
→ Read subject
→ Read complete body
→ Read thread history if available
→ Perform vetting
```

Ưu tiên:

```text
1. Unread emails
2. Email mới nhất
3. Email có dấu hiệu là khách hàng
4. Email liên quan đơn hàng / custom commission
5. Email cảnh báo hệ thống
```

Không chỉ dựa vào subject hoặc preview.

Phải mở email để đọc nội dung đầy đủ.

Nếu email thuộc một conversation/thread, phải kiểm tra các email trước đó trong cùng thread khi chúng có thể ảnh hưởng đến kết luận.

---

# 3. Quy trình thẩm định email

Mỗi email phải đi qua 5 bước:

```text
Step 1: Identity Audit
Step 2: Pattern & Linguistic Analysis
Step 3: Business Context Alignment
Step 4: Thread History & Threat Analysis
Step 5: Classification & Action
```

---

## Step 1 — Identity Audit

Kiểm tra:

```text
Display Name
Raw Sender Email
Sender Domain
Signature
Reply-To nếu thấy được
```

Đối chiếu xem các thông tin có thống nhất hay không.

Dấu hiệu đáng ngờ:

- Display Name và email sender là hai tên hoàn toàn khác nhau.
- Signature dùng tên khác với Display Name.
- Email tự nhận là Shopify, Stripe hoặc nền tảng chính thức nhưng sender là Gmail hoặc domain lạ.
- Địa chỉ sender chứa các từ như:
  - agency
  - solutions
  - digital
  - fixes
  - marketing
  - expert

Identity mismatch không tự động chứng minh scam nhưng phải tăng mức cảnh giác.

---

# 4. Pattern & Linguistic Analysis

Phân email vào một trong các nhóm sau.

## A. Genuine Customer

Dấu hiệu:

- Hỏi trực tiếp về sản phẩm cụ thể.
- Hỏi size, kích thước, vật liệu, màu gỗ, finish.
- Hỏi custom / bespoke.
- Hỏi shipping.
- Hỏi thời gian sản xuất.
- Hỏi giá hoặc consultation.
- Nội dung thể hiện nhu cầu mua hàng cụ thể.

Ví dụ:

```text
Can this table be customized to 84 inches?

Do you offer a darker walnut finish?

How much would shipping to Austin, Texas cost?
```

Đây là lead cần ưu tiên.

---

## B. Ice-Breaker Baiting

Email rất ngắn, chung chung, không đề cập sản phẩm cụ thể.

Ví dụ:

```text
Are you still taking orders?

Do you ship worldwide?

Can I speak with the owner?

Can I make a request?

Is this store active?
```

Đặc điểm thường gặp:

- Subject trống hoặc rất chung chung.
- Nội dung chỉ 1–2 câu.
- Không nhắc sản phẩm.
- Không có nhu cầu mua hàng rõ ràng.

Mục tiêu thường là kiểm tra xem mailbox có người trực trước khi gửi email chào dịch vụ.

Action:

```text
Do not reply.
```

---

## C. Cold Outreach / Service Pitch

Dấu hiệu:

- Tự nhận Shopify expert.
- SEO specialist.
- CRO expert.
- Google Ads / Facebook Ads expert.
- Web designer.
- Marketing agency.
- Đề nghị tăng doanh số.
- Đề nghị audit website.
- Đề nghị commission/revenue share.

Ví dụ:

```text
I noticed conversion issues on your store.

I can bring you 20 sales this week.

Can I send you a free audit?

I only charge a percentage of generated revenue.
```

Action:

```text
Ignore / Archive.
```

---

## D. Scam / Fraud

Đặc biệt cảnh giác khi:

- Đặt số lượng lớn bất thường.
- Sản phẩm yêu cầu không phù hợp với WRYDECO.
- Không muốn checkout qua website.
- Yêu cầu Cashier's Check.
- Yêu cầu Certified Check.
- Muốn gửi check qua bưu điện.
- Muốn shop trả tiền cho shipper/courier bên thứ ba.
- Check có giá trị lớn hơn đơn hàng.
- Yêu cầu hoàn lại hoặc chuyển phần tiền dư.

Nếu xuất hiện pattern:

```text
Large custom order
+
Cashier's Check
+
Third-party shipper
+
Overpayment
```

phân loại:

```text
HIGH-RISK FAKE CHECK SCAM
```

Action:

```text
Do not accept check.
Do not send money to third party.
Do not provide unnecessary personal information.
Do not continue payment outside the official website.
```

---

## E. Phishing

Đặc biệt kiểm tra email tự nhận là:

```text
Shopify
Stripe
PayPal
Meta
Google
Payment provider
```

Dấu hiệu:

- Đe dọa khóa store.
- Đe dọa suspend account trong 24–48h.
- Yêu cầu login ngay.
- Yêu cầu click Appeal / Verify / Login.
- Sender domain không phải domain chính thức.

Action:

```text
Do not click suspicious links.
Do not submit credentials.
Verify independently through the official admin/dashboard.
```

---

## F. System / App Notification

Ví dụ:

```text
Shopify
Judge.me
Loox
MIDA
Omega Pixel
Facebook Pixel
Billing notification
Theme notification
```

Phải xác minh sender trước.

Nếu sender hợp lệ và nội dung liên quan hệ thống đang sử dụng:

```text
Classification: SYSTEM / TECHNICAL
Priority: P2
```

---

# 5. Business Context Alignment

Luôn đánh giá email dựa trên business của WRYDECO.

WRYDECO tập trung vào:

```text
Premium handcrafted furniture
Solid wood furniture
Organic / sculptural furniture
Custom furniture
Bespoke high-ticket products
```

Các yêu cầu liên quan:

```text
table
shelf
vanity
cabinet
wood furniture
custom dimensions
wood finish
bespoke commission
interior project
```

có khả năng phù hợp business.

Các yêu cầu hoàn toàn lệch sản phẩm phải được xem xét kỹ.

Ví dụ:

```text
60 small engraved plaques
cheap promotional gifts
mass-produced souvenirs
award plaques
```

không phù hợp với business chính của WRYDECO và có thể là tín hiệu scam hoặc spam.

---

# 6. Thread History

Nếu email là một thread:

Phải đọc các email trước đó khi cần thiết.

Kiểm tra:

```text
Người gửi đã hỏi gì trước đó?
Shop đã trả lời gì?
Người gửi có thay đổi câu chuyện không?
Có né thanh toán chính thức không?
Có chuyển sang Cashier's Check không?
Có bắt đầu yêu cầu third-party shipper không?
Tên / email / signature có thay đổi không?
```

Không đánh giá email cuối cùng tách biệt nếu thread chứa thông tin quan trọng.

---

# 7. Classification

Mỗi email phải được gán đúng một classification chính:

```text
P0 — SCAM / PHISHING
P1 — GENUINE CUSTOMER
P2 — SYSTEM / TECHNICAL
P3 — BAITING
P4 — COLD PITCH
```

Ý nghĩa:

### P0 — Scam / Phishing

Rủi ro cao.

```text
Do not interact with suspicious links or payments.
Flag clearly.
```

### P1 — Genuine Customer

Ưu tiên cao nhất về business.

Cần xác định:

```text
Customer need
Product
Dimensions
Material / finish
Location
Shipping requirement
Custom request
Next recommended action
```

### P2 — System / Technical

Thông báo kỹ thuật hợp lệ cần xem xét.

### P3 — Baiting

Không reply.

### P4 — Cold Pitch

Ignore hoặc Archive.

---

# 8. Output cuối cùng

Mục tiêu của báo cáo **không phải** là thống kê chi tiết tất cả email đã kiểm tra.

Kết luận quan trọng nhất phải trả lời trực tiếp:

```text
Có bao nhiêu email có khả năng là từ khách hàng thật?
```

Sau khi hoàn tất việc kiểm tra inbox, luôn mở đầu kết quả bằng:

```text
KẾT LUẬN

Có [X] email có khả năng là từ khách hàng thật.
```

Trong đó `[X]` là số email được phân loại là:

```text
P1 — GENUINE CUSTOMER
```

Chỉ tính email vào `[X]` khi nội dung và bối cảnh cho thấy có khả năng thực sự liên quan đến nhu cầu mua hàng, tư vấn sản phẩm, bespoke/custom furniture, shipping, kích thước, vật liệu, finish, giá, lead time hoặc project nội thất.

Không tính các email thuộc:

```text
P0 — SCAM / PHISHING
P2 — SYSTEM / TECHNICAL
P3 — BAITING
P4 — COLD PITCH
```

## Danh sách khách hàng tiềm năng

Sau phần kết luận, chỉ liệt kê các email được đánh giá là **P1 — GENUINE CUSTOMER**.

Format:

```text
1. From: ...
   Subject: ...
   Lý do có khả năng là khách hàng thật:
   - ...
   - ...
   Confidence: High / Medium / Low
```

Nếu không có email nào phù hợp:

```text
KẾT LUẬN

Không phát hiện email nào có đủ dấu hiệu để xem là khách hàng thật.
```

## Các cảnh báo quan trọng khác

Không cần lập báo cáo chi tiết cho toàn bộ email thuộc P2, P3 hoặc P4.

Chỉ bổ sung mục này nếu phát hiện vấn đề thực sự đáng chú ý, đặc biệt:

```text
P0 — SCAM / PHISHING
```

Ví dụ:

```text
CẢNH BÁO

Phát hiện 1 email có dấu hiệu phishing giả mạo Shopify.
Không click link hoặc nhập thông tin đăng nhập.
```

Nếu không có cảnh báo nghiêm trọng thì bỏ qua mục này.

## Nguyên tắc báo cáo

- Ưu tiên kết luận số lượng khách hàng thật hơn thống kê số lượng email theo từng category.
- Không tạo mục "BÁO CÁO CHI TIẾT THEO CHUẨN FORMAT SKILL" cho tất cả email.
- Không liệt kê đầy đủ P2/P3/P4 nếu chúng không cần hành động.
- Không biến kết quả thành bảng thống kê toàn bộ inbox.
- Chỉ đưa thông tin cần thiết để người dùng nhanh chóng biết:
  1. Có bao nhiêu khách hàng tiềm năng.
  2. Họ là ai.
  3. Họ đang quan tâm điều gì.
  4. Có scam/phishing nghiêm trọng nào cần biết hay không.

Output mong muốn:

```text
KẾT LUẬN

Có 2 email có khả năng là từ khách hàng thật.

KHÁCH HÀNG TIỀM NĂNG

1. From: jane@example.com
   Subject: Custom walnut dining table
   Nhu cầu: Hỏi custom kích thước và walnut finish.
   Confidence: High

2. From: david@example.com
   Subject: Shipping to California
   Nhu cầu: Hỏi shipping cho một sản phẩm cụ thể trên WRYDECO.
   Confidence: Medium

CẢNH BÁO

Phát hiện 1 email phishing giả mạo Shopify.
```

## Không cần nêu số lượng baiting, cold pitch, system notification hoặc các nhóm khác trừ khi user yêu cầu riêng.

# 9. Quy tắc vận hành

Luôn:

```text
Login first
→ Open Inbox
→ Read complete email
→ Check thread when relevant
→ Analyze identity
→ Analyze message pattern
→ Compare with WRYDECO business
→ Classify
→ Recommend action
```

Không:

- Chỉ đọc preview rồi kết luận.
- Chỉ dựa vào một keyword.
- Tự động reply email nếu task chỉ yêu cầu check mail.
- Click link đáng ngờ.
- Download attachment đáng ngờ.
- Nhập credentials vào website khác.
- Hard-code, echo, log hoặc tiết lộ credential đọc từ `credentials.md`.
- Sử dụng credential khác ngoài mục WRYDECO webmail khi chưa xác định chắc chắn.
- Chấp nhận phương thức thanh toán ngoài luồng chính thức.
- Reply baiting hoặc cold pitch nếu không có yêu cầu rõ ràng từ user.

Mục tiêu cuối cùng là:

```text
Xác định chính xác có bao nhiêu email có khả năng là từ khách hàng thật.
Không bỏ sót khách hàng thật.
Không mất thời gian vào sales pitch.
Không tương tác với scam/phishing.
Ưu tiên đúng email cần xử lý.
```
