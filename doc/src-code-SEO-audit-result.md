# SEO Audit Result — WRYDECO Theme Source Code

> **Ngày audit:** 2026-07-27
> **Skill áp dụng:** `.agents/skills/optimize-seo-ssr-coding/SKILL.md` (SSR-First SEO)
> **Phạm vi:** toàn bộ `layout/`, `sections/` (54 file), `snippets/` (36 file), `templates/`
> **Kết luận ngắn:** Nền tảng SSR và canonical **rất tốt**. Vấn đề tập trung ở **indexing control** (không có `noindex` ở đâu cả), **structured data còn thiếu**, và **4 lỗi cụ thể** có thể sửa nhanh.
>
> **Cập nhật 2026-07-27:** ✅ **Toàn bộ 4 lỗi P0 đã được sửa và verify** (xem §7). Các mục P1/P2 vẫn còn nguyên.

---

## 1. Phương pháp & bằng chứng

Audit này không dựa trên đọc code suông. Mỗi kết luận đều có bằng chứng từ:

| Nguồn | Cách làm |
| --- | --- |
| Static analysis | Quét regex toàn bộ `.liquid` cho `<img>`, `image_tag`, `<h1>`, `ld+json`, `target="_blank"`, `itemprop` |
| Runtime probe | Fetch HTML thô của **15 route** từ theme dev server (`127.0.0.1:9292`), parse `<head>` |
| Crawl files | Fetch `/robots.txt`, `/sitemap.xml` qua dev server |
| Asset probe | Fetch trực tiếp asset URL để kiểm tra Liquid có được render không |

### Caveat quan trọng khi đọc báo cáo

1. **Dev server rewrite CDN URL.** `shopify theme dev` đổi `https://cdn.shopify.com/s/files/...` thành `/cdn/shop/files/...` để proxy qua localhost. Vì vậy `og:image` xuất hiện dạng tương đối khi probe — **đây không phải lỗi**, trên production template xuất ra URL tuyệt đối. Cần verify lại khi store mở public.
2. **Store đang bật password.** `https://wrydeco.myshopify.com/` trả về password page (11.5 KB), nên không đối chiếu được production. Các mục đánh dấu 🔍 cần kiểm tra lại sau khi store public.

---

## 2. Scorecard

| Hạng mục | Đánh giá | Ghi chú |
| --- | --- | --- |
| SSR-first / crawlability | 🟢 Rất tốt | Không có trang nào phụ thuộc hydration |
| Canonical strategy | 🟢 Rất tốt | Xử lý đúng cả pagination, sort, filter, UTM |
| Heading & semantic HTML | 🟢 Tốt | 1 `h1` mỗi trang, landmark đầy đủ |
| Image SEO | 🟢 Tốt | LCP priority + alt fallback làm chuẩn |
| Internal linking | 🟢 Tốt | Anchor thật, SSR, không JS-only |
| Trust / EEAT | 🟢 Tốt | Đủ about/contact/policies |
| **Index control (noindex)** | 🔴 **Thiếu hoàn toàn** | Không có `<meta name="robots">` ở bất kỳ đâu |
| **Structured data** | 🟠 Thiếu nhiều | Có Product + FAQ; thiếu Article/Breadcrumb/Organization |
| Metadata chi tiết | 🟠 Có lỗi | Brand bị lặp trong `<title>` |
| Crawl files | 🟠 Cần kiểm tra | Không thấy directive `Sitemap:` |

---

## 3. Những phần ĐÃ LÀM TỐT

### 3.1 SSR-first — đạt yêu cầu cốt lõi của skill

Toàn bộ nội dung SEO-critical nằm trong HTML server-render. Probe HTML thô (không chạy JS) xác nhận:

- **PDP** (`/products/natural-wood-corner-tree-branch-bookshelf-custom-design`): có `h1` tên sản phẩm, giá, mô tả, gallery ảnh, JSON-LD `Product` / `ProductGroup` / `Offer` / `Brand` — tất cả trong response đầu tiên.
- **Collection**: grid sản phẩm, tên, giá, link — SSR qua `{% paginate %}`, không fetch client.
- **Article**: `articleBody` render server-side.
- **Search**: kết quả render bằng `{% paginate search.results %}`, không phải JS-only.

