# Runbook Vận Hành Hệ Thống Mở Rộng Blog 20 Bài/Store (`wrydeco-blog-scaling-mcp`)

Tài liệu này hướng dẫn cách cấu hình, khởi chạy, kiểm tra trạng thái, khôi phục (resume) và quy trình chuẩn hóa 5 chặng (Standard 5-Stage Pipeline) cho hệ thống mở rộng Blog Shopify qua **MCP Server (`mcp_server.py`)**, **Web UI (`web_app.py`)** và **CLI (`cli.py`)** trong workspace `d:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-app\auto\module-5-blog`.

---

## 1. Phân tách 3 phạm vi vận hành (Mandatory Scope Separation)

1. **Mục tiêu năng lực hệ thống (Long-term Campaign Goal):**
   - Hỗ trợ mở rộng **20 bài blog mới/store × 5 store = 100 bài mới** (`wrydeco`, `dizzycustom`, `jeminise`, `chillgen`, `preaureum`).
   - Toàn bộ các bài đã xuất bản trước thời điểm bắt đầu chiến dịch được khóa trong `data/campaigns/baseline_2026-10-17/baseline_manifest.json` (`protected_article_ids`, `protected_handles`, `protected_zbigtee_content_ids`) và không bao giờ bị ghi đè hay tính vào bộ đếm bài mới.
2. **Phạm vi triển khai hệ thống (System Implementation Scope):**
   - Local stdio MCP Server (`mcp_server.py`) gồm các công cụ chuẩn hóa.
   - Section **Store Editorial Profile** độc lập theo từng store trên `/settings` (`store_profile_manager.py`, `schemas/store_editorial_profile.schema.json`, `data/store_profiles/<store_id>.json`).
   - Dịch vụ tra cứu bằng chứng Catalog & Media qua Shopify GraphQL Admin API (`shopify_catalog_service.py`).
   - Bộ kiểm toán sự thật & chính sách (`article_fact_auditor.py`).
   - Bộ chữa lành & làm giàu ảnh ngữ cảnh 4–7 ảnh/bài (`article_image_service.py`).
   - Bộ quản lý chiến dịch, khóa idempotency và máy trạng thái (`campaign_manager.py`).
3. **Quy tắc Batch Production tối ưu:**
   - **Kích thước Batch chuẩn:** Khuyến nghị **3 đến 5 bài / lần prompt** (lý tưởng nhất là 3 bài).
   - Tránh nạp > 5 bài trong 1 prompt để ngăn hiện tượng tràn context (>250k tokens), quá tải độ trễ proxy, hoặc timeout từ ZBigTee API.
   - Tự động kích hoạt thông báo đa kênh qua kỹ năng `mod-notifications` (Windows Toast + ntfy/mobile) sau mỗi batch hoàn tất.

---

## 2. Quản lý Credentials & Proxy Server-Side (Zero Secret Leakage)

- **Nguồn cấu hình duy nhất:**
  - `data/stores.json`: chứa thông tin kết nối từng store (`shop`, `client_id`, `client_secret`, `access_token`, `zbigtee_project_id`, `default_blog_handle`).
  - `data/proxy.json`: chứa cấu hình proxy bắt buộc cho mọi giao tiếp tới Shopify.
  - `data/store_profiles/<store_id>.json`: chứa hồ sơ biên tập (Editorial Profile) riêng cho từng store, **tuyệt đối không chứa credentials/tokens**.
- **Cơ chế bảo vệ Proxy bắt buộc (`ProxyManager`):**
  - Mọi kết nối tới Shopify (`*.myshopify.com`, custom storefront domain của 5 store, `cdn.shopify.com`) — bao gồm OAuth token refresh, Admin GraphQL API, Storefront HTTP checks, tải ảnh CDN về `media_cache` và Playwright Live Verification — đều đi qua `ProxyManager`.
  - Nếu Proxy bị tắt, thiếu thông tin hoặc lỗi kết nối, hệ thống lập tức chặn cứng với mã lỗi `PROXY_BLOCKED` (`ProxyBlockedError`), tuyệt đối không fallback sang kết nối trực tiếp (direct connection).
- **Chính sách Redaction:**
  - Toàn bộ phản hồi của MCP tools, logs (`stderr`), báo cáo JSON/Markdown và UI API đều tự động ẩn (`***REDACTED***`) các trường `client_secret`, `access_token`, `password` và chuỗi xác thực proxy (`user:pass@host:port`).

---

## 3. Khởi chạy Công cụ & Đăng ký MCP Server trên Antigravity

### 3.1. Khởi chạy Web UI (`/settings` & Dashboard)

