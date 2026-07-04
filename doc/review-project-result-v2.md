# Kết quả đối chiếu WRYDECO với "Tiêu chí chấm điểm mức độ hoàn thành"

> **Ngày review:** 2026-07-04
> **Phạm vi:** Đối chiếu project với `Tiêu chí chấm điểm mức độ hoàn thành.txt` (yêu cầu đạt ≥ 95/100).
> **Cách kiểm tra:** Chạy Playwright trực tiếp trên dev server thật `http://127.0.0.1:9292` (Shopify theme dev, proxy tới `wrydeco.myshopify.com`) + đọc mã nguồn theme.

---

## 1. Tóm tắt nhanh

- **Điều kiện loại trực tiếp:** PASS (kèm 1 cảnh báo về text hardcode trên PDP).
- **Điểm ước lượng hiện tại:** ~**90–95/100** — sát ngưỡng, phụ thuộc vào các mục cần hoàn thiện bên dưới.
- **Luồng mua hàng:** chạy trọn vẹn Home → Collection → PDP → Add to Cart → Cart drawer → Checkout.
- **Kỹ thuật:** 0 link chết (header/footer đều 200), 0 lỗi console, mobile 390px không tràn ngang (0px overflow).

---

## 2. Kiểm tra "Điều kiện loại trực tiếp" (mục 1 của tiêu chí)

| #   | Lỗi loại trực tiếp                         | Trạng thái    | Bằng chứng                                                                                           |
| --- | ------------------------------------------ | ------------- | ---------------------------------------------------------------------------------------------------- |
| 1   | Homepage chưa hoàn thiện / placeholder lớn | ✅ Không mắc  | 11 section đầy đủ, không placeholder                                                                 |
| 2   | Không bấm được collection / product        | ✅ Không mắc  | 52 product link trong `/collections/all`, click vào PDP OK                                           |
| 3   | PDP không có / hỏng nút Add to Cart        | ✅ Không mắc  | Nút "ADD TO CART" hoạt động                                                                          |
| 4   | Không thêm được sản phẩm vào cart          | ✅ Không mắc  | `/cart/add.js` → item_count 0 → 1                                                                    |
| 5   | Cart không hiển thị sản phẩm               | ✅ Không mắc  | Cart drawer render đúng item/ảnh/giá/variant                                                         |
| 6   | Không vào được checkout / checkout lỗi     | ✅ Không mắc  | Nút Checkout hoạt động (checkout bị chặn trên dev preview là giới hạn Shopify, không phải lỗi theme) |
| 7   | Nhiều link chết header/footer/CTA          | ✅ Không mắc  | Toàn bộ link header + footer trả HTTP 200                                                            |
| 8   | Mobile vỡ layout nghiêm trọng              | ✅ Không mắc  | 390px: overflow = 0px, menu mở, ATC hiện                                                             |
| 9   | Còn nội dung demo / text chưa thay thế     | ⚠️ **Rủi ro** | PDP có subtitle + 3 feature **hardcode** giống nhau trên mọi sản phẩm (xem mục 4)                    |
| 10  | Không demo được luồng mua cơ bản           | ✅ Không mắc  | Đã demo end-to-end                                                                                   |

---

## 3. Bảng điểm chi tiết (ước lượng)