Không có trang nào rơi vào "CSR red flags" ở §5.3 của skill. Client-side JS chỉ dùng cho: hover gallery, dropdown filter, add-to-cart AJAX, wishlist, lightbox, toast — đúng phạm vi "enhancement" §5.2.

### 3.2 Canonical — điểm mạnh nhất của theme

`snippets/meta-tags.liquid:100-103` dùng `canonical_url` của Shopify. Kết quả probe thực tế:

| URL request | Canonical trả về | Đánh giá |
| --- | --- | --- |
| `/collections/all` | `.../collections/all` | ✅ self |
| `/collections/all?page=2` | `.../collections/all?page=2` | ✅ **self-canonical, không gộp về page 1** (§9.3) |
| `/collections/all?page=1` | `.../collections/all` | ✅ tránh duplicate |
| `/collections/all?sort_by=price-ascending` | `.../collections/all` | ✅ (§9.4) |
| `/collections/all?filter.v.price.gte=2900` | `.../collections/all` | ✅ |
| `/collections/all?utm_source=facebook&utm_medium=cpc` | `.../collections/all` | ✅ (§18) |
| `/collections/all?from=%2Fcart` | `.../collections/all` | ✅ |
| `/products/...?variant=` | `.../products/...` | ✅ |

Tất cả canonical đều **tuyệt đối + HTTPS**, và `og:url` **luôn khớp canonical** — đúng yêu cầu §10.

### 3.3 Heading & semantic HTML

- **Đúng 1 `<h1>` trên mọi trang** — verify bằng cả grep source (21 vị trí `<h1`, mỗi template một cái) lẫn đếm trên HTML thật của 15 route. Không trang nào có 0 hoặc 2 `h1`.
- `sections/article.liquid:13` chủ động hạ cấp `<h1>` do merchant nhập trong rich text xuống `<h2>` — chi tiết rất tốt, ngăn double-h1 từ phía nội dung.
- Phân cấp trên PDP: `h1` (tên SP) → `h2` (trust section) → `h3` (từng trust item). Không nhảy cấp.
- Landmark: `<main id="MainContent">` bọc `content_for_layout`, `<article itemscope>` cho bài viết, `<aside>` cho trust block, `<nav aria-label="Breadcrumb">` cho breadcrumb.
- `<html lang="{{ request.locale.iso_code }}">` ✅

### 3.4 Image SEO — làm rất kỹ ở 2 surface quan trọng nhất

**PDP gallery** (`snippets/product-media-gallery.liquid:480-515`) là ví dụ mẫu:

```liquid
assign media_alt = media.alt | default: product.title
assign gallery_preload_count = 5
if is_active_media
  assign main_loading = 'eager'      # LCP image
  assign main_fetchpriority = 'high'
elsif forloop.index <= gallery_preload_count
  assign main_loading = 'eager'
  assign main_fetchpriority = 'low'  # preload nhưng không tranh băng thông với LCP
endif
```

- Ảnh LCP **không** bị lazy-load (§12.5) ✅
- Thumbnail `loading: 'lazy'` ✅
- `widths` + `sizes` responsive đầy đủ ✅
- **0/38** lời gọi `image_tag` thiếu `alt` ✅

**Collection card** (`sections/collection.liquid`) có fallback alt về `product.title`, kèm comment giải thích đúng cái bẫy `| default:` sau `image_tag` (chain vào chuỗi `<img>` nên không bao giờ blank).

**Collection banner** dùng `loading: 'eager'` + `fetchpriority: 'high'` cho ảnh hero ✅

### 3.5 Internal linking & trust (EEAT)

- Header: **23 internal anchor** thật (8 collection, customization, search, cart…). Footer: **18 internal anchor**. Tất cả là `<a href>` SSR, không có nav dựng bằng JS (§11.3).
- Trust pages đầy đủ (§16): `/pages/about-us`, `/pages/contact`, `/pages/faq`, `/pages/care-guide`, `/policies/privacy-policy`, `/policies/refund-policy`, `/policies/shipping-policy`, `/policies/terms-of-service`.
- **6/6** link `target="_blank"` đều có `rel="noopener"` ✅ (§17)

### 3.6 Các điểm đúng khác

