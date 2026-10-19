# BẢNG KIỂM TRA CHUẨN HÓA VẬN HÀNH BLOG SCALING (OPERATIONAL CHECKLIST)

Bảng kiểm tra này áp dụng cho toàn bộ các bài viết được sản xuất qua **MCP Server (`mcp_server.py`)** và **Pipeline (`pipeline.py`)** của store WRYDECO và các store vệ tinh.

---

## 1. Khâu Chuẩn Bị Brief (`prepare_article_brief` & MCP)

- [ ] **Trích xuất từ khóa trước khi search:** Bóc tách `clean_kw` từ `raw_topic_title` bằng Regex trước khi gọi `search_products`.
- [ ] **Smart Collection Mapping:** Tự động ánh xạ từ khóa sang handle collection tương ứng:
  - `wine` + `wall` -> `wall-mounted-wine-rack`
  - `wine` -> `wine-racks`
  - `tree` + `bookshelf` / `shelf` -> `tree-bookshelves` hoặc `wall-mounted-tree-bookshelves`
  - `fluted` -> `floating-shelves`
- [ ] **30-Item Cap Guard (ZBigTee API):** Bắt buộc đặt **100% sản phẩm catalog thật có đầy đủ handle, giá, kích thước, ảnh lên vị trí 0..4** (đầu mảng `verified_facts`).
- [ ] **Chặn Fallback Mù:** Nghiêm cấm bốc sản phẩm ở đầu store (gương, tranh...) khi bài viết về kệ/bàn ghế; chỉ fallback trong cùng collection.
- [ ] **Đồng bộ Artifact & Metadata:** Lưu file preview dạng `input/{store_id}/{content_id}_preview.json`. Cập nhật đầy đủ `handle`, `shopify_url`, `public_url` vào run file; tự động xóa `last_error_code` khi retry thành công.

---

## 2. Khâu Chữa Lành Ảnh (`article_image_service.py`)

- [ ] **Bộ lọc Stopword thương mại:** Bổ sung các từ `buying`, `guide`, `tips`, `ideas`, `review`, `fit`, `capacity`, `dimensions` vào `STOPWORDS` để tránh truy vấn trả về 0 kết quả trên Shopify GraphQL.
- [ ] **Ưu tiên Catalog Media Pool:** Nhặt ảnh theo thứ tự ưu tiên:
  1. Sản phẩm xuất hiện trong Brief và Decision Table.
  2. Sản phẩm tìm kiếm theo từ khóa đã làm sạch stopword.
  3. Sản phẩm trong cùng Collection (không ra ngoài danh mục).
- [ ] **Định lượng & Định danh ảnh:** 4 đến 7 ảnh body + 1 ảnh hero riêng biệt; kiểm tra perceptual hash (`ahash`, `dhash`, `sha256`) chống trùng lặp ảnh.

---

## 3. Khâu Hậu Xử Lý HTML & Fact Audit (`html_postprocessor.py` & `article_fact_auditor.py`)

- [ ] **Thuật toán Price Healing:** Dùng negative lookbehind `(?<=[(\s>]),\d{3}` trong `heal_corrupted_prices` để chống nuốt dấu `$` và chống cụt số (`range from .10 to ,371.10` -> `$2,348.10 to $3,371.10`).
- [ ] **Bảo toàn thẻ HTML trong FAQ:** Không bọc mù `html.escape()` lên câu trả lời FAQ. Giữ nguyên vẹn `<a href="...">`, `<strong>`, `<em>`, `<p>`, loại bỏ hoàn toàn lỗi link biến thành `&lt;a&gt;`.
- [ ] **Nhận diện Ngữ cảnh Phủ định (Negation Context Awareness):** Nhận diện đúng các câu phủ định hợp lệ (`not`, `does not`, `never`, `rather than`) và câu hỏi FAQ (`does ... include ...?`), không phạt nhầm câu đúng chính sách store.
- [ ] **Chuẩn hóa Domain Nội bộ:** Tự động chuyển đổi các link nội bộ trỏ về subdomain kỹ thuật (`wrydeco.myshopify.com`) sang domain chính thức `https://wrydeco.com`.

---

## 4. Khâu Kiểm Thử, Vận Hành & Xuất Bản

- [ ] **Quy tắc Batch Production Tối ưu:** Chạy batch từ **3 đến 5 bài / lần prompt** qua MCP server `wrydeco-blog-scaling-mcp` để tránh tràn context và quá tải mạng.
- [ ] **Create-Only Protection:** Chặn 100% việc cập nhật hoặc ghi đè lên 39 bài viết thuộc `baseline_manifest.json`.
- [ ] **Routing 404 Fallback:** Khi URL custom domain (`https://wrydeco.com/blogs/...`) trả về 404 do hạ tầng DNS chưa route `/blogs/`, tự động fallback xác thực live trên `myshopify_url`.
- [ ] **Test Suite 9/9 Passed:** Bộ test tự động trong `test_suite.py` chạy cô lập trong `tempfile.TemporaryDirectory()`, không gây side-effect lên file cấu hình thật `data/stores.json` và `data/proxy.json`.
- [ ] **Tích hợp Thông Báo Đa Kênh (`mod-notifications`):** Tự động gửi đồng thời Windows Desktop Toast (`mod toast`) và Mobile Remote Notification (`mod notify send` qua ntfy) ngay khi mỗi batch hoàn tất.
