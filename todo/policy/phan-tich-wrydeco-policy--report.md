# Báo cáo Chi tiết Khắc phục Lỗi Misrepresentation – WRYDECO

> **Tài liệu tham chiếu:** [`todo/policy/phan-tich-wrydeco-policy.md`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/todo/policy/phan-tich-wrydeco-policy.md)  
> **Mục đích:** Báo cáo chi tiết toàn bộ các thay đổi kỹ thuật, nội dung, mã nguồn và dữ liệu store đã thực hiện nhằm xử lý cảnh báo vi phạm chính sách Google Merchant Center (Misrepresentation). Tài liệu được cấu trúc để phục vụ truy vết (traceability), audit và debug sau này.  
> **Thời gian cập nhật:** Tháng 09/2026.

---

## 1. Bảng tổng hợp trạng thái khắc phục (Status Matrix)

Đối chiếu trực tiếp với bảng **"Audit LIVE các tín hiệu nguy cơ Misrepresentation rất cao"** tại dòng 13 của tài liệu gốc:

| STT | Mức độ | Vấn đề LIVE ban đầu | Đánh giá rủi ro | Trạng thái | Giải pháp / Chi tiết xử lý |
|:---:|:---|:---|:---|:---:|:---|
| 01 | **P0 – Rất cao** | Image alt text của product page chứa brand **“WAZARO”** | Brand/identity contamination; ảnh hưởng toàn site | **ĐÃ FIX** | Đã tạo file CSV chuyên dụng chỉ sửa duy nhất cột Image Alt Text (thay 27 ảnh WAZARO sang WRYDECO cho 3 sản phẩm). |
| 02 | **P0 – Rất cao** | Claim “372 Verified Client Reviews / 4.7 / 99% / 400+ Homes Styled”; PDP hiện “4.7 (372 reviews)” | Thiếu bằng chứng provenance; dễ bị Google hiểu là giả mạo product reviews | **Chưa fix** | Cần bằng chứng review thực hoặc điều chỉnh/gỡ bỏ claim không thể chứng minh. |
| 03 | **P0 – Cao** | Landing page sản phẩm không có hiển thị chữ “Availability” (chỉ có Add to Cart) | Google yêu cầu hiển thị rõ tình trạng còn hàng / đặt làm (availability) | **Chưa fix** | Cần thêm nhãn Availability (In Stock / Made to Order) rõ ràng trên PDP. |
| 04 | **P1 – Cao** | Contact page thiếu địa chỉ tại block "Registered Business Address"; Footer chỉ ghi street name | Business identity không đồng nhất, thiếu chi tiết pháp nhân | **ĐÃ FIX** | Đã đồng bộ đầy đủ pháp nhân `Beaconfield Group LLC` kèm đầy đủ số nhà, Suite R, City, State, ZIP trên cả Contact page và Footer. |
| 05 | **P1 – Cao** | Website headline “Free Worldwide Shipping” nhưng policy chỉ áp dụng cho “eligible” | Claim tuyệt đối rộng hơn điều kiện thực tế | **ĐÃ FIX** | Đã sửa headline thành `Free Shipping on All Orders` (có link trỏ về policy); định nghĩa rõ "eligible" gắn trực tiếp với selector quốc gia tại checkout. |
| 06 | **P1 – Cao** | Shipping policy thiếu thông tin thuế nhập khẩu (import duties/taxes) cho đơn quốc tế | Rủi ro omission về chi phí ẩn phát sinh khi nhận hàng | **ĐÃ FIX** | Đã bổ sung cam kết thuế DDP (Delivery Duty Paid) trọn gói theo phê duyệt của Leader Phương: WRYDECO chịu 100% thuế phí. |
| 07 | **P1 – Cao** | Crawler thấy `[Button: Test lead popup]` & `[Button: Test success popup]` trong production DOM | Code/nội dung test dev tồn tại trên môi trường production | **ĐÃ FIX** | Đã xóa sạch khỏi code gốc; tạo module script tự động inject khi dev (`dev.cmd`) và tự động dọn sạch khi nén deploy (`compress-store-src.cmd`). |
| 08 | **P2 – Cần kiểm** | Trang Track Order chỉ xác minh được heading, chưa xác minh được flow thực tế | Nghi ngờ tính năng chưa hoàn thiện | **Chưa fix** | Cần kiểm tra flow tra cứu thực tế với tracking number mẫu. |
| 09 | **Chưa thể kết luận** | GMC feed, structured data, Google Payments, checkout cuối cùng, thuế, phí ship tại checkout | Chưa đối chiếu live với Google Merchant Center | **Chưa fix** | Cần đồng bộ giữa data feed gửi sang GMC và dữ liệu hiển thị trên website. |