- `/this-page-404-test` trả **HTTP 404** thật, không phải 200 rỗng (§24) ✅
- Title tự thêm số trang: `Explore All Pieces – Page 2 – Wrydeco` (§8.1) ✅
- Structured data FAQ trên 5 trang, và nội dung FAQ **có hiển thị thật** trên trang (không phải schema ảo) ✅
- Localization là **country/currency-only** (`localization.available_countries`, không đổi ngôn ngữ) → **không cần hreflang**, việc theme không xuất hreflang là đúng ✅
- `sitemap.xml` do Shopify tự sinh, có đủ index con: products, pages, collections, blogs, metaobject_pages ✅
- `critical.css` được preload ✅

---

## 4. Những phần CHƯA TỐT

### 🔴 P0 — Critical

#### A1. Không có `<meta name="robots">` ở bất kỳ đâu → trang search bị index vô tội vạ

**Bằng chứng:** grep toàn repo cho `name="robots"` / `noindex` → **0 kết quả**. Probe 15 route → `robots: MISSING` trên tất cả.

Nghiêm trọng vì kết hợp 2 yếu tố:

1. `/search?q=shelf` trả **HTTP 200** với canonical **self** (`.../search?q=shelf`)
2. `robots.txt` của store **không hề chặn `/search`** (đã verify: chuỗi "search" không xuất hiện trong robots.txt)

→ Mỗi truy vấn tìm kiếm tạo một URL riêng, tự canonical, crawlable, indexable. Đây chính xác là thứ §22.3 yêu cầu tránh: *"Internal search result pages are usually noindex, follow"*. Hậu quả: thin content, loãng crawl budget, có thể bị đánh giá là low-quality pages.

**Fix đề xuất** — thêm vào `snippets/meta-tags.liquid`:

```liquid
{%- liquid
  assign robots_directive = 'index, follow'
  case request.page_type
    when 'search', 'cart', 'customers/account', 'customers/login', 'customers/register', 'customers/order', 'customers/addresses', 'customers/reset_password', 'customers/activate_account', 'gift_card'
      assign robots_directive = 'noindex, follow'
  endcase
-%}
<meta name="robots" content="{{ robots_directive }}">
```

#### A2. `/cart` đang crawlable và indexable

**Bằng chứng:** robots.txt chỉ có `Disallow: /cart/` (có dấu `/` cuối) và `Disallow: /cart.js`. Theo cách match của Google, `Disallow: /cart/` **không** chặn URL `/cart`. Probe `/cart` → HTTP 200, canonical `.../cart`, không có `noindex`.

Trang này còn dùng client-side redirect (xem F1) nên crawler thấy một trang "Cart" rỗng, có title, có canonical → đủ điều kiện index.

**Fix:** nằm trong cùng patch A1 (`when 'cart'`).

#### B1. Tên brand bị lặp trong `<title>` của mọi trang

**Bằng chứng thực tế từ HTML:**

```
Homepage : Handcrafted Solid Wood Furniture & Decor | WRYDECO – Wrydeco
Article  : Brooklyn Brownstone Interior with Sculptural Wood | WRYDECO – Wrydeco
```

**Nguyên nhân** — `snippets/meta-tags.liquid:97`:

```liquid
{%- unless page_title contains shop.name %} &ndash; {{ shop.name }}{% endunless -%}
```

Liquid `contains` **phân biệt hoa thường**. SEO title merchant nhập dùng `WRYDECO` (in hoa), còn `shop.name` là `Wrydeco` → điều kiện không khớp → vẫn nối thêm brand lần hai.

Đây là lỗi hiển thị trực tiếp trên SERP, làm phí ~10 ký tự title và trông thiếu chuyên nghiệp.

**Fix:**

```liquid
{%- liquid
  assign page_title_down = page_title | downcase
  assign shop_name_down = shop.name | downcase
-%}
{%- unless page_title_down contains shop_name_down %} &ndash; {{ shop.name }}{% endunless -%}
```

#### F2. PWA manifest xuất bản dạng Liquid chưa render → JSON hỏng

**Bằng chứng** — `snippets/meta-tags.liquid:9` trỏ tới asset **kèm đuôi `.liquid`**:

```liquid
<link rel="manifest" href="{{ 'manifest.json.liquid' | asset_url }}">
```

Fetch thử cả hai biến thể:

| Asset URL | Kết quả |
| --- | --- |
| `.../assets/manifest.json.liquid` | HTTP 200 — body là `{ "name": "{{ shop.name }}", ... }` ❌ **Liquid chưa render, JSON không hợp lệ** |
| `.../assets/manifest.json` | HTTP 200 — body đã render đúng ✅ |