Chạy từ thư mục `d:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-app\auto\module-5-blog`:

```powershell
D:\Python-3-12\python.exe cli.py serve --host 127.0.0.1 --port 8765 --no-browser --raw-server
```

- Cờ `--raw-server` khởi chạy trực tiếp Flask server mà không gọi `server.py` để tránh hành vi tự động kill tiến trình đang giữ cổng.
- Truy cập giao diện quản lý Store & Editorial Profile tại: `http://127.0.0.1:8765/settings`
- Web Tool quản lý riêng của store WRYDECO: `https://wrydeco.b6-team.site/blogs`

### 3.2. Khởi chạy và Đăng ký MCP Server (`mcp_server.py`)

Cấu hình mẫu trong `mcp_config.example.json` (dùng để đăng ký vào cấu hình MCP của Antigravity):

```json
{
  "mcpServers": {
    "wrydeco-blog-scaling": {
      "command": "D:\\Python-3-12\\python.exe",
      "args": [
        "d:\\D-Jobs\\ae-B6\\Shopify\\stores\\main\\wrydeco\\wrydeco-app\\auto\\module-5-blog\\mcp_server.py"
      ],
      "cwd": "d:\\D-Jobs\\ae-B6\\Shopify\\stores\\main\\wrydeco\\wrydeco-app\\auto\\module-5-blog",
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

> **Lưu ý giao thức stdio:** `mcp_server.py` ghi toàn bộ log vận hành ra `sys.stderr` và chỉ dùng `sys.stdout` cho bản tin JSON-RPC của giao thức MCP.

---

## 4. Quy trình Chuẩn hóa 5 Chặng (Standard 5-Stage Pipeline Flow)

Mọi bài viết sản xuất qua MCP server `wrydeco-blog-scaling-mcp` hoặc pipeline đều phải đi qua đúng 5 chặng kiểm soát nghiêm ngặt sau:

```
[Chặng 1: Brief Preparation]
  │  ├── 1. Trích xuất Keyword trước khi Search
  │  ├── 2. Mapping Collection thông minh (wine-rack, tree-bookshelves, floating-shelves...)
  │  ├── 3. Đưa 100% Sản phẩm thật lên đầu Verified Facts (Vị trí 0..4, tuân thủ ZBigTee 30-item limit)
  │  └── 4. Chuẩn hóa path {content_id}_preview.json & đầy đủ metadata handle/url
  ▼
[Chặng 2: Draft Generation]
  │  └── Submit Markdown outline lên ZBigTee API, chuyển trạng thái review và fetch preview
  ▼
