# Kết quả review dự án WRYDECO theo "Tiêu chí chấm điểm mức độ hoàn thành"

> Ngày review: 2026-07-03 · Phương pháp: đọc source code (templates/sections/snippets) + kiểm chứng runtime bằng `curl` và Playwright trên `shopify theme dev` (localhost:9292).
> Mục tiêu đạt: **≥ 95/100** và không mắc lỗi loại trực tiếp.

---

## TL;DR — Ước lượng điểm & kết luận

| #   | Hạng mục                            | Điểm tối đa | Ước lượng | Ghi chú nhanh                                              |
| --- | ----------------------------------- | :---------: | :-------: | ---------------------------------------------------------- |
| 1   | Cấu trúc trang & link bắt buộc      |     15      |   **9**   | ❌ Nhiều link chết ở footer + thiếu Shipping/Refund policy |
| 2   | Homepage                            |     10      |  **10**   | Rất đầy đủ, không placeholder                              |
| 3   | Collection Page                     |     10      |  **10**   | Banner, grid, filter/sort, empty state, pagination         |
| 4   | Product Detail Page                 |     15      |  **14**   | Đầy đủ; đã fix giá theo variant, zoom, sticky add-to-cart  |
| 5   | Cart & Checkout                     |     15      |  **13**   | Chạy tốt; thiếu discount/note field                        |
| 6   | Policy / Shipping / Support / Trust |     10      |   **5**   | ❌ Thiếu Shipping Policy & Refund Policy (404)             |
| 7   | Chat / Contact / hỗ trợ             |      5      |   **3**   | Có contact form + FAQ + email; **không có live chat**      |
| 8   | Search / Filter / điều hướng        |      5      |   **5**   | Search page + filter/sort + popover đã fix                 |
| 9   | UI/UX, branding, đồng bộ            |     10      |  **10**   | Design system nhất quán                                    |
| 10  | Responsive & lỗi kỹ thuật           |     10      |  **10**   | Không tràn ngang; không lỗi console thật                   |
|     | **TỔNG**                            |   **100**   | **≈ 89**  |                                                            |

**Kết luận:** Dự án đang ở mức **~89/100 — CHƯA đạt 95**. Có **1 rủi ro loại trực tiếp**: _"nhiều link chết trong header/footer"_ (mục 1.7 của tiêu chí). Hai nhóm việc chính cần xử lý để vượt 95:

1. **Dọn/vá toàn bộ link chết** (footer collections, footer pages, social).
2. **Tạo Shipping Policy + Return/Refund Policy** (và các trang hỗ trợ đang 404).

> Lưu ý: phần lớn các thiếu sót là **dữ liệu/cấu hình trong Shopify Admin** (collections, pages, policies) chứ không phải lỗi code theme. Nhưng theo cách chấm, link chết vẫn bị trừ điểm/loại nên phải xử lý.

---

## 1. Điều kiện loại trực tiếp

| Điều kiện                                |     Trạng thái     | Bằng chứng                                                                                                                                                 |
| ---------------------------------------- | :----------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Homepage còn placeholder lớn          |      ✅ Không      | `templates/index.json` có 11 section nội dung thật (hero, trust, collections, signature, process, materials, makers, projects, reviews, consultation, faq) |
| 2. Không bấm được collection/product     |    ✅ Bấm được     | Header/homepage link tới collection & PDP hoạt động                                                                                                        |
| 3. PDP thiếu/hỏng nút Add to Cart        |    ✅ Có & chạy    | `snippets/product-buy-buttons.liquid` + `assets/product-form.js`                                                                                           |
| 4. Không add được vào cart               |    ✅ Add được     | Đã kiểm chứng bằng Playwright (badge 0→1→2)                                                                                                                |
| 5. Cart không hiển thị sản phẩm          |    ✅ Hiển thị     | `cart-drawer.liquid` render line items                                                                                                                     |
| 6. Không vào được checkout               | ✅ Có nút checkout | Cart page & drawer POST `name="checkout"` → Shopify checkout                                                                                               |
| 7. **Nhiều link chết header/footer/CTA** |     ❌ **CÓ**      | **≥ 14 link chết ở footer** (xem mục 2.1 bên dưới)                                                                                                         |
| 8. Mobile vỡ layout nghiêm trọng         |      ✅ Không      | Không trang nào tràn ngang ở 390px/1440px (Playwright)                                                                                                     |
| 9. Còn nội dung demo/Lorem ipsum         |  ⚠️ Gần như không  | Không có "Lorem"; nhưng social link = `#`, một số trang footer trỏ tới page chưa tồn tại                                                                   |
| 10. Không demo được luồng mua hàng       |    ✅ Demo được    | Home → Collection → PDP → Add to Cart → Cart → Checkout đều nối được                                                                                       |