Shopify chỉ render asset `.liquid` khi được request **không kèm** đuôi `.liquid`. Theme đang link thẳng vào bản thô.

**Fix:** `<link rel="manifest" href="{{ 'manifest.json' | asset_url }}">`

---

### 🟠 P1 — Nên sửa sớm

#### C1. Article schema không đủ điều kiện rich result

`sections/article.liquid` dùng **microdata** với các `itemprop`: `headline`, `description`, `author` (text thuần), `articleBody`.

Thiếu: `datePublished`, `dateModified`, `image`, `publisher`, và `author` chưa phải object `Person`/`Organization`. Google yêu cầu tối thiểu `headline` + `image` + `datePublished` cho Article rich result → hiện **không đủ điều kiện**.

Ngoài ra Google khuyến nghị JSON-LD hơn microdata. Đề xuất bổ sung block JSON-LD `BlogPosting` vào `sections/article.liquid`.

#### C2. Không có `BreadcrumbList` structured data

Breadcrumb **hiển thị** ở `sections/collection-banner.liquid`, `sections/article.liquid`, `sections/main-faq-page.liquid` — nhưng không có schema đi kèm. §11.4 khuyến nghị thêm. Đây là cách rẻ nhất để lấy breadcrumb hiển thị trong SERP thay vì URL trần.

#### C3. Không có `Organization` / `WebSite` JSON-LD

Không có ở bất kỳ đâu (đã grep). Ảnh hưởng: khó lấy knowledge panel, mất cơ hội sitelinks searchbox, thiếu tín hiệu brand (logo, sameAs mạng xã hội, contactPoint) — đặc biệt đáng tiếc với thương hiệu định vị luxury.

Nên đặt trong `layout/theme.liquid` hoặc `snippets/meta-tags.liquid`, chỉ render ở trang chủ.

#### D1. PDP không có breadcrumb (cả UI lẫn schema)

Grep xác nhận chỉ 3 file có breadcrumb, **không có `main-product.liquid`**. §11.4 xếp product page là ứng viên hàng đầu. Với store có phân cấp Home → Collection → Product rõ ràng, thiếu breadcrumb làm mất:

- tín hiệu phân cấp cho crawler
- internal link ngược về collection cha (giá trị link equity thật)
- đường lùi cho người dùng

#### E1. `robots.txt` không có directive `Sitemap:` 🔍

Đã verify: chuỗi `sitemap` **không xuất hiện** trong `/robots.txt` (chỉ có 2 block `User-agent`: `*` và `adsbot-google`). §13 yêu cầu bắt buộc phải có.

Theme **không có** `templates/robots.txt.liquid` để override, nên robots.txt hoàn toàn do Shopify sinh. Cần kiểm tra lại trên production (store đang bật password có thể ảnh hưởng). Nếu production cũng thiếu, tạo `templates/robots.txt.liquid`:

```liquid
{% for group in robots.default_groups %}
  {{- group.user_agent }}
  {% for rule in group.rules %}{{ rule }}
  {% endfor %}
  {%- if group.sitemap != blank %}{{ group.sitemap }}{% endif %}
{% endfor %}
Sitemap: {{ shop.url }}/sitemap.xml
```

#### B2. Thiếu meta description trên một số trang thật

Probe cho thấy `<meta name="description">` **không tồn tại** trên:

- `/pages/about-us`
- `/blogs/news`
- `/cart` (sẽ thành noindex sau khi fix A1 nên không quan trọng)

Đây là khoảng trống dữ liệu bên admin (SEO description chưa nhập), không phải lỗi code — `meta-tags.liquid:105` chỉ render khi `page_description` có giá trị. Cần nhập trong Shopify Admin. Nếu muốn an toàn có thể thêm fallback thông minh (excerpt của page/blog), nhưng **không nên** fallback về `shop.description` cho nhiều trang vì sẽ tạo description trùng lặp — §8.2 cấm điều này.

#### B3. Trang phân trang dùng lại description của trang 1

Title đã có "– Page 2" nhưng description thì giống hệt trang 1. §8.2 yêu cầu description phân biệt theo số trang. Fix nhỏ trong `meta-tags.liquid`: nối ` (Page {{ current_page }})` khi `current_page != 1`.

---

### 🟡 P2 — Cải thiện thêm