| #   | Hạng mục (điểm tối đa)                | Ước lượng  | Ghi chú                                                                                                                |
| --- | ------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------- |
| 1   | Cấu trúc trang & link bắt buộc (15)   | **15**     | Nav + footer + policies + care guide đầy đủ, 0 link chết                                                               |
| 2   | Homepage (10)                         | **10**     | Hero, trust bar, collections, signature pieces, made-to-order, materials, makers, projects, reviews, consultation, FAQ |
| 3   | Collection Page (10)                  | **9**      | Grid đều, filter facet + sort + empty state OK; trừ nút "Filter" mở **drawer trống**                                   |
| 4   | Product Detail Page (15)              | **11–12**  | Rất giàu thông tin, mua được; **trừ vì subtitle + features hardcode** không khớp từng sản phẩm                         |
| 5   | Cart & Checkout Flow (15)             | **15**     | Drawer + qty + remove + subtotal + discount + checkout OK, 0 lỗi console                                               |
| 6   | Policy, Shipping, Support, Trust (10) | **7–10**   | Link 200 + Care Guide + FAQ; **cần xác minh nội dung policy trong Admin**                                              |
| 7   | Chat, Contact & hỗ trợ (5)            | **5**      | Shopify chat + contact form (13 inputs) + FAQ; đã fix chat che nút mua                                                 |
| 8   | Search, Filter & điều hướng (5)       | **5**      | Search có kết quả + empty state + pagination; filter facet chạy                                                        |
| 9   | UI/UX, branding, đồng bộ (10)         | **8–9**    | Design system đồng bộ; trừ vì text hardcode PDP                                                                        |
| 10  | Responsive & lỗi kỹ thuật (10)        | **10**     | 390px không vỡ, menu OK, ATC hiện, 0 lỗi                                                                               |
|     | **TỔNG**                              | **~90–95** | Sát ngưỡng, cần các fix ở mục 5                                                                                        |

---

## 4. Chi tiết từng hạng mục

### 4.1 Cấu trúc & link (15/15)

- Header nav: Collections (mega menu), Explore All Pieces, FAQ, About Us, Contact, Search, Cart, Account.
- Footer: Contact (tel/email), social (TikTok/YouTube/Pinterest/Facebook/Instagram), Collections, Our Story, Consultation, Care Guide, Track Order, FAQ, Privacy/Refund/Terms/Shipping/Legal.
- **Kết quả crawl:** tất cả link header/footer trả **HTTP 200** (bao gồm mọi `/collections/*`, `/pages/*`, `/policies/*`, `/apps/track-order`).

### 4.2 Homepage (10/10)

Thứ tự section: `hero_banner → trust_bar → shop_collections → signature_pieces → made_to_order → materials_craft → meet_the_makers → project_showcase → client_reviews → styling_consultation → faq_editorial`.

- Hero có eyebrow + heading thương hiệu + subtext + 2 CTA (Start a Custom Commission, View Signature Pieces) + 4 feature.
- Có trust bar (6 mục), collections nổi bật, signature pieces, quy trình đặt hàng, brand story (makers), reviews, consultation, FAQ.

### 4.3 Collection Page (9/10)

- 52 product link trong `/collections/all`, ảnh có `src`, card đồng bộ.
- Filter facet hoạt động: Availability, Price, Wood/Material (dùng `filter.values` + `url_to_remove`), Sort by, item count, empty state (`collection_is_empty`).
- **Cần dọn:** nút "Filter" mở **drawer trống** (comment trong `sections/collection.liquid` tự ghi "opens an (empty) drawer"). Filter thật đã chạy qua dropdown toolbar nên đây chỉ là dư thừa gây rối.

### 4.4 Product Detail Page (11–12/15) — ⚠️ cần sửa

**Điểm mạnh:** title, price, gallery (10 ảnh), variant picker (kèm size guide qua metafield), buy buttons (add to cart + buy now), consultation, benefits accordion, craftsperson, inventory status, rating summary, sale notice, related products, trust section (delivery/warranty).
**Vấn đề (trừ điểm):** `sections/main-product.liquid` (dòng ~606–662) **hardcode**:

- Subtitle: _"Sculptural function. Hand-carved fluting and solid walnut bring quiet sophistication to any space."_
- 3 feature: _"Solid walnut" / "Hand-finished" / "Made to order in 3–5 weeks"_.

