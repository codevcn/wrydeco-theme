# WRYDECO Theme — SEO Diagnosis

> **Trạng thái cập nhật (2026-07-07):** đã hoàn thành #1, #2, #3, #5, #8, #9 (thuần local, đã áp dụng lại
> sau lần revert). #4 chờ tạo metafield trong Shopify Admin. #6, #7 (blog/article) chưa xử lý.

> Đánh giá độ chuẩn SEO của theme theo skill `optimize-seo-ssr-coding` (SSR-first technical SEO).
> Phạm vi khảo sát: `layout/theme.liquid`, `snippets/meta-tags.liquid`, `sections/main-product.liquid`,
> `snippets/product-media-gallery.liquid`, `sections/collection.liquid`, `sections/collection-banner.liquid`,
> `sections/article.liquid`, `sections/header.liquid`, các template JSON (`product.json`, `collection.json`, `index.json`).

---

## Tổng quan

Theme **về cơ bản đúng hướng SSR-first** — điểm mạnh nhất theo skill. Toàn bộ nội dung chính
(tên/giá/mô tả/ảnh sản phẩm, tiêu đề collection, breadcrumb, internal links) render bằng Liquid trên server,
không có "CSR red flag" cho nội dung cốt lõi.

**Đã đạt chuẩn:**

- `meta-tags.liquid`: canonical (dùng `canonical_url`), Open Graph, Twitter card, JSON-LD sản phẩm,
  `og:price`, title xử lý pagination/tags.
- `collection-banner.liquid`: H1 = `collection.title`, breadcrumb link thật, render `collection.description`.
- `product-media-gallery.liquid`: ảnh chính `eager` + `fetchpriority:high`, các ảnh còn lại `lazy`,
  có `alt` + `widths/sizes`.
- `collection.liquid`: product card là `<a href>` thật, ảnh `lazy` + responsive, pagination self-referencing
  (không gộp về page 1 — đúng skill mục 9.3).
- `product.description` có mặt trong HTML server-render (accordion trong `product-comparison`).

Vấn đề chủ yếu: **semantic HTML (heading), duplicate structured data, và nội dung hardcoded trùng lặp giữa các sản phẩm.**

---

## 🔴 Critical — cần sửa

### 1. Hai thẻ `<h1>` trên mọi trang (heading structure sai) — ✅ DONE
- **File:** `sections/header.liquid:3`
- **Vấn đề:** logo bọc trong `<h1 class="header__heading">`. Section chạy trên **mọi** trang → trang
  product/collection/article vốn đã có H1 riêng sẽ bị **2 H1**, vi phạm skill mục 11.2 ("one clear h1").
- **Giải pháp:** chỉ dùng `<h1>` cho logo ở trang chủ; các trang khác dùng `<div>`/`<p>`.
  Ví dụ: `{% if request.page_type == 'index' %}<h1 …>{% else %}<div …>{% endif %}` (pattern chuẩn Dawn).
- **Đã làm:** wrapper logo dùng biến `header_heading_tag` = `h1` khi `request.page_type == 'index'`,
  ngược lại `div` (giữ nguyên class `header__heading`, không đổi `display` → hợp Rule 5).

### 2. JSON-LD Product render trùng 2 lần — ✅ DONE
- **File:** `snippets/meta-tags.liquid:66` và `sections/main-product.liquid:970`
- **Vấn đề:** `{{ product | structured_data }}` xuất hiện 2 lần → duplicate structured data,
  dễ gây cảnh báo trong Google Search Console.
- **Giải pháp:** giữ 1 bản (nên giữ ở `meta-tags.liquid` trong `<head>`), xoá bản trong `main-product.liquid`.
- **Đã làm:** xoá block ld+json trong `main-product.liquid` (thay bằng comment cảnh báo); JSON-LD chỉ còn
  1 nơi trong `<head>`.

---

## 🟠 Content & Semantic — duplicate content (cũng đụng Rule 4 — Business tone)

### 3. Subtitle sản phẩm hardcode giống hệt trên mọi PDP — ✅ DONE
- **File:** `sections/main-product.liquid:671-673`
- **Vấn đề:** *"Sculptural function. Hand-carved fluting and solid walnut…"* giống nhau ở **mọi** sản phẩm,
  sai với sản phẩm không phải walnut → duplicate content + thông tin sai lệch.
- **Giải pháp:** đọc từ metafield (vd `product.metafields.custom.subtitle`) hoặc excerpt của `product.description`,
  ẩn nếu blank.
- **Đã làm:** thay text cứng bằng `product.description | strip_html | strip`, ẩn nếu blank; CSS clamp
  **2 dòng + ellipsis** (`-webkit-line-clamp: 2` + `line-clamp: 2`). Mô tả đầy đủ vẫn nằm ở accordion
  `product-comparison` nên không trùng nội dung. *(Fallback theo `product.description` — chưa cần metafield.)*

### 4. Danh sách "features" hardcode giống nhau mọi sản phẩm — ⏳ PENDING (chờ metafield)
- **File:** `sections/main-product.liquid:678-728`
- **Vấn đề:** "Solid walnut / Hand-finished / Made to order in 3–5 weeks" cố định trên mọi PDP.
- **Giải pháp:** chuyển sang metafield theo từng sản phẩm hoặc block trong schema.
- **Trạng thái:** tạm để lại — cần tạo metafield definition trong Shopify Admin
  (Settings → Custom data → Products) + nhập dữ liệu cho từng sản phẩm; không làm được thuần local.