| # | Vấn đề | Chi tiết |
| --- | --- | --- |
| B4 | `og:image` không resize | `meta-tags.liquid:49` dùng `image_url` không tham số → xuất ảnh gốc (PDP: 1254×1254 vuông). §10 khuyến nghị 1200×630. Nên `image_url: width: 1200`. |
| B5 | Thiếu `twitter:image` | Đang khai `twitter:card=summary_large_image` nhưng không có `twitter:image`. X sẽ fallback về `og:image` nên tác động thấp, vẫn nên khai tường minh. |
| B6 | Thiếu `og:image:alt` | Ảnh hưởng accessibility của social preview. |
| B7 | `og:price:currency` dùng `cart.currency.iso_code` | Store đa market; nên dùng `localization.country.currency.iso_code` cho nhất quán với phần còn lại của theme. |
| E2 | Chưa xác nhận image sitemap 🔍 | §12.6: e-commerce nhiều ảnh gallery nên có. Sitemap product của Shopify thường đã kèm `<image:image>` — cần verify trên production. |
| F1 | `/cart` redirect bằng client-side JS | `layout/theme.liquid:20-24` dùng `window.location.replace` trong `<head>`, chặn parse, và là redirect phía client (§5 ưu tiên server-side). Nên chuyển sang **URL redirect trong Shopify Admin** (301 thật) — vừa sạch SEO vừa nhanh hơn. |
| F3 | `assets/site.webmanifest` là file rác | Còn nội dung boilerplate `"name": "MyWebSite"`. Không được link tới nhưng nên xóa để tránh nhầm lẫn. |
| D2 | Không có skip-to-content link | Chủ yếu là accessibility, ảnh hưởng SEO gián tiếp. |
| D3 | `<main role="main">` | `role` thừa với thẻ `<main>` — nit, vô hại. |

---

## 5. Bảng ưu tiên hành động

| Ưu tiên | Mục | File cần sửa | Công sức |
| --- | --- | --- | --- |
| **P0** | A1 + A2 — thêm `<meta name="robots">` | `snippets/meta-tags.liquid` | ~10 dòng |
| **P0** | B1 — sửa lặp brand trong title | `snippets/meta-tags.liquid` | 3 dòng |
| **P0** | F2 — sửa link manifest | `snippets/meta-tags.liquid` | 1 dòng |
| P1 | C3 — Organization + WebSite JSON-LD | `snippets/meta-tags.liquid` | block mới |
| P1 | C2 — BreadcrumbList JSON-LD | snippet dùng chung + 3 section | vừa |
| P1 | D1 — breadcrumb cho PDP | `sections/main-product.liquid` | vừa |
| P1 | C1 — BlogPosting JSON-LD | `sections/article.liquid` | block mới |
| P1 | E1 — `templates/robots.txt.liquid` | file mới | nhỏ 🔍 |
| P1 | B2 — nhập SEO description | Shopify Admin (không phải code) | thủ công |
| P2 | B3–B7, F1, F3, D2 | rải rác | nhỏ |

---

## 6. Việc cần kiểm tra thủ công (không verify được từ code)

1. 🔍 **Fetch lại `/robots.txt` và `/sitemap.xml` trên production** sau khi gỡ password — xác nhận có `Sitemap:` directive và image entries.
2. 🔍 **Kiểm tra `og:image` trên production** là URL tuyệt đối (`https://cdn.shopify.com/...`) — bản probe hiện tại bị dev server rewrite nên không kết luận được.
3. Chạy **Google Rich Results Test** cho 1 PDP, 1 article, 1 FAQ page sau khi bổ sung structured data.
4. Submit sitemap trong **Google Search Console**, theo dõi Coverage report — đặc biệt xem có URL `/search?q=` nào bị index trước khi fix A1 không (nếu có, cần chờ Google recrawl để rớt ra).
5. Đo **Core Web Vitals** thực tế (LCP trên PDP và collection) — code đã tối ưu priority đúng hướng nhưng cần field data.

---

## 7. Trạng thái khắc phục P0 (2026-07-27)

Cả 4 lỗi P0 đã sửa xong. Toàn bộ thay đổi nằm trong `snippets/meta-tags.liquid` và `assets/manifest.json.liquid` — không đụng tới section/template nào khác.

### A1 + A2 — Thêm `<meta name="robots">`