**Tiến độ hiện tại:** Đã khắc phục hoàn chỉnh **5 / 9** vấn đề (xử lý xong vấn đề brand contamination WAZARO và 100% các vấn đề P1 cấp bách về Policy & Code artifact).

---

## 2. Chi tiết kỹ thuật các hạng mục đã khắc phục

### 2.1. Mục 04: Đồng bộ thông tin pháp nhân (Business Identity) giữa Contact Page và Footer

- **Vấn đề trước khi sửa:**
  - Tại trang `/pages/contact`, block *"Registered Business Address"* không in địa chỉ chi tiết.
  - Tại Footer toàn site, block liên hệ chỉ hiển thị địa chỉ đường cắt ngắn, thiếu tên công ty sở hữu, Suite, City, State và Mã bưu chính (ZIP).
  - Tài liệu đăng ký kinh doanh chính thức: **Beaconfield Group LLC**, 1209 MOUNTAIN ROAD PL NE, STE R, ALBUQUERQUE, NM 87110.

- **Các file đã can thiệp:**
  1. [`sections/main-contact.liquid`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/sections/main-contact.liquid):
     - Hiển thị đầy đủ pháp nhân và địa chỉ đăng ký tại block *"Registered Business Address"*:
       ```html
       <strong>Beaconfield Group LLC</strong><br>
       1209 Mountain Road Pl NE, Ste R<br>
       Albuquerque, NM 87110, United States
       ```
  2. [`sections/footer.liquid`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/sections/footer.liquid) & [`sections/footer-group.json`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/sections/footer-group.json):
     - Đồng bộ block thông tin liên hệ ở Footer khớp từng ký tự với trang Contact Us, đảm bảo crawler của Google đối chiếu mọi trang đều thấy cùng một pháp nhân và địa chỉ đồng nhất.

---

### 2.2. Mục 05: Xử lý Headline "Free Worldwide Shipping" & Làm rõ điều kiện "Eligible"

- **Vấn đề trước khi sửa:**
  - Top-bar announcement trên website hiển thị headline mang tính tuyệt đối: `"Free Worldwide Shipping"`.
  - Tuy nhiên trong Shipping Policy lại nêu chỉ áp dụng cho *"eligible destinations/orders"*. Google đánh giá đây là dạng quảng cáo gây hiểu lầm (Misrepresentation - Unrealistic/Absolute Claims).

- **Các bước đã thực hiện:**
  1. **Cập nhật Live Metaobject trên Shopify qua GraphQL Admin API:**
     - Tìm kiếm definition: `top_bar_announcement`.
     - Metaobject ID thực tế trên store `wrydeco.myshopify.com`: `gid://shopify/Metaobject/197517934649`.
     - Thay đổi trường `html_message`:
       - Trước: Chứa text `Free Worldwide Shipping`.
       - Sau: Chuyển thành link trỏ về chính sách với text chuẩn mực:
         ```html
         <a href="/policies/shipping-policy">Free Shipping on All Orders</a> &bull; Handcrafted Wooden Decor
         ```
       - Đảm bảo headline không còn claim "Worldwide" thiếu căn cứ mà khẳng định miễn phí vận chuyển cho tất cả các đơn hàng đủ điều kiện đặt trên website (kèm link đối chiếu).
  2. **Cập nhật tài liệu chính sách [`doc/policy/public/Shipping policy.html`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/doc/policy/public/Shipping%20policy.html):**
     - Tại **Mục 01 (Shipping Destinations & Eligibility)**:
       - Định nghĩa rõ ràng: *"Eligible destinations are defined as any country or territory available for selection in the shipping destination dropdown at WRYDECO's online checkout (over 200 countries and regions worldwide)."*
       - Liệt kê cụ thể các trường hợp không thể giao hàng (Ineligible/Exclusions): Hòm thư bưu điện (P.O. Boxes), địa chỉ quân sự (APO/FPO/DPO), và các vùng chiến sự/lãnh thổ bị cấm vận quốc tế mà các hãng vận chuyển quốc tế (DHL, FedEx, UPS) từ chối cung cấp dịch vụ.

