# Báo Cáo Triển Khai (Deploy Report)

**Dự án:** Shopify Admin App (vnote.io.vn)
**Ngày hoàn thành:** 31/07/2026
**Trạng thái:** THÀNH CÔNG ✅
**Đường dẫn truy cập:** [https://shopify.vnote.io.vn](https://shopify.vnote.io.vn)

---

## 1. Tóm tắt Quá trình Triển khai ban đầu
- **Tạo môi trường cách ly:** Triển khai mã nguồn vào thư mục riêng biệt `/home/vmadmin/shopify-admin-app` trên VPS (`160.25.81.57`) để không xung đột với các dịch vụ khác.
- **Cài đặt thư viện:** Thiết lập môi trường ảo (`venv`) và cài đặt các dependencies (FastAPI, Uvicorn, Jinja2, requests,...).
- **Cấu hình Process Manager:** Tạo và kích hoạt systemd service có tên `shopify-admin-app.service` chạy ngầm ở port `8085`.
- **Cấu hình Nginx:** Viết cấu hình Reverse Proxy cho tên miền `shopify.vnote.io.vn` trỏ vào port `8085`.

---

## 2. Các sự cố phát sinh và Biện pháp khắc phục

Trong quá trình "Go Live", hệ thống đã gặp một số sự cố. Dưới đây là chi tiết nguyên nhân và cách Agent đã xử lý:

### Sự cố 1: Lỗi hiển thị trang Nginx mặc định & Không thể lấy chứng chỉ SSL (Lỗi 404)
- **Nguyên nhân:** Có sự bất đồng bộ giữa biến môi trường. File `.vps.env` cũ lưu IP `103.147.123.63` khiến user trỏ nhầm DNS, trong khi thực tế server kết nối và deploy thành công lại mang IP `160.25.81.57`. Đồng thời Nginx chưa bị xóa trang cấu hình `default`.
- **Cách khắc phục:** 
  - Hướng dẫn user đổi IP trong bản ghi DNS `shopify` về đúng `160.25.81.57`.
  - Kết nối vào server xóa bỏ file `/etc/nginx/sites-enabled/default` và chạy lại Certbot. Kết quả: SSL được cấp phát thành công, trang web tự động ép sang HTTPS.

### Sự cố 2: Lỗi "Internal Server Error" do Shopify Token (Lỗi 401 Unauthorized)
- **Nguyên nhân:** File `.env` chứa biến `SHOPIFY_API_VERSION=2026-07` không hợp lệ (version chưa ra mắt) và `SHOPIFY_ADMIN_TOKEN` cũ đã bị hết hạn/thu hồi.
- **Cách khắc phục:** Nhận thông tin cấu hình mới từ user, điều chỉnh lại API version về bản ổn định `2024-04` và thay token mới (`shpat_76c...`) vào file `.env` trên VPS. Khởi động lại service.

### Sự cố 3: Lỗi "Internal Server Error" do xung đột thư viện FastAPI (TypeError)
- **Nguyên nhân:** Giao diện bị sập với lỗi `TypeError: unhashable type: 'dict'` phát sinh ở hàm xử lý lỗi của Starlette. Nguyên nhân sâu xa là do cú pháp `templates.TemplateResponse("index.html", {...})` trong `main.py` không còn tương thích với phiên bản FastAPI/Starlette mới nhất cài trên server.
- **Cách khắc phục:** 
  - Viết một kịch bản bằng Regex (Python script) quét toàn bộ mã nguồn `main.py`.
  - Tự động thay thế hàng loạt cú pháp cũ sang chuẩn mới: `templates.TemplateResponse(request=request, name="index.html", context={...})`.
  - Tải lại file `main.py` lên server và restart `shopify-admin-app.service`.

---

## 3. Tổng kết
Tất cả các công việc từ upload code, cấu hình môi trường, cài đặt reverse proxy Nginx, lấy chứng chỉ bảo mật Let's Encrypt (HTTPS), cho đến việc debug mã nguồn và sửa lỗi trực tiếp trên server đều được hoàn thành và ghi chép lại đầy đủ.

Website hiện đã chạy mượt mà và an toàn tại `https://shopify.vnote.io.vn`. Toàn bộ nhật ký các lệnh SSH được lưu lại tại file `logs/vps-ssh.log`.

## 4. 2026-10-13 — Real Homes video playback repair (WRYDECO)

Confirmed on the live storefront with Playwright: a gallery video requested a private Shopify originals URL, which returned HTTP 403 / XML `AccessDenied`. The upload helper had accepted `originalSource` before processing completed and could also fall back to the staged resource URL.

Updated only the Real Homes upload/media functions on the active VPS at `/home/azureuser/shopify-admin-app/main.py`. Uploads now wait for `READY` and a public MP4 rendition, prefer 720p, and never return a private/staged URL as a fallback. Polling runs in a worker thread. Unrelated functions, templates, environment files, and Nginx configuration were preserved. The service restarted successfully; the subsequent readiness check returned HTTP 200 on port 8085.

Remote backup: `/home/azureuser/shopify-admin-app/main.py.video-fix-20261013T043513Z.bak`. Deployment hashes and commands are recorded in `logs/real-homes-video-fix-20261013T043513Z.json`. Original gallery values are retained in the repository's `admin/backups/` directory.

Replaced six private video URLs across four existing project entries, retaining gallery order, images, and posters. A later read-only audit found no remaining private URLs. Eight upload/source-selection regression tests passed. Playwright verified all nine currently listed videos across five projects at 1440×900 and 390×844 (18 playback checks: time advanced, readyState 4, no media errors). The requested Chrome browser also played the original affected project video and the single-video project through to their durations without media errors.

## 5. 2026-11-11 — CSV product images and bulk result accuracy

Fixed the live application at `https://wrydeco.b6-team.site` using the supplied 71-column floor-lamp CSV (SHA-256 `55c683976c43680715db945ffc88f43afa66ee78893de89c67c26a51ca3237da`). Browser-side parsing retained all 25 products and 98 image URLs. The existing server archive also contained the expected image URLs, so the image loss occurred after CSV parsing.

### Verified cause

The deployed service reported success as soon as `productSet` returned a product ID and no immediate `userErrors`. It never checked the resulting media. A temporary draft reproduced this: `productSet` returned success, but three of four images subsequently had `status: FAILED`, `image: null`, and `UNKNOWN / Media processing failed`. The source image URLs returned HTTP 200 with valid PNG/JPEG content. Adding the same four images through `productUpdate(product: ..., media: ...)` produced four READY images with public URLs. Shopify's internal reason for its generic UNKNOWN processing errors was not exposed by the API.

The live bulk verification also exposed two executors: the web request launched a thread while the standalone daemon independently picked up the same job. Restart recovery reset an active item, producing two attempts and inconsistent job counters. This was observed on temporary QA data, not inferred solely from code.

### Changes deployed

- `product_create_service.py`: create product attributes/options/variants with `productSet`, attach images separately with `productUpdate`, and verify the exact expected count, READY status, and image URLs before returning success. Surface processing failures/timeouts and retain the created product ID on partial failure. All calls retain the store's existing proxy-enforced client.
- `main.py`: run synchronous creation/media polling in a worker thread so the event loop remains responsive; preserve product IDs and links in failed single-product archives.
- `bulk_product_worker.py`: preserve partially created product IDs in failed items/events and take a job execution lock before recovery or dispatch.
- `bulk_product_job_store.py`: provide a nonblocking OS file lock shared by web threads and worker processes. A process exit releases the lock; the lock file remains to avoid inode replacement races.

Only these four runtime files were deployed. Existing local work outside this fix was preserved. Backups, SHA-256 hashes, and restart commands are in `logs/media-import-fix-20261111T145210Z.json` and `logs/media-job-lock-fix-20261111T145934Z.json`. The initial immediate startup probe ran before Uvicorn bound its port; subsequent loopback and browser checks returned HTTP 200. Both application and worker services are active, and all four deployed file hashes match local files.

### Verification and cleanup

94 focused tests passed, including image processing failures, missing/unfinished images, public URL readiness, local uploads, proxy behavior, CSV handling, partial-failure archives, and competing thread/process execution.

Using Playwright MCP profile `codevcn`, the supplied CSV was parsed on the live create page. Two temporary DRAFT products derived from its first PNG and JPEG products were submitted through the bulk UI. The final job `job_20261111150010_11fb0b94` completed with 2 successes, 0 failures, and exactly one attempt per item. Shopify returned 4/4 and 3/3 READY images, respectively, with seven variants each. The homepage's Media column showed four and three distinct images, and every image completed loading with a positive natural width. This live run sampled two products; it did not recreate the original 25-product catalog.

All five temporary diagnostic/verification drafts and their associated media were removed; a read-only query verified all 24 unique QA resource IDs were absent. The two QA jobs were removed from SQLite, and the user's previous 25-product archive was restored only after confirming the current archive belonged to the QA run. Evidence: `logs/media-ui-verification-20261111.json`, `logs/media-qa-products-20261111.json`, and `logs/media-qa-cleanup-20261111.json`.

Official API references: [productSet](https://shopify.dev/docs/api/admin-graphql/2026-10/mutations/productSet), [FileSetInput](https://shopify.dev/docs/api/admin-graphql/2026-10/input-objects/FileSetInput), [productUpdate](https://shopify.dev/docs/api/admin-graphql/2026-10/mutations/productUpdate).

## 6. 2026-11-11 — Full-batch source preservation, resumable staged uploads, and recovery

This follow-up supersedes section 5's two-product sample as evidence of import reliability. The user's subsequent real job `job_20261111151149_3723932d` created 25 product records, but only four completed media processing. A failed import item therefore did not mean that no product existed: metadata creation and asynchronous media processing were separate operations, without a transaction rolling back the product. The natural-live-edge product had three FAILED image nodes and no usable image.

The remaining failure was in the tool's media workflow. Passing existing same-store image URLs did not reliably produce READY media across the whole batch. Some original URLs were available in a browser/cache while returning 404 from the server. Removing failed media before durably preserving its source could make recovery impossible from that URL. Shopify returned generic processing errors, which do not establish an internal Shopify root cause; successful uploads of the same actual bytes demonstrate that its API can import this batch.

### Deployed workflow

- Preserve and validate image bytes before creating a product or deleting failed media. A persistent image cache and browser upload fallback keep the import independent of later source URL availability. A missing/unreadable source fails preflight before product creation.
- Upload actual bytes through staged uploads, attach images individually, wait for READY/public URLs, and verify the complete expected count and order. Retry failed images while retaining successful images.
- Persist product ownership and image IDs immediately. An identical import resumes the existing owned product; a lost mutation response is reconciled by reading Shopify state, without blindly repeating product creation. Preserve partial product IDs in errors and job archives.
- Retain the cross-process job lock and existing store/proxy controls. Include `product_media_service.py` in future deployments.

Recovered all 98 original image files from the supplied source gallery ZIP. Each image's SHA-256 matched the checksum embedded in its CSV filename; no replacement imagery or CSV edits were used. The mapping is recorded in `logs/media-98-original-assets-checksummed.json`. Source bytes are preserved in `data/product_media_cache/` on the server. Deployment backups, file hashes, service restart results, and all 98 cache transfers are recorded in `logs/media-staged-deploy-20261111T153735Z.json` and `logs/media-source-cache-deploy-20261111T155300Z.json`.

### Complete live verification

The original 25 products were repaired in place by job `job_20261111155841_eeb6358b`: 25 successes, zero failures, with every original product ID retained. Independent checks verified 98 READY images returning HTTP 200, correct source content/order/dimensions, and all 165 variants including prices, compare-at prices, SKUs, barcodes, and options. Ninety-five image pixel hashes matched exactly; the three JPEGs retained matching dimensions and visual hashes after Shopify recompression. The natural-live-edge product now has all three images. Playwright profile `codevcn` verified all 98 images loaded on the actual homepage.

Then the full 25-product/98-image CSV payload was created as a new set of temporary DRAFT products through the native bulk UI: job `job_20261111160721_50c09c8e` completed with 25 successes and zero failures. The same full batch was submitted again: job `job_20261111161959_e0fc4f20` also completed with 25 successes and zero failures. All 25 product IDs and all 98 media URLs were unchanged on replay, and the matching catalog contained exactly 25 products. The browser source-cache fallback was independently exercised: an uncached image became durably cached after a browser fetch/upload.

The complete local test suite passed: **212 tests**. Regression cases cover failed processing, preserving sources before deletion, staged bytes, transient retries, lost responses, restarts, safe ownership, preflight before product creation, repeated imports without duplication, cache validation, and browser cache uploads.

Evidence: `logs/media-real-25-products-98-images-verified.json`, `logs/media-fresh-create-25-products-98-images-verified.json`, `logs/media-full-replay-verification.json`, `logs/media-real-homepage-final-verification.json`, and `logs/media-browser-source-cache-proof.json`.

### Final cleanup and deployment checks

Removed only the 25 explicitly tagged QA drafts and their 98 media resources after verifying their IDs were disjoint from all real media. Read-back confirmed all 123 QA resources absent and the original 25 products/98 media unchanged. Removed the two terminal QA jobs and their 25 ownership receipts, then atomically restored the real successful 25-product archive after checking that the current archive still belonged to QA. Evidence: `logs/media-full-qa-cleanup-20261111.json`.

All eight deployed runtime file hashes match local source. Both app and bulk-worker services are active, the create page returns HTTP 200, and all 98 real output image URLs also return image content with HTTP 200 from the VPS itself. Evidence: `logs/media-final-deployed-source-hashes.json` and `logs/media-final-vps-health-and-98-images.json`.
