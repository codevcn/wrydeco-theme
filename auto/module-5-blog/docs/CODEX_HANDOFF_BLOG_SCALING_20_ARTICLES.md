# TÀI LIỆU BỐI CẢNH DỰ ÁN: MỞ RỘNG BÀI VIẾT BLOG CHO 5 STORE SHOPIFY (HANDOFF TO CODEX)

> **Mục đích tài liệu:** Cung cấp toàn bộ bối cảnh hệ thống, dữ liệu thực tế, yêu cầu nghiệp vụ và ràng buộc kỹ thuật để **Codex** nghiên cứu và lập kế hoạch (Plan) triển khai hoàn thành mục tiêu xuất bản tối thiểu 20 bài viết mới cho mỗi store.  
> **Lưu ý phân định vai trò:**  
> - File này **chỉ mô tả bối cảnh, thực trạng, yêu cầu và đề xuất hướng kiến trúc**, **không** đưa ra plan hành động chi tiết. Việc thiết kế kế hoạch chi tiết thuộc trách nhiệm của Codex.  
> - Các tác vụ tối ưu và thực thi bài viết sẽ do **AI Agent Antigravity CLI** hiện diện trên máy chủ này đảm nhiệm. Codex có nhiệm vụ lên plan và thiết kế **1 MCP Server** làm công cụ chuẩn hóa cho Antigravity CLI thực thi.  
> - **LƯU Ý ĐẶC BIỆT:** Toàn bộ đề xuất trong file này cần được kiểm tra lại bởi Codex trước khi đưa vào kế hoạch triển khai chính thức.

---

## 1. Bối cảnh công cụ `auto/module-5-blog` (Local Pipeline)

`auto/module-5-blog` là bộ công cụ tự động hóa chạy cục bộ (local) được xây dựng để làm cầu nối giữa hệ sinh thái quản lý nội dung (**Zbigtee**) và các cửa hàng thương mại điện tử (**Shopify Stores**).

### 1.1. Cấu trúc thư mục & các module chính
- **`auto/module-5-blog/web_app.py`:**  
  Giao diện Web UI local (chạy tại cổng mặc định `http://127.0.0.1:8765`), cho phép người dùng xem trước bài viết, kiểm tra chất lượng và kích hoạt thủ công các nút chức năng (ví dụ: *Sync to Store & Verify Live*).
- **`auto/module-5-blog/pipeline.py`:**  
  Trình điều phối luồng xử lý trung tâm: tiếp nhận payload HTML/JSON từ Zbigtee, đưa qua bộ tiền xử lý HTML, gọi module đăng bài Shopify, và kích hoạt kiểm thử xác thực live.
- **`auto/module-5-blog/html_postprocessor.py`:**  
  Bộ xử lý và chuẩn hóa HTML chuyên sâu:
  - Chuẩn hóa cấu trúc tiêu đề (`H1`, `H2`, `H3`), bảng biểu, danh sách, internal link.
  - Xử lý các thẻ hình ảnh `<figure>` và `<img>` (bổ sung `alt`, `loading="lazy"`, responsive markup).
  - Kiểm tra độ dài nội dung (tối thiểu từ 1,200 – 1,800+ từ) và kiểm tra số lượng hình ảnh tối thiểu (mặc định yêu cầu >= 4 hình ảnh).
  - *Hạn chế hiện tại:* Nếu Zbigtee trả về bài viết thiếu ảnh (< 4 ảnh), module này lập tức ném ngoại lệ `ValueError: CẢNH BÁO THIẾU ẢNH` và dừng luồng xử lý, buộc can thiệp thủ công.
- **`auto/module-5-blog/shopify_publisher.py`:**  
  Module phụ trách kết nối với Shopify Admin GraphQL API (hoặc REST Admin API) của từng store:
  - Tự động tìm hoặc tạo Blog Container tương ứng (ví dụ: `News`, `Guides`, `Buying Guides`).
  - Thực hiện mutation `articleCreate` hoặc `articleUpdate` với HTML body đã qua xử lý, trích xuất `summary_html`, thiết lập `image` đại diện (Featured Image), tags và tác giả.
  - Sử dụng thông tin cấu hình từ `auto/module-5-blog/data/stores/*.json` và token xác thực trong `admin/.env`.