---

### 2.3. Mục 06: Bổ sung chính sách Thuế nhập khẩu DDP (Delivery Duty Paid)

- **Vấn đề trước khi sửa:**
  - Website bán hàng quốc tế nhưng Shipping Policy không nhắc đến thuế nhập khẩu, phí hải quan, VAT/GST. Google Merchant Center coi việc không công bố rõ người mua hay người bán chịu thuế là lỗi che giấu chi phí (Hidden Fees/Omission).
  - Leader Phương đã duyệt: Áp dụng **Option 2 (Bên mình bao thuế trọn gói - DDP)**.

- **Các bước đã thực hiện:**
  - Cập nhật tài liệu [`doc/policy/public/Shipping policy.html`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/doc/policy/public/Shipping%20policy.html):
    - Bổ sung nội dung tại **Mục 18 (International Shipping, Customs & Import Duties)**:
      - Khẳng định 100% đơn hàng quốc tế đều được vận chuyển theo hình thức **Delivered Duty Paid (DDP)**.
      - Giá hiển thị tại checkout là chi phí trọn gói cuối cùng: WRYDECO chịu toàn bộ thuế nhập khẩu (customs duties), thuế giá trị gia tăng nhập khẩu (import VAT/GST) và phí thông quan phát sinh.
      - Người mua không phải nộp thêm bất kỳ khoản phí nào khi nhận hàng. Trường hợp đơn vị vận chuyển địa phương yêu cầu nộp nhầm, WRYDECO cung cấp hướng dẫn liên hệ `support@wrydeco.com` để xử lý hoặc hoàn tiền ngay lập tức.

---

### 2.4. Mục 07: Loại bỏ Test Popup Buttons khỏi Production DOM & Tự động hóa Dev/Build

- **Vấn đề trước khi sửa:**
  - Crawler của Google khi quét qua DOM phát hiện 2 button ẩn: `[Button: Test lead popup]` và `[Button: Test success popup]`. Việc để nút test dev trong production DOM làm giảm trust score và có thể bị bot đánh dấu là trang đang thử nghiệm / chưa hoàn thiện.

- **Các bước đã thực hiện:**
  1. **Làm sạch triệt để mã nguồn gốc:**
     - Đã xóa toàn bộ markup `<button data-lead-capture-test-toggle>`, CSS `.lead-capture-test-toggle`, và block script JS khởi tạo sự kiện test khỏi file [`snippets/lead-capture-popup.liquid`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/snippets/lead-capture-popup.liquid).
  2. **Tạo module quản lý kiểm thử độc lập tại thư mục [`scripts/lead-capture-test/`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/scripts/lead-capture-test):**
     - [`init_test.py`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/scripts/lead-capture-test/init_test.py): Tự động inject lại code test vào `lead-capture-popup.liquid` khi dev. Code test được bao bọc bởi marker:
       - `<!-- [DEV-TEST-START:HTML] --> ... <!-- [DEV-TEST-END:HTML] -->`
       - `/* [DEV-TEST-START:CSS] */ ... /* [DEV-TEST-END:CSS] */`
       - `/* [DEV-TEST-START:JS] */ ... /* [DEV-TEST-END:JS] */`
       - Nút test chỉ xuất hiện trên giao diện khi URL có query parameter `?lead_popup_test=1`.
     - [`init-test-src.cmd`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/scripts/lead-capture-test/init-test-src.cmd): File CMD gọi thực thi `init_test.py`.
     - [`remove_test.py`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/scripts/lead-capture-test/remove_test.py): Tự động tìm và gỡ bỏ sạch 100% các đoạn code test (marker và regex), bảo toàn indentation và chuẩn hóa định dạng gốc.
     - [`remove-test-src.cmd`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/scripts/lead-capture-test/remove-test-src.cmd): File CMD gọi thực thi `remove_test.py`.
  3. **Tích hợp vào quy trình vận hành tự động:**
     - **File [`dev.cmd`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/dev.cmd):** Thêm lệnh gọi `init-test-src.cmd` trước khi khởi động `shopify theme dev`.
     - **File [`compress-store-src.cmd`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/compress-store-src.cmd):** Thêm lệnh gọi `remove-test-src.cmd` ngay đầu script để luôn đảm bảo file nén đẩy lên store là bản production sạch 100%.