> **Rủi ro loại trực tiếp đang tồn tại: điều kiện #7 (nhiều link chết).**

---

## 2. Phân tích chi tiết theo từng hạng mục

### 1) Cấu trúc trang & link bắt buộc — ~9/15

**Đã có (tốt):**

- Header: Home (logo), Collections (mega menu), category chính, About Us, FAQ, Contact, Search, Cart, Account (icon + trong drawer mobile). `sections/header.liquid`.
- Footer: About, Contact, FAQ, Blog, Privacy, Terms, email/phone, social. `sections/footer.liquid`.
- Templates Shopify quan trọng đều có: `index`, `collection`, `product`, `cart`, `search`, `page.contact`, `page.faq`, `page.about-us`, `page.customization`, `404`, `password`, `blog`, `article`, `list-collections`.

**❌ Link chết đã phát hiện (curl trên dev server):**

_Collection (footer "Shop"/"Browse"):_

- `/collections/dining-room-furniture` → **404**
- `/collections/living-room-furniture` → **404**
- `/collections/office` → **404**
- `/collections/wood-decor-accents` → **404**

_Pages (footer):_

- `/pages/care-guide`, `/pages/craftsmanship`, `/pages/materials`, `/pages/order-tracking`, `/pages/projects`, `/pages/sustainability`, `/pages/trade` → **404** (7 trang)

_Social (footer):_ Instagram / Pinterest / LinkedIn đều `href="#"` (3 link placeholder).

→ Tổng ~**14 link chết** ở footer. Đây là nguyên nhân chính khiến vướng điều kiện loại trực tiếp #7.

**Cách khắc phục:**

- Trong Shopify Admin: tạo lại các collection/pages tương ứng **HOẶC** cập nhật link trong `sections/footer.liquid` trỏ về các handle collection đang tồn tại (ví dụ: `signature-pieces`, `coffee-table`, `bedroom-furniture`, `storage-cabinet`, `wooden-plant-stand`...).
- Gắn URL social thật (hoặc ẩn icon social nếu chưa có kênh).

---

### 2) Homepage — ~10/10

- Hero banner + thông điệp thương hiệu + CTA "Start a Custom Commission" / "View Signature Pieces" (bấm được). `sections/hero-banner.liquid`.
- Trust bar 6 mục (ethical sourcing, handcrafted, made-to-order, delivery, 5-year warranty, support).
- Section collection nổi bật (`shop-collections`), sản phẩm nổi bật (`signature-pieces`).
- Quy trình đặt custom (`made-to-order-steps`), materials/personalization, Meet the Makers, project showcase, client reviews (testimonial), private consultation, FAQ editorial.
- Footer đầy đủ. Không placeholder, không lorem.

→ Homepage hoàn chỉnh, đáng tin. Các link collection trong section `shop_collections` hiện trỏ tới handle 200 OK.

---

### 3) Collection Page — ~10/10

`sections/collection-banner.liquid` + `sections/collection.liquid`:

- Title + banner + breadcrumb (đã fix vị trí/kích thước breadcrumb).
- Grid card đồng bộ (ảnh 6/5, tên, "Crafted By", giá "From").
- Filter (Availability, Price, Wood Type) + Sort (đã fix popover tràn màn hình; đã fix 2 card/hàng mobile).
- Empty state "This collection is being curated" (đã build theo design) + gợi ý collection khác.
- Pagination dạng pill.
- Responsive: 4→2→(giữ 2) cột.

---

### 4) Product Detail Page — ~14/15