Thêm block quyết định directive ngay sau thẻ canonical trong `snippets/meta-tags.liquid`. Mặc định `index, follow`; chuyển sang `noindex, follow` cho:

- `request.page_type`: `search`, `cart`, `gift_card`, `password`, `captcha`
- toàn bộ `customers/*` (account, login, register, order, addresses, reset_password, activate_account)
- mọi đường dẫn chứa `/apps/` — app proxy page (`/apps/track-order`, `/apps/page/wishlist`) render qua layout này với HTTP 200 và là nội dung mỏng/cá nhân hóa

Dùng `noindex, follow` (không phải `nofollow`) để link trên các trang đó vẫn truyền tín hiệu crawl.

**Verify:**

| Route | robots |
| --- | --- |
| `/`, `/collections/all`, `/products/…`, `/pages/about-us`, `/blogs/news`, `/collections` | `index, follow` |
| `/search?q=shelf` | `noindex, follow` |
| `/cart` | `noindex, follow` |
| `/apps/track-order`, `/apps/page/wishlist` | `noindex, follow` |

Mỗi trang đúng **1** thẻ robots (đã đếm, không double tag).

### B1 — Sửa lặp brand trong `<title>`

So sánh brand bằng bản `downcase` của cả hai vế trước khi quyết định có nối `shop.name` hay không.

**Verify:**

| Trang | Trước | Sau |
| --- | --- | --- |
| Homepage | `… Decor \| WRYDECO – Wrydeco` | `… Decor \| WRYDECO` ✅ |
| Article | `… Wood \| WRYDECO – Wrydeco` | `… Wood \| WRYDECO` ✅ |
| Collection | `Explore All Pieces – Wrydeco` | `Explore All Pieces – Wrydeco` (giữ nguyên, đúng — title không chứa brand) |
| Collection page 2 | — | `Explore All Pieces – Page 2 – Wrydeco` (logic phân trang không bị ảnh hưởng) |

### F2 — Sửa link PWA manifest

Hai thay đổi:

1. `snippets/meta-tags.liquid` trỏ tới `{{ 'manifest.json' | asset_url }}` (bỏ đuôi `.liquid`) → Shopify render Liquid thay vì trả file thô.
2. `assets/manifest.json.liquid` thay `{{ shop.name }}` bằng chuỗi `"WRYDECO"`. Lý do: asset `.liquid` được render **ngoài** ngữ cảnh storefront nên object `shop` không khả dụng — giữ nguyên sẽ ra `"name": ""`. Filter `asset_url` cho icon vẫn hoạt động bình thường nên phần icon giữ nguyên.

**Verify:** manifest trả về JSON hợp lệ, `name = "WRYDECO"`, 2 icon resolve đúng về `/cdn/shop/t/2/assets/…`.

> **Ghi chú lint:** theme-check báo `MissingAsset` cho `'manifest.json'` vì nó đọc tên file trên đĩa theo nghĩa đen (`manifest.json.liquid`). Đây là false positive — đã verify bằng HTTP là reference đúng. Rule được tắt đúng 1 dòng bằng `{% # theme-check-disable MissingAsset %}`.

### Kiểm tra hồi quy

Probe lại 11 route sau khi sửa, tất cả invariant đều giữ nguyên:

- đúng 1 thẻ canonical / trang
- đúng 1 thẻ robots / trang
- đúng 1 `<h1>` / trang
- `og:url` **luôn khớp** canonical
- canonical vẫn xử lý đúng `?page=2` (self), `sort_by` và `utm_*` (về URL sạch)

`shopify theme check`: **70 errors / 67 warnings** — bằng đúng baseline trước khi sửa, `meta-tags.liquid` sạch hoàn toàn.

---

## 8. Lưu ý cuối

Audit này đánh giá **code**, không đánh giá thứ hạng. Việc index và ranking cuối cùng do search engine quyết định — sửa hết các mục trên là điều kiện cần để crawler hiểu đúng site, không phải điều kiện đủ để lên top.

Điểm cần nhấn mạnh: **nền móng của theme này chắc**. Canonical, SSR, heading, image priority, internal link đều đã đúng — đây là phần khó và tốn công nhất, và đã làm xong. Những gì còn thiếu chủ yếu là **lớp khai báo bổ sung** (robots meta, structured data) — sửa nhanh, rủi ro thấp, lợi ích rõ ràng.