- **`auto/module-5-blog/verify_live.py` & `test_suite.py`:**  
  Bộ kiểm thử chất lượng sau khi đăng bài:
  - Dùng Playwright điều khiển trình duyệt truy cập URL thực tế của bài viết qua mạng proxy US (`auto/module-5-blog/data/proxy_config.json`).
  - Kiểm tra 12 tiêu chí chất lượng nghiêm ngặt: HTTP 200, hiển thị đúng trên Desktop & Mobile, thẻ `canonical`, Open Graph, `H1` duy nhất, không vỡ layout, ảnh tải thành công không lỗi 404, schema JSON-LD hợp lệ. Chụp ảnh màn hình lưu vào thư mục artifacts.
- **`auto/module-5-blog/zbigtee_ui_operator.py`:**  
  Client tương tác trực tiếp với Zbigtee API (tRPC) bằng session cookies lưu tại `auto/module-5-blog/data/zbigtee_auth.json`.

---

## 2. Bối cảnh nền tảng Zbigtee

Zbigtee (`https://zbigtee.com`) là nền tảng quản trị chiến lược nội dung SEO, tích hợp dữ liệu từ Google Search Console (GSC) và AI Content Writer.

### 2.1. Cơ chế backend & API
- **Giao thức:** Sử dụng framework tRPC (`https://zbigtee.com/api/trpc/...`) trên nền Next.js.
- **Xác thực:** Dựa trên Cookie phiên đăng nhập (`session_token`) và Header Context Workspace ID (`01a0b213-65a2-712a-b349-85b9bd8fa591`). Cấu hình xác thực đã được lưu trữ sẵn sàng tại `auto/module-5-blog/data/zbigtee_auth.json`.
- **Các endpoint tRPC trọng yếu:**
  - `content.list`: Quản lý danh sách thẻ bài viết trên bảng Kanban (`WRITING`, `REVIEW`, `PUBLISHED`, `ARCHIVED`).
  - `plan.list`: Danh sách các đề xuất kế hoạch bài viết do hệ thống tổng hợp từ dữ liệu GSC, catalog sản phẩm, hoặc vùng chủ đề.
  - `content.setStatus`: Cập nhật trạng thái thẻ nội dung (chuyển sang `published` sau khi đã sync thành công lên Shopify).
  - `plan.accept`: Chấp nhận đề xuất trong kế hoạch để đưa vào hàng đợi viết bài.

### 2.2. Danh sách 5 Store quản lý
Hệ thống hiện quản lý 5 dự án tương ứng với 5 store Shopify:
1. **WRYDECO** (`wrydeco.com` / `wrydeco.myshopify.com`): Đồ gỗ nội thất thủ công trang trí, kệ cây gắn tường (`tree bookshelves`, `floating shelves`).
2. **DizzyCustom** (`dizzycustom.com` / `dizzycustom.myshopify.com`): Phụ kiện xe hơi tùy biến kim loại 3D (`metal auto emblems`, `custom letters`, `skull badges`).
3. **Jeminise** (`jeminise.com` / `jeminise.myshopify.com`): Chăn ga gối đệm in họa tiết theo chủ đề (`printed bedding sets`, `quilts`, `comforter sets`).
4. **Chillgen** (`chillgen.com` / `chillgen.myshopify.com`): Thảm trang trí phòng và lớp học (`classroom rugs`, `reading corner rugs`, `decor`).
5. **Preaureum** (`preaureum.com` / `preaureum.myshopify.com`): Túi xách thời trang in họa tiết, quà tặng cá nhân hóa (`tote bags`, `handbags`, `personalized gifts`).

