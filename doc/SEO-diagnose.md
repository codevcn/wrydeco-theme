# WRYDECO Theme — SEO Diagnosis

> **Trạng thái cập nhật (2026-07-08 — đọc lại toàn bộ src):** đã hoàn thành #1, #2, #3, #5, #9 (thuần local).
> #8 mới xong **một phần** (còn 3 chỗ). #4 chờ metafield ở Shopify Admin. #6, #7, #10, #11 chưa xử lý.

> Đánh giá độ chuẩn SEO của theme theo skill `optimize-seo-ssr-coding` (SSR-first technical SEO).
> Phạm vi khảo sát (đã đọc lại toàn bộ): `layout/theme.liquid`, `snippets/meta-tags.liquid`,
> `snippets/product-media-gallery.liquid`, và toàn bộ `sections/*.liquid` (product, collection, search,
> blog, article, page, header, hero-banner, các section trang chủ & customization…), các template JSON.

---

## Tổng quan

Theme **về cơ bản đúng hướng SSR-first** — điểm mạnh nhất theo skill. Toàn bộ nội dung chính
(tên/giá/mô tả/ảnh sản phẩm, tiêu đề collection, breadcrumb, internal links) render bằng Liquid trên server,
không có "CSR red flag" cho nội dung cốt lõi.

**Đã đạt chuẩn:**