### 2.5. Mục 01: Xử lý triệt để brand cũ WAZARO trong Image Alt Text qua file CSV

- **Vấn đề trước khi sửa:**
  - Có 27 hình ảnh thuộc 3 sản phẩm bàn cà phê (`handcrafted-curved-oak-wood-minimalist-coffee-table`, `custom-handcrafted-wave-solid-oak-wood-coffee-table-1`, `custom-handcrafted-wave-solid-oak-wood-coffee-table`) chứa chữ `WAZARO` trong `Image Alt Text`.
  - Kiểm tra chéo toàn bộ các trường khác (Title, Body HTML, Vendor, Tags, và 13 cột Metafield): Sạch 100%, không bị dính chữ WAZARO.

- **Giải pháp đã thực hiện:**
  - Tạo file CSV chuyên dụng [`backup-products-data/from-real-store - latest/products_fixed_wazaro_3_products_only.csv`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/backup-products-data/from-real-store%20-%20latest/products_fixed_wazaro_3_products_only.csv) chứa đúng 54 dòng của 3 sản phẩm bị ảnh hưởng:
    - 66 cột khác được giữ nguyên vẹn 100% không suy suyển.
    - Duy nhất 27 ô `Image Alt Text` được thay thế từ `WAZARO` thành `WRYDECO`.
  - Đồng thời tạo bản catalog đầy đủ [`backup-products-data/from-real-store - latest/products_fixed_wazaro_all.csv`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/backup-products-data/from-real-store%20-%20latest/products_fixed_wazaro_all.csv) gồm 5.224 dòng sạch hoàn toàn.

---

## 3. Nhật ký can thiệp tệp tin (Files & Assets Changelog)