### 2.3. Hạn chế hiện tại của AI Writer trên Zbigtee
- **Không có cơ chế tự động đăng (Publish):** Zbigtee chỉ sinh ra nội dung dạng Draft và cung cấp các nút copy thủ công (Copy HTML, Copy Markdown).
- **Vấn đề chất lượng ảnh do Zbigtee sinh ra:**
  - Thường chỉ chèn từ 1 đến 2 ảnh, dẫn đến việc vi phạm ngưỡng tối thiểu của pipeline xuất bản.
  - Thường xuyên lấy lại một ảnh giống hệt nhau chèn liên tiếp thành 2 thẻ `<figure>` trùng lặp.
  - Sử dụng link CDN bên thứ ba không ổn định hoặc URL bị hỏng.
- **Vấn đề nội dung suy diễn (Hallucinations):** AI Writer của Zbigtee thường có xu hướng tự "sáng tác" ra các dịch vụ không có thật để lấp đầy số từ (ví dụ: tự ý đưa ra "đội thợ chuyên nghiệp đến tận nhà lắp đặt với giá $2,079" cho store bán kệ treo tường, hoặc bịa ra chính sách đổi trả/bảo hành 10 năm sai lệch).

---

## 3. Mục tiêu hoàn thành Task

- **Chỉ tiêu định lượng:** Tạo và xuất bản thành công **ít nhất 20 bài viết MỚI cho MỖI store** (Tổng cộng tối thiểu **100 bài viết mới** cho cả 5 store: Wrydeco, DizzyCustom, Jeminise, Chillgen, Preaureum).
- **Tiêu chuẩn chất lượng:**
  1. Toàn bộ 100 bài viết mới phải được sync thành công lên Shopify blog thật qua GraphQL Admin API.
  2. Toàn bộ bài viết phải vượt qua bộ kiểm thử tự động 12 tiêu chí của `verify_live.py` (Desktop/Mobile, HTTP 200, SEO metadata, layout toàn vẹn, hình ảnh hiển thị sắc nét).
  3. Thẻ tương ứng trên Zbigtee phải được cập nhật trạng thái `published`.

---

## 4. Phân tích dữ liệu thực tế & Lưu ý về 2 nhãn trên Zbigtee

Quá trình quét dữ liệu trực tiếp trên tRPC `plan.list` của cả 5 store trả về các phát hiện kỹ thuật đặc biệt quan trọng sau:

### 4.1. Nhãn "Sửa trang có sẵn" (`action: improve`)
- **Bản chất kỹ thuật:** Trong schema của Zbigtee, mỗi đề xuất có trường `action`. Khi `action == 'improve'`, đề xuất đó có trường `targetPath` trỏ đến một bài viết blog cũ hoặc một trang sản phẩm đã tồn tại. Mục đích của dạng đề xuất này là bổ sung câu trả lời FAQ hoặc củng cố yếu tố uy tín (Trust factor) vào trang cũ.
- **YÊU CẦU NGHIỆP VỤ BẮT BUỘC:**  
  Các đề xuất "Sửa trang có sẵn" **TUYỆT ĐỐI KHÔNG ĐƯỢC TÍNH VÀO CHỈ TIÊU 20 BÀI VIẾT MỚI**. Chỉ những đề xuất có `action == 'create'` (và `targetPath == null`) mới được coi là bài viết mới.
- **Hiện trạng số lượng bài mới (`action: create`) của 5 store:**
  - **WRYDECO:** Tổng 25 đề xuất = 5 "Sửa trang có sẵn" + **20 bài viết MỚI** *(Vừa đủ mốc 20)*.
  - **DizzyCustom:** Tổng 27 đề xuất = 2 "Sửa trang có sẵn" + **25 bài viết MỚI** *(Dư 5 bài)*.
  - **Jeminise:** Tổng 31 đề xuất = 6 "Sửa trang có sẵn" + **25 bài viết MỚI** *(Dư 5 bài)*.
  - **Chillgen:** Tổng 24 đề xuất = 0 "Sửa trang có sẵn" + **24 bài viết MỚI** *(Dư 4 bài)*.
  - **Preaureum:** Tổng 14 đề xuất = 0 "Sửa trang có sẵn" + **14 bài viết MỚI** *(⚠️ Hiện thiếu 6 bài để đạt mốc 20)*.