`templates/product.json` gồm: `main-product`, `product-artist`, `judgeme-reviews`, `product-comparison` (Details/Materials/Care accordion), `product-recommendations` (Pairs Beautifully With), feature blocks, apps.

- Tên, giá (đã fix **giá + Save cập nhật tức thì theo variant**, không gọi API).
- Gallery + thumbnail + **zoom popup có lens box** (mới thêm).
- Variant picker (size/color/finish) + quantity.
- Add to Cart hoạt động; Buy It Now / dynamic checkout (`payment_button`).
- Mô tả + Dimensions + Delivery & Returns + Care Guide + Customization (accordion, mobile có "Read more").
- "Made to order in 3–5 weeks" (processing time); Size Guide popup; trust panel; related (Pairs) carousel; sticky Add-to-Cart mobile.

**Còn thiếu nhẹ:** một số thông tin shipping/return chỉ nằm trong accordion (không có badge nổi bật); đủ để không mất điểm nặng.

---

### 5) Cart & Checkout — ~13/15

`sections/cart-drawer.liquid` + `sections/cart.liquid`:

- Add to Cart từ PDP ✅; cart badge cập nhật (đã fix lỗi **badge mất số khi drawer mở**).
- Cart drawer mở được; line item hiển thị tên/ảnh/giá/variant.
- Tăng/giảm quantity ✅; Remove ✅; Subtotal cập nhật ✅.
- Nút Checkout ✅ (POST `name="checkout"` → Shopify checkout).
- Không lỗi console thật; không mất cart.

**Còn thiếu (đều là "nếu có"):**

- Không có **discount code field** trong cart.
- Không có **order note field** trong cart.
  → Không bắt buộc nhưng bổ sung sẽ tròn điểm hơn.

---

### 6) Policy / Shipping / Support / Trust — ~5/10 ⚠️ (điểm thấp nhất)

| Trang                                                |                                     Trạng thái                                     |
| ---------------------------------------------------- | :--------------------------------------------------------------------------------: |
| Privacy Policy (`/policies/privacy-policy`)          |                                       ✅ 200                                       |
| Terms of Service (`/policies/terms-of-service`)      |                                       ✅ 200                                       |
| **Shipping Policy** (`/policies/shipping-policy`)    |                                     ❌ **404**                                     |
| **Return/Refund Policy** (`/policies/refund-policy`) |                                     ❌ **404**                                     |
| Contact (`/pages/contact`)                           |                           ✅ 200 (form contact + toast)                            |
| FAQ (`/pages/faq`)                                   | ✅ 200 (đủ nhóm: orders, shipping, returns, materials, custom, care, consultation) |
| Track Order (`/pages/order-tracking`)                |                                     ❌ **404**                                     |
| Care Guide (`/pages/care-guide`)                     |                   ❌ **404** (nhưng PDP có accordion Care Guide)                   |
| Size Guide                                           |                          ✅ có popup trong variant picker                          |
| Customization Guide (`/pages/customization`)         |                                       ✅ 200                                       |

**Đây là nhóm kéo điểm nhiều nhất.** Tiêu chí yêu cầu rõ **Shipping Policy** và **Return/Refund Policy** — hiện cả hai đều 404. Footer trỏ tới `/policies/shipping-policy` & `/policies/refund-policy` (qua `shop.shipping_policy.url | default:`) nhưng policy chưa được set trong Admin nên link chết.

**Cách khắc phục (Shopify Admin → Settings → Policies):**

- Tạo **Shipping Policy** (thời gian xử lý, thời gian vận chuyển dự kiến, khu vực giao hàng, white-glove).
- Tạo **Refund/Return Policy** (điều kiện đổi trả, đặc biệt nêu rõ **hàng custom/bespoke không áp dụng đổi trả** — rất quan trọng với ngành custom furniture).
- Tạo page **Track Order** (hoặc bỏ link) và **Care Guide** page (nội dung đã có sẵn trong FAQ/accordion, chỉ cần tách trang).

---

### 7) Chat / Contact / hỗ trợ — ~3/5