- `meta-tags.liquid`: canonical (`canonical_url`), Open Graph, Twitter card, JSON-LD sản phẩm, `og:price`,
  title xử lý pagination/tags; `og:image` đã dùng `https:` (#9).
- `header.liquid`: logo chỉ là H1 ở trang chủ, các trang khác dùng `<div>` (#1) → mỗi trang 1 H1.
- `collection-banner.liquid`: H1 = `collection.title`, breadcrumb link thật, render `collection.description`.
- `product-media-gallery.liquid`: ảnh chính `eager` + `fetchpriority:high`, còn lại `lazy`, có `alt` + `widths/sizes`.
- `collection.liquid` / `search.liquid`: product card là `<a href>` thật, ảnh `lazy` + responsive,
  pagination self-referencing (không gộp về page 1 — đúng skill mục 9.3).
- Phần lớn section trang chủ/nội dung render ảnh có `alt` gán qua biến đúng cách
  (`product-recommendations`, `meet-the-makers`, `project-showcase`, `customization-*`, `main-contact`,
  `main-faq-page`, `collection-banner`, `404`, `cart-drawer`).
- `product.description` có mặt trong HTML server-render (accordion trong `product-comparison`).

Vấn đề chủ yếu còn lại: **một số bug fallback `alt`, nhiều ảnh nội dung thiếu `alt`, blog/article sơ sài,
search page chưa `noindex`, và features PDP hardcode (chờ metafield).**

---

## 🔴 Critical

### 1. Hai thẻ `<h1>` trên mọi trang (heading structure sai) — ✅ DONE
- **File:** `sections/header.liquid`
- **Vấn đề:** logo bọc trong `<h1 class="header__heading">` chạy trên **mọi** trang → PDP/collection/article
  bị **2 H1** (skill mục 11.2).
- **Đã làm:** wrapper logo dùng biến `header_heading_tag` = `h1` khi `request.page_type == 'index'`, ngược lại `div`
  (giữ class, không đổi `display` → hợp Rule 5). Tiện thể sửa fallback alt logo qua biến `logo_alt`.

### 2. JSON-LD Product render trùng 2 lần — ✅ DONE
- **File:** `snippets/meta-tags.liquid` + `sections/main-product.liquid`
- **Vấn đề:** `{{ product | structured_data }}` xuất hiện 2 lần → duplicate structured data (cảnh báo GSC).
- **Đã làm:** xoá block ld+json trong `main-product.liquid` (thay bằng comment cảnh báo); JSON-LD chỉ còn
  1 nơi trong `<head>` của `meta-tags.liquid`.

---

## 🟠 Content & Semantic (cũng đụng Rule 4 — Business tone)

### 3. Subtitle sản phẩm hardcode giống hệt trên mọi PDP — ✅ DONE
- **File:** `sections/main-product.liquid`
- **Đã làm:** thay text cứng bằng `product.description | strip_html | strip`, ẩn nếu blank; CSS clamp 2 dòng +
  ellipsis. Mô tả đầy đủ vẫn nằm ở accordion `product-comparison` nên không trùng nội dung.

### 4. Danh sách "features" hardcode giống nhau mọi sản phẩm — ⏳ PENDING (chờ metafield)
- **File:** `sections/main-product.liquid` (khối `.main-product__features`, ~dòng 678–728)
- **Vấn đề:** "Solid walnut / Hand-finished / Made to order in 3–5 weeks" cố định trên mọi PDP.
- **Giải pháp:** chuyển sang metafield theo từng sản phẩm. Cần tạo metafield definition trong Shopify Admin
  (Settings → Custom data → Products) + nhập dữ liệu — không làm được thuần local.

### 5. H2 "Why You Choose This Masterpiece" hardcode + heading thừa — ✅ DONE
- **File:** `sections/main-product.liquid`
- **Đã làm:** xoá `<header class="main-product__trust-header">` (khối `display:none` chứa H2 ẩn trùng) → còn **1 H2**;
  H2 hiển thị lấy text từ setting mới `trust_subheading`, giữ `id` + `aria-labelledby`. Gỡ 2 setting cũ
  (`trust_eyebrow`, `trust_heading`) + dọn CSS mồ côi ở cả 3 breakpoint.
- **Lưu ý:** Theme Editor: 2 ô "Eyebrow"/"Heading" cũ được thay bằng "Subheading".

### 6. `article.liquid` & `blog.liquid` sơ sài cho SEO/EEAT — ⬜ Chưa làm
- **File:** `sections/article.liquid`, `sections/blog.liquid`
- **Vấn đề:** đều là section mặc định. Không có wrapper `<article>`; ảnh (`article.image`) render
  `image_tag` không `alt`/`width`/`height`/`loading` (`article.liquid:10`, `blog.liquid:14`);
  không breadcrumb; không `article:published_time`/author meta.
- **Giải pháp:** bọc `<article>`, thêm `alt` + dimensions + `loading` cho ảnh, breadcrumb, hiển thị
  author/date (skill mục 23). *(Ưu tiên tùy mức độ dùng blog.)*

---

## 🟡 Image / Metadata

### 7. Nhiều ảnh nội dung thiếu `alt` (một số thiếu cả dimensions) — ⬜ Chưa làm
- **Vấn đề:** `image_tag` không truyền `alt` → thuộc tính `alt` bị thiếu trên ảnh **có ý nghĩa** (skill mục 12.4).
- **Các chỗ thiếu `alt` (ảnh meaningful):**
  - `sections/hero-banner.liquid:55` — ảnh hero (LCP), **ưu tiên cao**
  - `sections/shop-collections.liquid:60` và `:70` — ảnh collection
  - `sections/signature-pieces.liquid:51` — ảnh sản phẩm
  - `sections/materials-craftsmanship.liquid:189` — ảnh visual
  - `sections/curated-collections.liquid:27` — ảnh collection (nhánh fallback `<img>` thì đã có alt)
  - `sections/client-reviews.liquid:43` — ảnh review
  - `sections/styling-consultation.liquid:499` — ảnh advisor (fallback `<img>` có alt)
  - `sections/article.liquid:10`, `sections/blog.liquid:14` — xem #6
- **Cần review (đang `alt=''`):** `sections/product-comparison.liquid:624` — nếu ảnh mang nội dung thì nên có alt;
  nếu trang trí thì giữ `alt=''`.
- **Decorative `alt=''` hợp lệ (không cần sửa):** `header.liquid:359` (mega feature), `hero-banner.liquid:76` (avatars).
- **Giải pháp:** gán `alt` qua biến (ví dụ `assign x_alt = image.alt | default: <tiêu đề phù hợp>`) rồi truyền `alt: x_alt`.

### 8. Bug fallback `alt` ở ảnh (filter `| default:` sai chỗ) — ⚠️ MỘT PHẦN
- **Vấn đề:** `alt: image.alt | default: <title>` — `| default:` áp lên **output của `image_tag`** (chuỗi `<img>`
  không bao giờ blank), nên khi `image.alt` rỗng thì `alt` thành rỗng chứ không fallback.
- **Đã sửa:** `sections/collection.liquid` (product card, biến `card_alt`) và `sections/header.liquid` (logo, `logo_alt`).
- **Còn lại (chưa sửa):**
  - `sections/collection.liquid:383` — ảnh "other collections" ở empty state
  - `sections/collections.liquid:117-118` — `alt: room_collection.featured_image.alt | default: room_label`
  - `sections/search.liquid:249-250` — `alt: result.featured_image.alt | default: result.title`
- **Giải pháp:** tính fallback vào biến trước rồi truyền `alt: <biến>` (như đã làm ở collection card).

### 9. `og:image` chính dùng `http:` — ✅ DONE
- **File:** `snippets/meta-tags.liquid`
- **Đã làm:** đổi `content="http:{{ page_image | image_url }}"` → `https:`.

### 10. Trang tìm kiếm nội bộ chưa `noindex` — ⬜ Chưa làm (mới)
- **File:** `snippets/meta-tags.liquid` (thêm meta robots có điều kiện) / `sections/search.liquid`
- **Vấn đề:** skill mục 8.4 & 22.3 khuyến nghị trang search nội bộ nên `noindex, follow`. Hiện theme không set
  robots cho trang search → các URL `?q=...` có thể bị index (thin/duplicate).
- **Giải pháp:** trong `meta-tags.liquid`, thêm `<meta name="robots" content="noindex, follow">` khi
  `request.page_type == 'search'` (cân nhắc thêm các trang tiện ích khác nếu cần).

### 11. `page.liquid` generic thiếu semantic wrapper + breadcrumb — ⬜ Chưa làm (mới, nhẹ)
- **File:** `sections/page.liquid`
- **Vấn đề:** chỉ có `<h1>` + `{{ page.content }}`, không `<main>`/`<article>`, không breadcrumb.
- **Ghi chú:** các trang chính (About/Contact/FAQ/Care Guide) đã dùng section riêng (`main-*`) có H1 riêng,
  nên đây chỉ ảnh hưởng các page dùng template `page` mặc định. Ưu tiên thấp.

---

## 🟢 Crawl files & ghi chú

- **`robots.txt` / `sitemap.xml`:** không có file tùy biến — **đúng và ổn**, Shopify tự sinh + tự thêm canonical.
  Chỉ tạo `templates/robots.txt.liquid` nếu sau này muốn chặn crawl trang filter mỏng.
- **`/cart`:** `theme.liquid` redirect `/cart` → `/collections/all` bằng JS (chấp nhận được; không phải nội dung index).
- **`product-recommendations`:** dùng object `recommendations` (server-side khi load qua Recommendations API)
  — không phải nội dung SEO-critical, chấp nhận được.
- **Dead code:** `sections/product.liquid` (section mặc định cũ, không nằm trong `product.json`) — nên xoá.

---

## Tiến độ

| # | Mức độ | Trạng thái |
|---|--------|-----------|
| 1 | 🔴 Critical | ✅ DONE |
| 2 | 🔴 Critical | ✅ DONE |
| 3 | 🟠 Content | ✅ DONE (fallback `product.description`) |
| 4 | 🟠 Content | ⏳ PENDING — chờ tạo metafield trong Shopify Admin |
| 5 | 🟠 Content | ✅ DONE |
| 6 | 🟠 Semantic | ⬜ Chưa làm (article + blog) |
| 7 | 🟡 Image | ⬜ Chưa làm (nhiều ảnh thiếu `alt`) |
| 8 | 🟡 Image | ⚠️ MỘT PHẦN — còn `collection.liquid:383`, `collections.liquid:117`, `search.liquid:250` |
| 9 | 🟡 Metadata | ✅ DONE |
| 10 | 🟡 Crawl | ⬜ Chưa làm (search chưa `noindex`) |
| 11 | 🟢 Semantic | ⬜ Chưa làm (nhẹ — `page.liquid`) |

**Lưu ý triển khai (theo `CODING_RULES.md`):**
- Sửa `header.liquid` **không** đổi `display` của wrapper (Rule 5).
- Style mới dùng biến trong `assets/base.css` (Rule 3).
- Nội dung UI giữ tiếng Anh (Rule 7).
- Nếu thêm icon → qua iconify MCP (Rule 9).