### 4.2. Nhãn cảnh báo màu vàng: *"Chưa nối được với truy vấn nào — vùng chủ đề nên viết bằng ngôn ngữ của site"*
- **Bản chất kỹ thuật:**
  - Thuộc tính trong dữ liệu thô:
    ```json
    {
      "purpose": "adjacent",
      "source": "territory",
      "sourceRef": "3d metal letters for vehicle",
      "action": "create",
      "targetPath": null,
      "evidence": {
        "note": "Chưa nối được với truy vấn nào — vùng chủ đề nên viết bằng ngôn ngữ của site",
        "queries": [],
        "existingPages": 0
      }
    }
    ```
  - Các đề xuất này xuất phát từ nguồn **`source: "territory"` (Vùng chủ đề tiềm năng)** nhằm mục đích **`purpose: "adjacent"` (Mở rộng từ khóa ngách lân cận)**.
  - Do là chủ đề mở rộng đón đầu, Google Search Console hiện tại chưa có dữ liệu click/impression cho cụm từ này trỏ về store (`queries: []`).
  - Dòng chữ *"vùng chủ đề nên viết bằng ngôn ngữ của site"* là template thông báo mặc định của Zbigtee để nhắc nhở người dùng nhập tên vùng chủ đề theo đúng ngôn ngữ bản địa của store (ở đây toàn bộ các cụm chủ đề đều đã là tiếng Anh chuẩn).
- **Định hướng xử lý:**  
  Đây là **thông tin trạng thái bình thường**, không phải lỗi chặn hệ thống. Các đề xuất này **hoàn toàn đủ điều kiện và rất nên viết** để mở rộng tầm phủ SEO cho website.

---

## 5. Yêu cầu tối ưu quy trình xử lý bài viết

Quy trình trước đây mang tính thủ công: Bấm từng bài trên Web UI local (`:8765`), gặp lỗi thiếu ảnh hoặc claim ảo thì người dùng phải nhờ AI sửa tay từng file rồi mới sync lại. Với quy mô 100 bài viết, quy trình này không thể đáp ứng.

Quy trình mới cần được tối ưu tự động hóa triệt để nhằm giải quyết 2 bài toán lớn:

### 5.1. Bài toán về hình ảnh (Image Quality & Catalog Matching)
- **Không để bài viết bị thiếu ảnh:**  
  Bài viết phải luôn đạt từ 4 đến 7 ảnh chất lượng cao, phân bổ đều ở các đề mục lớn. Thay vì ném lỗi văng chương trình khi Zbigtee trả về thiếu ảnh, hệ thống cần có cơ chế tự động bù ảnh (Auto-Image Healing) dựa trên ngữ cảnh bài viết và danh mục sản phẩm có sẵn của từng store.
- **Không dùng sai ảnh, nhầm ảnh:**  
  Ảnh bổ sung phải lấy từ chính catalog sản phẩm thật của store tương ứng (sử dụng thư viện ảnh sản phẩm Shopify đã có hoặc folder dữ liệu catalog local). Không được lấy ảnh ngẫu nhiên hoặc ảnh không khớp với chủ đề bài viết.
- **Khử trùng lặp ảnh (Deduplication):**  
  Tự động quét và loại bỏ các khối `<figure>` có hình ảnh giống nhau hoặc trùng lặp `src` / `alt` nằm cạnh nhau.

### 5.2. Bài toán về thông tin & tính xác thực (Fact & Policy Guardrail)
- **Triệt tiêu thông tin bịa đặt / suy diễn:**  
  Bài viết của AI thường tự bịa ra các dịch vụ không có trong mô hình kinh doanh (ví dụ: lắp đặt tận nhà, dịch vụ khoan tường trọn gói giá trên trời, bảo hành sai lệch...). Cần có cơ chế kiểm duyệt và tự động thay thế bằng các thông điệp chuẩn mực (ví dụ: tự lắp đặt dễ dàng DIY bằng ốc vít đi kèm, hoặc thuê thợ địa phương nếu cần).
- **Đúng chính sách thực tế của từng store:**  
  Mọi cam kết về thời gian giao hàng, phí vận chuyển, chính sách đổi trả (30 ngày) và bảo hành phải bám sát chính sách chính thức được định nghĩa trong dữ liệu cấu hình store.