- ✅ Contact page + form gửi được (Shopify `contact` form + toast), email `support@wrydeco.com`, giờ hỗ trợ.
- ✅ FAQ trả lời đủ shipping/return/payment/customization/care/consultation.
- ❌ **Không có live chat widget** (không tìm thấy tawk/crisp/messenger/gorgias...).
- Không có icon chat che CTA (vì không có chat) → không bị trừ phần "che nút mua".

**Gợi ý:** thêm 1 chat widget nhẹ (Tawk.to/Messenger) hoặc nút "Chat/WhatsApp" nổi để lấy đủ 5 điểm.

---

### 8) Search / Filter / điều hướng — ~5/5

- ✅ Search popup (predictive) + Search results page (`sections/search.liquid`) đã build lại theo design: hero, sort pills, grid/list toggle, pagination, empty state.
- ✅ Filter/sort trên collection hoạt động; popover đã fix tràn màn hình.
- ✅ Điều hướng quay lại collection/product dễ dàng.

---

### 9) UI/UX, branding, đồng bộ — ~10/10

- Design system tập trung ở `assets/base.css` (màu earth-brown/clay/cream, font Fraunces + Plus Jakarta + Roboto), dùng CSS variables xuyên suốt (tuân thủ `CODING_RULES.md`).
- Button/card/spacing đồng bộ; đúng tinh thần ngành furniture cao cấp (không "budget/discount").
- Header/footer cân đối; ảnh chất lượng, đúng tỉ lệ.

---

### 10) Responsive & lỗi kỹ thuật — ~10/10

- Không trang nào tràn ngang ở **1440px** và **390px** (kiểm chứng Playwright: home, collection, pdp, cart, search, contact, faq, 404).
- Mobile menu mở/đóng; account đưa vào drawer; product grid không vỡ; PDP có sticky Add-to-Cart mobile.
- **Lỗi console:** chỉ có artifact của môi trường `shopify theme dev` local (script `origin_trials-*.js` của Shopify CDN bị chặn CORS + favicon 404) — **không phải lỗi thật của theme**, sẽ không xuất hiện trên production domain.

---

## 3. Danh sách việc cần làm để đạt ≥ 95 (ưu tiên)

### 🔴 Bắt buộc (gỡ rủi ro loại trực tiếp + lấy lại điểm)

1. **Tạo Shipping Policy & Return/Refund Policy** trong Shopify Admin (nêu rõ điều kiện đổi trả cho hàng custom). → +4~5đ mục 6, gỡ 2 link chết.
2. **Sửa/dọn toàn bộ link chết ở footer** (`sections/footer.liquid`):
   - 4 collection 404 (dining-room / living-room / office / wood-decor-accents) → trỏ về handle đang tồn tại hoặc tạo lại collection.
   - 7 page 404 (care-guide, order-tracking, projects, sustainability, craftsmanship, materials, trade) → tạo page hoặc bỏ link.
   - 3 social `href="#"` → gắn URL thật hoặc ẩn.
     → gỡ điều kiện loại trực tiếp #7, +vài điểm mục 1.

### 🟡 Nên làm (tròn điểm)

3. Tạo page **Track Order** & **Care Guide** (nội dung đã có sẵn ở FAQ) — mục 6.
4. Thêm **live chat / nút WhatsApp** — mục 7 (+2đ).
5. Thêm **discount code field** và **note field** trong cart/drawer — mục 5.

### 🟢 Tùy chọn (đánh bóng)

6. Thêm badge shipping/return nổi bật trên PDP (ngoài accordion).
7. Rà lại các link mega-menu trỏ tới collection ít sản phẩm/ẩn để tránh trang trống.

---

## 4. Ghi chú phương pháp & giới hạn

- Kiểm chứng chạy trên `shopify theme dev` (dữ liệu store thật). Trạng thái collection/page/policy phản ánh **cấu hình Admin hiện tại** — có thể thay đổi nếu Admin được cập nhật.
- Checkout chỉ xác minh tới bước bấm nút (POST tới Shopify checkout); không đặt đơn thật để kiểm tra sâu trang checkout.
- Các fix code đã thực hiện trong các phiên trước (giá theo variant, cart badge, breadcrumb, popover filter, empty collection, contact page, search page, sticky add-to-cart, zoom lens...) đều đã pass Playwright.