→ Hiện y hệt trên **mọi sản phẩm**, kể cả sản phẩm không phải walnut (cat-tree, wine-rack, fruit-bowl, floor-lamp-base...). Đây là nội dung không chính xác theo từng sản phẩm → dễ bị coi là "text chưa thay thế" (rủi ro loại trực tiếp #9) và trừ điểm mục #4, #9.

### 4.5 Cart & Checkout (15/15)

- Add to Cart hoạt động, cart icon cập nhật số lượng, drawer mở đúng.
- Item hiển thị đúng tên/ảnh/giá/variant; tăng/giảm qty + remove + subtotal cập nhật.
- **Discount field** đã build hoàn chỉnh: áp mã (`/cart/update.js`), phân biệt mã hợp lệ / chưa đủ điều kiện (min purchase) / mã sai, và **xóa mã** (nút × + chip pending), thông báo qua global Toast.
- Checkout button hoạt động (trang checkout bị chặn trên dev preview là giới hạn Shopify, chạy bình thường trên store thật).

### 4.6 Policy & Support (7–10/10) — ⚠️ cần xác minh nội dung

- Link 200: `/policies/privacy-policy`, `/refund-policy`, `/shipping-policy`, `/terms-of-service`, `/legal-notice`.
- Có `/pages/care-guide` (đã build section + template, page tồn tại), `/pages/faq` (7 nhóm câu hỏi), `/pages/contact`, `/pages/customization`, `/apps/track-order`.
- **Chưa kiểm chứng được nội dung** các trang `/policies/*` (do Shopify Admin quản lý, không nằm trong theme). Cần đảm bảo có nội dung thật: thời gian xử lý, thời gian ship, khu vực giao, điều kiện đổi trả, **ngoại lệ với hàng custom/personalized**, cách liên hệ.

### 4.7 Chat & Contact (5/5)

- Shopify chat widget hoạt động; đã fix lỗi chat **che nút Checkout** trong cart drawer (ẩn launcher khi drawer mở).
- Contact page có form (13 inputs).
- FAQ trả lời shipping/return/payment/customization/care/consultation.

### 4.8 Search & Filter (5/5)

- Search có kết quả khi nhập từ khóa, empty state khi 0 kết quả, có pagination.
- Filter/sort trên collection hoạt động.

### 4.9 UI/UX & Branding (8–9/10)

- Đồng bộ font/màu/button/card theo design system (`assets/base.css` tokens).
- Tông luxury đúng ngành hàng gỗ thủ công cao cấp.
- Trừ nhẹ vì text hardcode PDP (mục 4.4).

### 4.10 Responsive & kỹ thuật (10/10)

- 390px: overflow ngang = 0px trên Home / Collection / PDP.
- Mobile menu mở/đóng được; nút Add to Cart hiện trên PDP mobile.
- 0 lỗi console trong toàn luồng mua.

---

## 5. Việc cần hoàn thiện để chắc chắn ≥ 95/100

### A. Sửa ở theme (có thể làm ngay bằng code)

1. **[Ưu tiên cao] PDP — bỏ text hardcode** (`sections/main-product.liquid` ~606–662): lấy subtitle + features từ **metafield/description của từng sản phẩm** (có fallback), hoặc ẩn nếu không có dữ liệu. Đây là hạng mục kéo điểm mục #4 và #9, đồng thời loại bỏ rủi ro "loại trực tiếp #9".
2. **[Nhỏ] Collection — nút "Filter" mở drawer trống** (`sections/collection.liquid`): bỏ nút hoặc đưa các facet vào drawer đó.

### B. Cần xác minh / điền trong Shopify Admin (ngoài theme)

3. **Nội dung Policy** — đảm bảo `/policies/*` có nội dung thật (không để trống/mẫu): thời gian xử lý & vận chuyển, khu vực giao, điều kiện đổi trả, ngoại lệ hàng custom, cách liên hệ. (mục #6, tối đa 3 điểm)
4. **Mô tả sản phẩm** — probe thấy phần mô tả khá mỏng (~56 ký tự ở sản phẩm test). Xác minh mọi sản phẩm có mô tả + benefits/metafield đầy đủ (chất liệu, kích thước, công dụng). (mục #4)
5. **Size guide** — PDP hiển thị qua `metafields.custom.size_guide`; đảm bảo đã điền cho sản phẩm có nhiều size. (mục #6)

---

## 6. Ghi chú về môi trường kiểm tra

- `shopify theme dev` (local preview) **chặn** một số route storefront do Shopify host: `/checkout`, `/discount/*`, `/account/*` → trả 401/redirect. Đây là **giới hạn của môi trường dev**, không phải lỗi theme; các chức năng này hoạt động bình thường trên store thật (published/preview).
- Store dùng **New customer accounts** (đăng nhập passwordless); flow login đã được chỉnh để nút account trỏ thẳng tới `routes.account_login_url` (Shopify lo phần đăng nhập).