- **Tính khách quan của bảng so sánh:**  
  Các bảng so sánh sản phẩm cần đặt trong đúng bối cảnh của thương hiệu (ví dụ: so sánh giữa các dòng sản phẩm khác nhau trong bộ sưu tập của chính store đó, không bịa đặt tên sản phẩm không tồn tại).

---

## 6. Phân định vai trò & Nhiệm vụ của Codex

### 6.1. Ràng buộc về phân định trách nhiệm
1. **Antigravity CLI (Local Agent):**  
   - Là AI Agent đang trực tiếp điều khiển thiết bị này, có toàn quyền chạy script, truy cập codebase `auto/module-5-blog`, kết nối database/API và thao tác với Playwright / Shopify Admin.  
   - Toàn bộ công việc thực thi tối ưu quy trình xử lý bài viết và triển khai sync thực tế sẽ do **Antigravity CLI** đảm nhận.
2. **Codex:**  
   - Nhiệm vụ trọng tâm của Codex là **tiếp nhận bối cảnh này để lập kế hoạch tổng thể (Plan)** cho dự án 20 bài viết mới mỗi store.  
   - Codex cần **thiết kế và xây dựng 1 MCP Server (Model Context Protocol)** chuyên dụng, đóng vai trò là bộ công cụ thực thi tiêu chuẩn (standardized tools & execution interface) cung cấp cho Antigravity CLI. MCP Server này sẽ giúp Antigravity CLI nắm bắt chính xác logic xử lý bài viết, kiểm tra tính hợp lệ về ảnh và fact, và thực hiện tối ưu quy trình một cách nhất quán.

### 6.2. Đề xuất gợi ý hướng làm (Architectural Suggestions - Toàn bộ đề xuất cần được kiểm tra lại bởi Codex)
*Lưu ý: Dưới đây chỉ là các gợi ý kỹ thuật sơ bộ. Toàn bộ đề xuất trong mục này cũng như trong toàn bộ file cần được kiểm tra lại bởi Codex trước khi đưa ra quyết định kiến trúc và lập plan chính thức:*
- **Gợi ý về kiến trúc MCP Server cho Antigravity:**  
  Codex có thể cân nhắc thiết kế các tool trong MCP server xoay quanh các năng lực:
  - *Tool tra cứu Catalog & Kho ảnh:* Cho phép Agent truy vấn hình ảnh sản phẩm chuẩn xác theo danh mục hoặc từ khóa của store (`query_store_catalog_assets`).
  - *Tool kiểm duyệt & chuẩn hóa nội dung (Guardrail Tool):* Cho phép Agent gửi HTML vào để nhận diện các claim rủi ro (lắp đặt tận nhà, bảo hành ảo) và trả về nội dung đã được làm sạch theo policy của store (`sanitize_article_claims`).
  - *Tool tự động bù ảnh (Image Auto-Healer):* Nhận diện các vị trí thiếu ảnh trong HTML và tự động ghép hình ảnh phù hợp từ catalog (`heal_article_images`).
  - *Tool đồng bộ và xác thực bài viết (Sync & Verify Tool):* Trigger luồng publish trực tiếp qua GraphQL và nhận kết quả Playwright test (`publish_and_verify_article`).
- **Gợi ý về giải pháp cho Preaureum:**  
  Vì Preaureum mới có 14 bài mới (thiếu 6 bài), Codex có thể lên phương án bổ sung 6 chủ đề ngách dựa trên danh mục túi xách/quà tặng của store này để nạp vào kế hoạch.
- **Gợi ý về chiến lược vận hành theo đợt (Rolling Batches):**  
  Nên tổ chức quy trình thực thi theo từng lô (ví dụ 5 bài/lần) để đảm bảo việc sinh nội dung, làm sạch và xuất bản diễn ra mượt mà, không gây quá tải cho AI Writer trên Zbigtee hay hệ thống mạng.

---

*Tài liệu này được lưu trữ tại `doc/CODEX_HANDOFF_BLOG_SCALING_20_ARTICLES.md` để phục vụ làm tài liệu đầu vào hoàn chỉnh cho Codex.*
