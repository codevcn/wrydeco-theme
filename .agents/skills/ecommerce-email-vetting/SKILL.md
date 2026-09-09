---
name: ecommerce-email-vetting
description: Quy trình và phương pháp thẩm định, phân loại email cho hộp thư thương mại điện tử (e-commerce support inbox). Giúp nhận diện chính xác email từ khách hàng thật (mua hàng, tư vấn bespoke), phân biệt rõ với email chào hàng dịch vụ (CRO, Ads, SEO), thư mồi (ice-breaker baiting), các hình thức lừa đảo tinh vi (Fake Cashier's Check, Phishing mạo danh sàn) và thông báo ứng dụng.
---

# E-commerce Email Vetting & Inbox Triage Skill

## 1. Mục tiêu cốt lõi (Core Directive)

Kỹ năng này cung cấp quy trình chuẩn mực và phương pháp luận chuyên sâu để kiểm tra, phân tích và phân loại toàn bộ thư từ gửi tới hộp thư hỗ trợ (`support@`, `contact@`, `sales@`) của cửa hàng thương mại điện tử (đặc biệt là các thương hiệu cao cấp, sản phẩm bespoke / high-ticket như WRYDECO).

Nhiệm vụ tối thượng:
1. **Bảo vệ và ưu tiên tuyệt đối các cơ hội kinh doanh thật (Genuine Customer Leads):** Nhận diện nhanh chóng khách hàng tiềm năng có nhu cầu mua sắm, đặt thiết kế riêng (custom commission) hoặc cần tư vấn sản phẩm.
2. **Loại bỏ nhiễu và bẫy tiếp thị (Spam, Pitches, Baiting):** Phát hiện các kỹ thuật "thả mồi" thăm dò, email chào hàng tự động hoặc hàng loạt từ các freelancer / agency.
3. **Ngăn chặn rủi ro an ninh và lừa đảo tài chính (Scam & Phishing Prevention):** Vạch trần kịp thời các kịch bản lừa đảo chi phiếu ngân hàng (Fake Check Scam), thư giả mạo nền tảng (Shopify Phishing) đe dọa tài sản và tài khoản của cửa hàng.

---

## 2. Khi nào kích hoạt Skill này (When To Use)

Kích hoạt skill này khi:
* Được yêu cầu kiểm tra hộp thư đến (Inbox) của cửa hàng định kỳ hoặc sau khi vừa thay đổi giao diện, cài app mới.
* Cần xác minh một email cụ thể xem người gửi có phải là **khách hàng thật** hay là **chào hàng / lừa đảo**.
* Cần phân loại danh sách email theo mức độ ưu tiên xử lý (Khách hàng > Cảnh báo hệ thống > Spam/Scam).
* Cần tư vấn hướng phản hồi an toàn trước một đề nghị mua hàng số lượng lớn bất thường hoặc phương thức thanh toán lạ.

---

## 3. Quy trình 5 bước thẩm định Email (5-Step Vetting Framework)

Mọi email khi được rà soát phải đi qua phễu thẩm định 5 bước tuần tự sau:

```
[ Email Đến ]
     │
     ▼
Step 1: Kiểm tra Tam giác Danh tính Kỹ thuật (Identity Audit)
     │   └── Tên hiển thị vs. Email thật vs. Chữ ký chân thư
     ▼
Step 2: Phân tích Kịch bản & Ngôn từ (Pattern & Linguistic Analysis)
     │   └── Khách thật vs. Thư mồi vs. Chào dịch vụ vs. Scam
     ▼
Step 3: Đối chiếu Bối cảnh Thương hiệu (Business Context Alignment)
     │   └── Phù hợp với DNA sản phẩm, tầm giá và tệp khách hàng?
     ▼
Step 4: Kiểm tra Lịch sử & Dữ liệu Cảnh báo (History & Threat Intelligence)
     │   └── Đã có email trao đổi trước đó? Khớp với kịch bản lừa đảo quốc tế?
     ▼
Step 5: Xếp loại & Đề xuất Hành động (Classification & Action Protocol)
```

---

### BƯỚC 1: Kiểm tra Tam giác Danh tính Kỹ thuật (Identity Audit)

Luôn luôn kiểm tra bộ 3 thông số định danh trong phần Header của email:

| Thành phần | Khách hàng thật thông thường | Dấu hiệu Nghi vấn / Lừa đảo / Dịch vụ |
| :--- | :--- | :--- |
| **1. Tên hiển thị (Display Name)** | Tên cá nhân thật, viết hoa bình thường (VD: *Sarah Jenkins*, *David Miller*) | Tên viết hoa toàn bộ (*JOHNSON RICHARD*), tên kèm chức danh (*Abdul Expert*, *Faith skilled Shopify partner*). |
| **2. Địa chỉ gửi thực tế (Raw Sender)** | Trùng khớp với tên hiển thị. Domain cá nhân hoặc tổ chức hợp lệ. | **Bất nhất với tên hiển thị.** Tên là Johnson nhưng email là `whitneyrounds88@gmail.com`. Tên tài khoản chứa từ khóa dịch vụ: `-fixes`, `-solutions`, `-digital`, `-agency`. |
| **3. Tên ký ở chân thư (Signature)** | Thống nhất với Tên hiển thị và email. | Một người nhưng có 3 tên khác nhau (Display: *A*, Email: *B*, Chân thư ký: *C*). |
| **4. Email mạo danh hệ thống** | Shopify / Stripe gửi từ domain chính thức (`@shopify.com`, `@stripe.com`). | Gửi từ các địa chỉ Gmail mạo danh: `mailingsystem.shopifyhelp@gmail.com`, `support.shopify.billing@gmail.com`. |

> **Quy tắc vàng:** Bất kỳ email nào có **Tên hiển thị khác hoàn toàn với địa chỉ email gửi đi** đều phải nâng mức cảnh giác lên cao nhất.

---

### BƯỚC 2: Phân tích Kịch bản & Ngôn từ (Pattern Matching)

Phân loại email vào 1 trong 5 nhóm dựa trên cấu trúc câu chữ:

#### Nhóm 1: Khách hàng thật (Genuine Customer)
* **Đặc điểm:** Hỏi trực diện vào sản phẩm, nhu cầu có tính cá nhân hóa cao.
* **Nội dung mẫu:**
  * *"Tôi thích mẫu kệ nhánh cây gắn tường, phòng khách nhà tôi dài 3m thì nên chọn size nào?"*
  * *"Sản phẩm bàn live-edge này có thể tùy chỉnh màu gỗ sồi sẫm hơn được không?"*
  * *"Thời gian hoàn thiện và phí ship một chiếc bàn đặt riêng đến Austin, Texas là bao nhiêu?"*
* **Tâm lý:** Khách hàng quan tâm đến giá trị sản phẩm, tính thẩm mỹ, độ bền và quy trình đặt hàng an toàn qua web.

#### Nhóm 2: Thư mồi / Thăm dò (Ice-Breaker Baiting)
* **Đặc điểm:** Tiêu đề thường để trống `(Không có chủ đề)` hoặc tiêu đề 1 chữ (*"Greetings"*, *"Hello"*). Nội dung cực ngắn (1 câu cộc lốc), hỏi bâng quơ.
* **Nội dung mẫu:**
  * *"Are you still taking orders through this store?"*
  * *"Do you ship worldwide?"* / *"Can u ship New York?"*
  * *"Can I speak with the owner..?"* / *"Cn I make a request ?"*
* **Bản chất:** Kẻ gửi (thường là bot hoặc freelancer săn khách) cố tình **không chào mời dịch vụ ngay** để không bị bộ lọc Spam chặn. Mục đích duy nhất là xem hòm thư này có người trực hay không. Nếu shop trả lời, họ sẽ lập tức gửi email thứ hai để chào mời dịch vụ sửa web, tối ưu SEO, chạy quảng cáo.

#### Nhóm 3: Chào mời Dịch vụ Trực diện (Cold Outreach / Pitches)
* **Đặc điểm:** Tự nhận là chuyên gia CRO, đối tác Shopify Partner, chuyên gia quảng cáo Google/Facebook, hoặc đề nghị ăn chia phần trăm doanh số.
* **Nội dung mẫu:**
  * *"Tôi nhận thấy trang sản phẩm của bạn chưa tối ưu chuyển đổi, tôi có thể gửi cho bạn bản phân tích 50 giây được không?"*
  * *"Nếu tôi đem về 20 đơn hàng trong 3 ngày tới, bạn có trích 3% hoa hồng không?"*
  * *"Tôi chạy ads Google Shopping & YouTube, chỉ nhận tiền trên doanh thu mang lại..."*

#### Nhóm 4: Lừa đảo Tài chính & Phishing (Scams & Fraud)
* **Đặc điểm:**
  * Giả mạo đơn hàng lớn (Bulk order) nhưng từ chối thanh toán trực tuyến qua web.
  * Bắt buộc dùng **Cashier's Check / Certified Check (Séc ngân hàng gửi qua bưu điện)**.
  * Hoặc giả mạo thông báo dọa khóa cửa hàng trong 24h - 48h vì vi phạm chính sách nhằm chiếm đoạt tài khoản.

#### Nhóm 5: Thông báo Hệ thống & Ứng dụng (App & Store System Notifications)
* **Đặc điểm:** Gửi từ các đối tác công nghệ, ứng dụng đã cài đặt trên Shopify (MIDA, Loox, Judge.me, Omega Facebook Pixel, Shopify Billing).
* **Nội dung:** Thông báo theme mới được publish, nhắc bật App Embed, thông báo chu kỳ thanh toán, cảnh báo Pixel ngừng thu thập dữ liệu.

---

### BƯỚC 3: Đối chiếu Bối cảnh Kinh doanh Cửa hàng (Business Context Alignment)

Đặt nội dung email vào lăng kính thực tế của thương hiệu WRYDECO:
* **Định vị sản phẩm:** WRYDECO là thương hiệu nội thất gỗ nghệ thuật thủ công, điêu khắc hữu cơ (bàn ghế, kệ nhánh cây, tủ kệ nghệ thuật) với mức giá từ **\$2.000 đến \$25.000+**.
* **Hành vi bất thường cảnh báo lừa đảo:**
  * Nếu ai đó liên hệ yêu cầu làm **60 chiếc bảng tên/kỷ niệm chương gỗ giá rẻ** (*"60 pieces of 6x8-inch plaques engraved CERTIFICATE BRIDAL MAKEUP ARTIST"*), đây hoàn toàn không phải dòng sản phẩm của WRYDECO.
  * Một thương hiệu nội thất gallery cao cấp không phải là xưởng in quà tặng lưu niệm giá rẻ. Sự lệch pha 100% giữa sản phẩm cửa hàng và đơn đặt hàng là tín hiệu cảnh báo lừa đảo cực mạnh.

---

### BƯỚC 4: Kiểm tra Lịch sử & Dữ liệu Cảnh báo (Threat Intelligence)

* **Tra cứu chuỗi email (Thread History):** Xem đối tượng đã gửi bao nhiêu thư, phản ứng ra sao khi cửa hàng đưa ra link thanh toán chính thức trên website.
* **Kiểm tra mẫu lừa đảo đã biết (Scam Database Check):**
  * Kẻ lừa đảo thường dùng các kịch bản sẵn lưu hành trên toàn cầu.
  * *Mẫu lừa đảo nổi tiếng:* Yêu cầu khắc 60 bảng gỗ 6x8 inch cho chương trình "women's empowerment", viện cớ được giới thiệu bởi "Mary", đòi trả bằng Cashier's check và tự điều động shipper riêng.
  * Khi bị ép thanh toán qua website, kẻ lừa đảo sẽ bắt đầu lộ ngữ pháp tiếng Anh kém, lặp từ, hối thúc.

---

### BƯỚC 5: Xếp loại & Đề xuất Hành động (Action Protocol)

| Phân loại | Mức độ rủi ro / Ưu tiên | Hành động xử lý chuẩn |
| :--- | :--- | :--- |
| **Khách hàng thật (Lead)** | 🟢 **Ưu tiên cao nhất (P1)** | • Phản hồi ngay trong vòng 2–4 giờ làm việc.<br>• Thu thập kích thước, yêu cầu vật liệu, không gian bài trí.<br>• Điều hướng sang lịch tư vấn chuyên sâu (*Book a Consultation*). |
| **Cảnh báo Kỹ thuật (Apps/Shopify)** | 🟡 **Ưu tiên kỹ thuật (P2)** | • Xác nhận nguồn gửi chính thống.<br>• Kiểm tra ngay Theme Editor để bật App Embed (ví dụ: MIDA, Judge.me) hoặc kích hoạt lại Facebook Pixel nếu đang chạy ads. |
| **Thư mồi (Baiting)** | ⚪ **Bỏ qua / Không trả lời (P3)** | • **Tuyệt đối không trả lời** các câu hỏi vu vơ như *"Do you ship worldwide?"* hay *"Are you still taking orders?"*.<br>• Trả lời sẽ xác nhận hộp thư đang hoạt động và kích hoạt hàng loạt email chào hàng tiếp theo. |
| **Chào mời dịch vụ (Cold Pitch)** | ⚪ **Bỏ qua / Lưu trữ (P4)** | • Không phản hồi. Đưa vào thư mục lưu trữ hoặc xóa nếu không có nhu cầu. |
| **Lừa đảo Séc giả (Fake Check Scam)** | 🔴 **Nguy hiểm cao (P0)** | • **Tuyệt đối không nhận séc giấy / cashier's check** qua đường bưu điện.<br>• **Không cung cấp:** Họ tên người thụ hưởng trên séc, địa chỉ nhà/văn phòng nhận thư, số điện thoại cá nhân.<br>• Nếu khách nài nỉ: Chỉ chấp nhận thanh toán 100% qua cổng thẻ chính thức trên website WRYDECO.<br>• Gắn cờ cảnh báo hoặc đưa vào danh sách đen (Blacklist). |
| **Phishing giả mạo Shopify/Stripe** | 🔴 **Nguy hiểm cao (P0)** | • Tuyệt đối không click vào đường link "Appeal" hoặc "Login" trong thư.<br>• Kiểm tra trực tiếp tại trang quản trị `admin.shopify.com` xem có thông báo chính thức không.<br>• Đánh dấu là Phishing / Báo cáo thư rác. |

---

## 4. Cẩm nang Bóc trần: Kịch bản Lừa đảo Séc Giả (Fake Cashier's Check Scam Playbook)

Đặc biệt lưu ý kịch bản lừa đảo này vì kẻ xấu thường nhắm trực tiếp vào các cửa hàng đồ gỗ thủ công (woodcraft / furniture):

### Diễn biến chi tiết của cái bẫy:
1. **Tiếp cận:** Gửi đơn đặt hàng số lượng lớn (thường là 50–100 món quà tặng/kỷ niệm chương gỗ) với thông số rất cụ thể để tạo vẻ chuyên nghiệp. Kèm câu chuyện giả tạo: *"Tôi được người quen giới thiệu"* hoặc *"Phục vụ hội nghị từ thiện"*.
2. **Nài nỉ trả bằng séc:** Luôn nại lý do *"Bộ phận tài chính / kế toán của tôi chỉ có thể xuất Cashier's check hoặc Certified check"* và từ chối thanh toán qua thẻ tín dụng trên web vì sợ lộ thông tin thẻ bị đánh cắp.
3. **Chiêu bài tạo niềm tin giả:** Kẻ gian nói: *"Tôi sẽ gửi séc cho bạn và đợi bạn mang ra ngân hàng nộp, khi nào tiền nổi (clear) thì bạn mới bắt đầu sản xuất"*.
4. **Cơ chế lừa đảo ngân hàng (Check Clearing Loophole):**
   * Theo luật ngân hàng quốc tế (như Reg CC tại Mỹ), ngân hàng buộc phải tạm ứng tiền vào tài khoản người nộp séc sau 24–48 giờ. Người bán thấy tài khoản tăng tiền thì ngỡ là tiền thật đã vào.
   * Kẻ lừa đảo thường viết séc **thừa tiền** (ví dụ đơn hàng \$2.000 nhưng séc ghi \$5.000) và viện cớ: *"Tôi gửi gộp tiền vận chuyển cho bên giao phôi gỗ (woodcarver courier), bạn làm ơn rút tiền mặt hoặc chuyển khoản phần tiền thừa \$3.000 cho bên vận chuyển giúp tôi"*.
   * Thực chất, quá trình ngân hàng thẩm định nguồn tiền thật từ séc giả mất từ 2 đến 3 tuần. Khi phát hiện séc rác hoặc từ tài khoản bị hack, ngân hàng sẽ **thu hồi toàn bộ số tiền đó**. Cửa hàng vừa mất trắng khoản tiền đã chuyển cho "shipper", vừa bị ngân hàng phạt vì nộp séc lừa đảo.

---

## 5. Bảng Checklist Đánh giá Nhanh một Email (Quick Triage Checklist)

Khi mở một email bất kỳ, tự hỏi 5 câu hỏi nhanh sau:

- [ ] **1. Người gửi có dùng email dịch vụ / lạ không?** (Có chứa `-fixes`, `-solutions`, đuôi `@gmail.com` mạo danh hệ thống?).
- [ ] **2. Tên hiển thị, tên email và chữ ký cuối thư có khớp nhau không?** (Nếu xuất hiện 2–3 tên khác nhau ➔ 99% Scam/Spam).
- [ ] **3. Nội dung có đề cập đến một sản phẩm cụ thể trên website WRYDECO không?** (Hỏi về kệ, bàn, kích thước, hoàn thiện gỗ ➔ Khách thật. Hỏi làm đồ linh tinh không có trên web ➔ Cần thẩm tra kỹ).
- [ ] **4. Có đòi thanh toán ngoài website bằng Séc / Cashier's check không?** (Có ➔ 100% Lừa đảo).
- [ ] **5. Có đe dọa khóa tài khoản/khóa shop trong 24h-48h không?** (Kiểm tra ngay email người gửi có phải `@shopify.com` thật không).