### 5. H2 "Why You Choose This Masterpiece" hardcode + heading thừa — ✅ DONE
- **File:** `sections/main-product.liquid:773`
- **Vấn đề:** hardcode; trust panel có 2 `<h2>` (`trust-heading` + `trust-subheading`) hơi thừa/lặp.
- **Giải pháp:** đưa nội dung vào schema settings, giữ 1 H2 logic cho khối này.
- **Đã làm:** xoá `<header class="main-product__trust-header">` (khối `display:none` chứa H2 ẩn trùng)
  → còn **1 H2**; H2 hiển thị lấy text từ setting mới `trust_subheading`, giữ `id` + `aria-labelledby`.
  Gỡ 2 setting cũ (`trust_eyebrow`, `trust_heading`) và dọn CSS mồ côi (`trust-header/eyebrow/heading/ornament*`)
  ở cả 3 breakpoint.
- **Lưu ý:** trong Theme Editor 2 ô "Eyebrow"/"Heading" cũ biến mất, thay bằng "Subheading"
  (giá trị tùy chỉnh cũ nếu có sẽ mất — nhưng chúng vốn đang `display:none`).

### 6. `article.liquid` quá sơ sài cho SEO/EEAT
- **File:** `sections/article.liquid`
- **Vấn đề:** section mặc định — không có wrapper `<article>`, ảnh không `alt`/`width`/`height`,
  không breadcrumb, không `article:published_time`.
- **Giải pháp:** bọc `<article>`, thêm alt + dimensions cho `article.image`, thêm breadcrumb +
  hiển thị author/date (skill mục 23). *(Ưu tiên tùy mức độ dùng blog.)*

---

## 🟡 Image / Metadata — nhẹ

### 7. Ảnh article thiếu alt/dimensions
- **File:** `sections/article.liquid:10`
- **Vấn đề:** `article.image` render không `alt`/`width`/`height`/`loading` → CLS + thiếu alt.

### 8. Bug fallback alt ở card sản phẩm — ✅ DONE
- **File:** `sections/collection.liquid:441` (cùng pattern `sections/header.liquid:14-15`)
- **Vấn đề:** `alt: media.alt | default: product.title` — filter `| default:` áp lên **output của `image_tag`**
  (chuỗi `<img>` không bao giờ blank), nên khi `media.alt` rỗng thì alt thành rỗng chứ không fallback.
- **Giải pháp:** tính fallback vào biến trước: `{% assign card_alt = media.alt | default: product.title %}`
  rồi truyền `alt: card_alt`.
- **Đã làm:** thêm `card_alt` trong `collection.liquid` và bỏ `| default:` sai chỗ. Đồng thời vá luôn pattern
  tương tự cho logo trong `header.liquid` (biến `logo_alt`).

### 9. `og:image` chính dùng `http:` — ✅ DONE
- **File:** `snippets/meta-tags.liquid:47`
- **Vấn đề:** URL `og:image` chính dùng `http:` (dù đã có `og:image:secure_url`).
- **Giải pháp:** đổi sang `https:` hoặc protocol-relative.
- **Đã làm:** đổi `content="http:{{ page_image | image_url }}"` → `https:`.

---

## 🟢 Crawl files & ghi chú

- **`robots.txt` / `sitemap.xml`:** không có file tùy biến — **đúng và ổn**, Shopify tự sinh cả hai +
  tự thêm canonical. Chỉ cần tạo `templates/robots.txt.liquid` nếu sau này muốn chặn crawl trang filter mỏng.
- **`product-recommendations`:** dùng object `recommendations` (server-side khi section load qua Recommendations API)
  — không phải nội dung SEO-critical, chấp nhận được.
- **Dead code:** `sections/product.liquid` (section mặc định cũ, không nằm trong `product.json`) — vô hại nhưng
  gây nhiễu, nên xoá.

---

## Thứ tự thực hiện đề xuất

1. ✅ **#1 (double-H1)** và **#2 (duplicate JSON-LD)** — DONE.
2. ✅ **#3, #5** (subtitle + H2 hardcode) — DONE. ⏳ **#4** (features) — chờ metafield ở Admin.
3. ✅ **#8** (alt fallback), **#9** (`og:image` https) — DONE. ⬜ **#6, #7** (article + ảnh) — chưa làm.

### Tiến độ

| # | Mức độ | Trạng thái |
|---|--------|-----------|
| 1 | 🔴 Critical | ✅ DONE |
| 2 | 🔴 Critical | ✅ DONE |
| 3 | 🟠 Content | ✅ DONE (fallback `product.description`) |
| 4 | 🟠 Content | ⏳ PENDING — chờ tạo metafield trong Shopify Admin |
| 5 | 🟠 Content | ✅ DONE |
| 6 | 🟠 Semantic | ⬜ Chưa làm (article) |
| 7 | 🟡 Image | ⬜ Chưa làm (ảnh article) |
| 8 | 🟡 Image | ✅ DONE |
| 9 | 🟡 Metadata | ✅ DONE |

**Lưu ý triển khai (theo `CODING_RULES.md`):**
- Sửa `header.liquid` **không** đổi `display` của wrapper (Rule 5).
- Style mới dùng biến trong `assets/base.css` (Rule 3).
- Nội dung UI giữ tiếng Anh (Rule 7).
- Nếu thêm icon → qua iconify MCP (Rule 9).