[Chặng 3: HTML Postprocessing & Fact Audit]
  │  ├── 1. Thuật toán heal_corrupted_prices: Dùng negative lookbehind (?<=[(\s>]),\d{3}
  │  ├── 2. Giữ nguyên thẻ HTML hợp lệ (<a>, <strong>, <p>) trong FAQ, cấm escape thành &lt;a&gt;
  │  ├── 3. Nhận diện ngữ cảnh phủ định (not, does not, rather than, does ... include ...?)
  │  └── 4. Chuẩn hóa link nội bộ sang domain chính thức https://wrydeco.com
  ▼
[Chặng 4: Image Healing & Media Manifest]
  │  ├── 1. Bổ sung STOPWORDS thương mại (buying, guide, tips, review, fit, capacity...)
  │  ├── 2. Bắt buộc ưu tiên nhặt media pool từ chính verified products trong Brief
  │  └── 3. Phân bổ 4–7 ảnh body + 1 hero image, tính perceptual hash (ahash, dhash, sha256)
  ▼
[Chặng 5: Validation, Publishing & Verification]
  │  ├── 1. Cấp mã băm ready_digest (Pre-Publish Gate)
  │  ├── 2. Xuất bản Shopify ở chế độ create_only, chống ghi đè bài baseline
  │  ├── 3. Live Verification 16 tiêu chí (Desktop/Mobile), fallback myshopify_url khi domain chính 404
  │  ├── 4. Đồng bộ trạng thái published trên ZBigTee
  │  └── 5. Kích hoạt mod-notifications (Toast + ntfy mobile)
```

---

## 5. Chi tiết Các Cải Tiến Kỹ Thuật Đã Chốt

### 5.1. Khâu Chuẩn bị Brief (`prepare_article_brief`)
* **Thứ tự bóc tách từ khóa:** Tuyệt đối không gọi `svc.search_products` với query rỗng. Phải chạy Regex bóc tách keyword từ `raw_topic_title` (vd: `Trang cho “tree bookshelves”` -> `clean_kw = "tree bookshelves"`) trước khi truy vấn catalog.
* **Smart Collection Routing:** Nếu keyword chứa:
  - `wine` + `wall`: map sang collection `wall-mounted-wine-rack`
  - `wine`: map sang collection `wine-racks`
  - `tree` + `shelf`/`bookshelf`: map sang collection `tree-bookshelves` hoặc `wall-mounted-tree-bookshelves`
  - `fluted`: map sang collection `floating-shelves`
* **Vị trí Verified Facts (30-Item Cap Guard):** ZBigTee API giới hạn mảng `verified_facts` tối đa 30 phần tử. Phải xếp **100% sản phẩm catalog thật có đầy đủ handle, giá, kích thước, ảnh lên vị trí 0..4** (đầu mảng). Sau đó mới chèn các điều khoản chính sách cho phép (allowed claims) ở các vị trí tiếp theo. Nghiêm cấm fallback mù sang các sản phẩm đầu store (như gương, tranh) khi bài viết nói về kệ hay đồ nội thất khác.
* **Metadata & Artifact Sync:** Run record phải lưu đầy đủ `handle`, `shopify_url`, `public_url`, và đường dẫn artifact preview chuẩn: `input/{store_id}/{content_id}_preview.json`. Khi retry thành công, `last_error_code` phải được tự động xóa rỗng.

### 5.2. Khâu Chữa Lành Ảnh (`article_image_service.py`)
* **Loại bỏ từ khóa rác (Stopwords):** Mở rộng danh sách `STOPWORDS` với các từ: `buying`, `guide`, `tips`, `ideas`, `review`, `reviews`, `best`, `fit`, `capacity`, `dimensions`. Tránh việc gửi query `rustic wine rack buying` lên Shopify Admin GraphQL làm trả về 0 sản phẩm.
* **Ưu tiên Verified Catalog Pool:** Xây dựng Media Candidate Pool theo thứ tự ưu tiên:
  1. `Priority 1`: Các sản phẩm được link tường minh trong Brief / Bảng so sánh (Decision Table).
  2. `Priority 2`: Tìm kiếm theo từ khóa đã lọc sạch stopword.
  3. `Priority 3`: Chỉ fallback trong phạm vi cùng Collection, **nghiêm cấm fallback mù ra toàn catalog**.

### 5.3. Khâu Hậu Xử Lý HTML & Fact Audit (`html_postprocessor.py` & `article_fact_auditor.py`)
* **Price Corruption Healing:** Hàm `heal_corrupted_prices` sử dụng negative lookbehind `(?<=[(\s>]),\d{3}` để thay thế giá bị mất dấu `$` hoặc cụt số (`range from .10 to ,371.10` -> `$2,348.10 to $3,371.10`), đồng thời không làm hỏng các chuỗi giá hợp lệ có dấu phẩy ngăn cách hàng nghìn.
* **HTML Unescaping trong FAQ:** Loại bỏ việc bọc mù `html.escape()` lên câu trả lời FAQ. Giữ nguyên vẹn các thẻ HTML hợp lệ (`<a>`, `<strong>`, `<em>`, `<p>`), đảm bảo không còn lỗi link biến thành `&lt;a href="..."&gt;`.
* **Nhận diện Ngữ cảnh Phủ định (Negation Context Awareness):** Trong `article_fact_auditor.py`, các kiểm tra cấm (forbidden claims) phải phân biệt được câu phủ định hợp lệ (`not`, `does not`, `never`, `rather than`) và câu hỏi FAQ (`does ... include ...?`). Không phạt nhầm câu khẳng định đúng chính sách: *"Standard shipping does not include wall mounting or installation services"*.
* **Domain Normalization:** Tự động chuyển đổi các internal links trỏ về subdomain kỹ thuật (`wrydeco.myshopify.com`) sang domain chính thức (`https://wrydeco.com`).

### 5.4. Khâu Xuất Bản & Live Verification (`shopify_publisher.py` & `verify_live.py`)
* **Create-Only Protection:** Chặn 100% mutation sửa bài cũ thuộc `baseline_manifest.json`.
* **Routing 404 Fallback:** Khi URL custom domain (`https://wrydeco.com/blogs/...`) trả về 404 do hạ tầng DNS/proxy bên ngoài chưa cấu hình route `/blogs/`, hệ thống tự động fallback kiểm tra live verification trên `myshopify_url` (`https://wrydeco.myshopify.com/blogs/...`) để xác thực tính toàn vẹn của layout, hình ảnh và DOM mà không làm nghẽn tiến trình xuất bản.

---

## 6. Bộ Kiểm Thử Tự Động Cô Lập (Test Suite 9/9 Passed)

Để đảm bảo không bao giờ làm rò rỉ dữ liệu hoặc thay đổi file cấu hình thật khi chạy kiểm thử, file `test_suite.py` được thiết kế chạy hoàn toàn trong môi trường cô lập:

* **9 Bộ Test Độc lập:**
  1. `test_01_proxy_isolation_and_fail_closed`
  2. `test_02_store_manager_crud_and_extra_fields`
  3. `test_03_store_profile_manager_revision_concurrency`
  4. `test_04_article_fact_auditor_claim_detection_and_blocking`
  5. `test_04b_price_corruption_detection_and_healing`
  6. `test_05_image_canonicalization_and_publisher_create_only_guard` *(Đã bọc trong `tempfile.TemporaryDirectory()`)*
  7. `test_06_campaign_manager_idempotency_and_pilot_cohort`
  8. `test_07_web_ui_settings_profile_section`
  9. `test_08_zero_live_config_side_effects` *(Xác thực `data/stores.json` và `data/proxy.json` nguyên vẹn 100%)*

* **Lệnh chạy kiểm thử nhanh:**
```powershell
D:\Python-3-12\python.exe test_suite.py
```
> Kết quả mong đợi: `all_passed: true, passed_count: 9`.

---

## 7. Hướng Dẫn Vận Hành Batch Production & Thông Báo

### 7.1. Mẫu lệnh Prompt khuyến nghị cho Antigravity CLI

Khi yêu cầu mở rộng bài viết, người dùng nên chia thành các batch từ **3 đến 5 bài**:

> `/goal Hãy dùng mcp server wrydeco-blog-scaling-mcp để viết và xuất bản batch 3 bài tiếp theo cho store WRYDECO theo đúng flow đã sửa. Hoàn thành thì thông báo qua /mod-notifications cho tôi.`

### 7.2. Tích hợp `mod-notifications`

Sau khi batch bài viết hoàn tất hoặc gặp sự cố cần chú ý, hệ thống tự động thực hiện 2 thông báo độc lập:

1. **Windows Desktop Toast:**
   ```powershell
   mod toast "Xuất bản hoàn tất 3 bài viết WRYDECO" "Đã xuất bản thành công 3 bài viết catalog WRYDECO lên Shopify & Web Tool."
   ```
2. **Mobile / Remote Notification (ntfy):**
   ```powershell
   mod notify send "Xuất bản thành công 3 bài viết WRYDECO: Tree Bookshelves, Floating Tree Bookshelf, Fluted Shelves. Hiển thị hoàn hảo trên https://wrydeco.b6-team.site/blogs." --title "WRYDECO Blog Scaling Complete" --priority high --tags tada
   ```

---

## 8. Bảng Mã Lỗi & Cách Khắc Phục Nhanh

| Mã lỗi (`error_code`) | Trạng thái (`state`) | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- | :--- |
| `PROXY_BLOCKED` | `BLOCKED_PROXY` | Proxy bị ngắt kết nối hoặc cấu hình proxy sai trong `data/proxy.json`. | Kiểm tra `mod proxy test` hoặc kiểm tra lại file `data/proxy.json`. |
| `PROFILE_INVALID` | `BLOCKED_PROFILE` | Editorial Profile của store chưa hoàn tất hoặc mâu thuẫn chính sách. | Truy cập `http://127.0.0.1:8765/settings`, kiểm tra lại các trường policy của store. |
| `FACT_UNSUPPORTED` | `BLOCKED_FACTS` | Bài viết chứa giá bị corrupt, vi phạm claim chính sách, hoặc format sai. | `article_fact_auditor` sẽ tự động kích hoạt `heal_corrupted_prices` hoặc yêu cầu sửa nội dung trước khi cấp `ready_digest`. |
| `INSUFFICIENT_IMAGES` | `BLOCKED_MEDIA` | Số lượng ảnh body hợp lệ nằm ngoài khoảng 4 đến 7 ảnh. | `article_image_service` sẽ tự động bổ sung ảnh từ catalog media pool của chính collection đó. |
| `LIVE_VERIFY_FAILED` | `LIVE_FAILED` | Layout vỡ hoặc ảnh không hiển thị qua 16 kiểm tra Playwright. | Kiểm tra `output/<store_id>/<handle>_verify_report.json`, kiểm tra xem domain công khai có bị 404 không; dùng fallback `myshopify_url`. |
| `ZBIGTEE_SYNC_PENDING` | `ZBIGTEE_SYNC_PENDING` | Shopify đã tạo bài thành công nhưng ZBigTee API timeout khi mark published. | Gọi `resume_run` để đồng bộ lại trạng thái ZBigTee mà không tạo trùng bài trên Shopify. |