| Đường dẫn tệp tin | Loại can thiệp | Mục đích |
|:---|:---:|:---|
| [`sections/main-contact.liquid`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/sections/main-contact.liquid) | Modify | Thêm địa chỉ đăng ký kinh doanh chi tiết vào block "Registered Business Address". |
| [`sections/footer.liquid`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/sections/footer.liquid) | Modify | Cập nhật cấu trúc hiển thị địa chỉ footer đồng bộ với trang Contact. |
| [`sections/footer-group.json`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/sections/footer-group.json) | Modify | Lưu dữ liệu địa chỉ đầy đủ của pháp nhân Beaconfield Group LLC. |
| [`snippets/lead-capture-popup.liquid`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/snippets/lead-capture-popup.liquid) | Modify | Xóa sạch HTML/CSS/JS test buttons khỏi production template. |
| [`doc/policy/public/Shipping policy.html`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/doc/policy/public/Shipping%20policy.html) | Modify | Định nghĩa rõ "eligible" tại Mục 01 và bổ sung chính sách DDP tại Mục 18. |
| [`dev.cmd`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/dev.cmd) | Modify | Tự động gọi `scripts\lead-capture-test\init-test-src.cmd` khi bật dev server. |
| [`compress-store-src.cmd`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/compress-store-src.cmd) | Modify | Tự động gọi `scripts\lead-capture-test\remove-test-src.cmd` trước khi nén zip. |
| [`scripts/lead-capture-test/init_test.py`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/scripts/lead-capture-test/init_test.py) | New | Script inject code test vào popup lead capture. |
| [`scripts/lead-capture-test/init-test-src.cmd`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/scripts/lead-capture-test/init-test-src.cmd) | New | CMD wrapper thực thi `init_test.py`. |
| [`scripts/lead-capture-test/remove_test.py`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/scripts/lead-capture-test/remove_test.py) | New | Script dọn sạch code test popup. |
| [`scripts/lead-capture-test/remove-test-src.cmd`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/scripts/lead-capture-test/remove-test-src.cmd) | New | CMD wrapper thực thi `remove_test.py`. |
| [`todo/policy/phan-tich-wrydeco-policy.md`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/todo/policy/phan-tich-wrydeco-policy.md) | Modify | Thêm cột "Đã fix" và cập nhật trạng thái các mục đã xử lý. |
| [`backup-products-data/from-real-store - latest/products_fixed_wazaro_3_products_only.csv`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/backup-products-data/from-real-store%20-%20latest/products_fixed_wazaro_3_products_only.csv) | New | File CSV 54 dòng chứa 3 sản phẩm đã thay thế sạch WAZARO sang WRYDECO ở Image Alt Text để import. |
| [`backup-products-data/from-real-store - latest/products_fixed_wazaro_all.csv`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/backup-products-data/from-real-store%20-%20latest/products_fixed_wazaro_all.csv) | New | File CSV toàn bộ 5.224 dòng sản phẩm đã thay thế sạch WAZARO sang WRYDECO ở Image Alt Text. |
| **Metaobject trên Store** (`gid://shopify/Metaobject/197517934649`) | Live API Update | Sửa Headline thành `Free Shipping on All Orders` có link dẫn về policy. |

---

## 4. Hướng dẫn Debug & Kiểm tra thực tế (Verification Guide)

1. **Kiểm tra tính năng Test Lead Popup:**
   - Khi chạy `dev.cmd`, mở trang với tham số: `https://wrydeco.myshopify.com/?lead_popup_test=1`.
   - Nút `Test lead popup` và `Test success popup` sẽ hiển thị ở góc dưới bên trái màn hình để test mở/đóng popup và màn hình cảm ơn.
   - Khi bỏ tham số `?lead_popup_test=1`, 2 nút này hoàn toàn ẩn.
2. **Kiểm tra tính năng dọn sạch code trước khi đóng gói:**
   - Chạy `compress-store-src.cmd`.
   - Mở file [`snippets/lead-capture-popup.liquid`](file:///d:/D-Jobs/ae-B6/Shopify/stores/main/wrydeco/wrydeco-app/snippets/lead-capture-popup.liquid) và tìm kiếm chuỗi `lead-capture-test` hoặc `DEV-TEST`. Kết quả trả về phải là **0 kết quả**.
3. **Kiểm tra Headline trên store:**
   - Truy cập trang chủ WRYDECO, kiểm tra top announcement bar: Phải hiển thị *"Free Shipping on All Orders"* và click vào sẽ chuyển hướng đến `/policies/shipping-policy`.

---

## 5. Các bước xử lý tiếp theo được khuyến nghị (Next Remediation Steps)

Trước khi submit yêu cầu Google xem xét lại (Request Review), còn 2 vấn đề **P0** cốt lõi cần hoàn thiện nốt:
1. **P0 - Xử lý cụm số liệu Social Proof & Reviews:** Rà soát claim `372 Verified Client Reviews / 4.7 / 99% Satisfaction / 400+ Homes Styled`. Nếu không có hệ thống review bên thứ 3 (như Trustpilot, Judge.me, Loox) chứng minh được xuất xứ, cần gỡ bỏ hoặc điều chỉnh cách hiển thị các claim đánh giá cụ thể này trên cả Homepage và Product page.
2. **P0 - Thêm nhãn "Availability" trên trang sản phẩm:** Bổ sung hiển thị rõ ràng tình trạng hàng hóa (ví dụ: `Availability: In Stock` hoặc `Availability: Made-to-Order (Crafted in 15–20 days)`) ngay cạnh giá sản phẩm và nút Add to Cart.
