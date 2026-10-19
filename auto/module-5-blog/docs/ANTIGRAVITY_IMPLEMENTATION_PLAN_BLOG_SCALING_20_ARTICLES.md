# PLAN BÀN GIAO ANTIGRAVITY: BLOG SCALING CHO 5 STORE SHOPIFY

**Ngày lập:** 17/10/2026 · **Phiên bản:** 1.0 · **Trạng thái:** kế hoạch triển khai, chưa thực thi.

**Workspace duy nhất của dự án:** `D:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-app\auto\module-5-blog`.

Tài liệu này tổng hợp các quyết định đã chốt trong trao đổi với người dùng, đối chiếu code hiện tại, handoff cũ và dữ liệu website đã thu thập. Antigravity dùng tài liệu này để triển khai khi được giao thực hiện. Việc viết tài liệu không có nghĩa MCP Server, cấu hình store hay các tính năng dưới đây đã tồn tại.

## 1. Kết quả cần đạt và giới hạn thực thi

### 1.1. Hai phạm vi phải phân biệt

| Phạm vi | Yêu cầu |
| --- | --- |
| Mục tiêu nghiệp vụ toàn chiến dịch | Công cụ phải hỗ trợ đạt **20 bài mới/store**, tương ứng 100 bài mới cho 5 store. |
| Phạm vi triển khai hệ thống | MCP Server cho Antigravity CLI; cấu hình biên tập riêng 5 store; kiểm tra sản phẩm/ảnh qua Shopify API; proxy Settings bắt buộc; xử lý ảnh và kiểm duyệt claim; báo cáo và khả năng chạy lại. |
| Phạm vi nghiệm thu thực tế sau triển khai | **3 bài viết mới đầu tiên của Preaureum + 3 bài viết mới đầu tiên của WRYDECO = 6 bài**, chạy bằng công cụ thật, có xác minh live. |
| Không phải điều kiện nghiệm thu | Không cần chạy thử 20 bài/store; không yêu cầu xuất bản hoặc kiểm thử E2E 100 bài để chứng minh triển khai đạt. |
| Đầu việc bổ sung | Chuẩn bị 6 chủ đề mới cho Preaureum, khử trùng trước khi thêm vào Plan. |

**Ưu tiên yêu cầu mới nhất của người dùng:** phần handoff cũ yêu cầu nghiệm thu toàn bộ 100 bài bằng 12 kiểm tra phải được hiểu lại theo phạm vi 6 bài trên. Các gate bảo vệ sản phẩm, ảnh, claim, store và proxy vẫn là logic bắt buộc của công cụ cho mọi lần chạy; không nhân rộng đợt test nghiệm thu lên 100 bài.

Sau khi triển khai và hoàn thành 6 bài nghiệm thu, báo cáo kết quả và dừng đợt nghiệm thu. Không tự động đăng nốt các bài còn lại chỉ vì mục tiêu dài hạn là 100 bài. Sáu bài hợp lệ có thể đóng góp vào tiến độ chiến dịch, mỗi store tương ứng 3/20; không báo cáo thành 20/20.

### 1.2. Những quyết định bắt buộc

1. Có **section cấu hình biên tập riêng cho từng store** trong Settings; Antigravity phải đọc và tuân thủ trước khi viết/sửa bài.
2. Dùng **credentials đã cấu hình trong Settings của đúng store**, do backend giải quyết, để đọc Shopify API. Không đưa token/client secret vào prompt hay kết quả MCP.
3. Kiểm tra thông tin sản phẩm và danh tính ảnh bằng **Shopify API**. Playwright/Chrome phục vụ giao diện, xác minh cách hiển thị và kiểm tra live; không thay thế API bằng việc đoán từ HTML.
4. **Mỗi phiên giao tiếp với Shopify phải đi qua proxy Settings** tại `data/proxy.json`, gồm OAuth/token, Admin API, storefront, media/CDN, kiểm tra URL, retry và trình duyệt. Thiếu hoặc hỏng proxy thì dừng, không chuyển sang kết nối trực tiếp.
5. Ảnh phải đúng store, đúng sản phẩm/biến thể và đúng nội dung đoạn văn; không chọn ảnh ngẫu nhiên để đủ số lượng.
6. Nội dung không được bịa vật liệu, kích thước, set contents, dịch vụ, giá, bảo hành, giao hàng, hoàn trả hoặc các cam kết khác.
7. Dữ liệu cào 5 store là **nguyên liệu để biên soạn cấu hình**, không copy nguyên văn/nguyên khối vào section Settings.
8. Nghiệm thu phải **khởi chạy tool thật**, đi qua MCP/pipeline đã triển khai và kiểm tra bài live; không chỉ chạy unit test hoặc đưa ảnh chụp của bài cũ.

### 1.3. Phạm vi không làm

- Không sửa theme toàn store hay dựng lại storefront để xử lý một lỗi bài viết.
- Không thay credentials/proxy đang có bằng giá trị hardcode hoặc proxy của dịch vụ bên ngoài.
- Không sửa các bài có sẵn hoặc đề xuất `improve` như một cách tăng chỉ tiêu bài mới.
- Không lấy dữ liệu khách hàng/đơn hàng để phục vụ việc viết blog.
- Không đăng hàng loạt trước khi đợt 6 bài đáp ứng nghiệm thu.
- Trong lần lập plan này chỉ tạo file tài liệu; chưa chạy server, thay Settings, gọi mutation hay xuất bản bài.

## 2. Tài liệu đầu vào và mức độ tin cậy

Đường dẫn trong các bảng dưới đây được tính từ workspace nêu ở đầu tài liệu.

| Nguồn | Vai trò và cách dùng |
| --- | --- |
| `docs/CODEX_HANDOFF_BLOG_SCALING_20_ARTICLES.md` | Bối cảnh ban đầu; có một số nhận định cần sửa theo code và quyết định mới. |
| `data/store_editorial_research_2026-10-17.json` | Bộ dữ liệu website 5 store: 44 trang HTTP 200, 10 trang sản phẩm mẫu, 47 đoạn dẫn chứng trong phần seed đã đối chiếu văn bản. |
| `data/stores/<store_id>.json` | Định danh store, domain API thực tế, credentials, API version, mapping Zbigtee và cấu hình blog hiện có. Không copy toàn file ra log. |
| `data/proxy.json` | Nguồn cấu hình proxy vận hành bắt buộc. Không lấy mặc định trong tài liệu để ghi đè lên Settings hiện hành. |
| `input/<store_id>/` | Preview/Kanban đã lưu; cần phân biệt snapshot cũ với dữ liệu mới lấy lúc chạy. |
| `output/<store_id>/` | Artifact lịch sử; dùng phát hiện bài cũ, không coi sự tồn tại của file là bằng chứng bài đang live/đã đạt. |
| Kết quả kiểm tra Plan bằng Chrome ngày 17/10/2026 | Snapshot số đề xuất `create`/`improve`, cần đọc lại khi thực thi vì trạng thái có thể đổi. |

### 2.1. Giới hạn của bộ research

- Đây là dữ liệu đại diện gồm home, About, chính sách/FAQ/care phù hợp và hai sản phẩm mẫu/store; **không phải full catalog export**.
- Shopify storefront được tải cục bộ qua proxy Settings. Firecrawl `parse` phân tích 5 bundle HTML tĩnh từ nội dung công khai đã tải. Không dùng Firecrawl cloud crawl trực tiếp storefront vì connector đã dùng không hỗ trợ truyền proxy Settings riêng.
- `firecrawl_analysis.candidate_data` là kết quả mô hình chưa đáng tin để nhập cấu hình. Một số câu được gắn nhãn exact quote thực tế là diễn giải hoặc trỏ sai nguồn; đã giữ riêng kèm audit.
- Đọc ưu tiên `scope`, `implementation_handoff`, `stores[].research_summary`, `stores[].editorial_profile_seed`, rồi mở `sources` để kiểm chứng.
- Một đoạn khớp văn bản chỉ chứng minh website đã nói vậy tại thời điểm thu thập; chưa chứng minh thông tin đúng độc lập hoặc vẫn còn hiệu lực khi triển khai.
- `ready_to_apply=false`, sản phẩm/ảnh mẫu `api_verified=false` và không có duyệt thị giác. Không đổi thành true chỉ vì đã đọc file.
- Research không chứa credentials hay proxy secrets. Tiếp tục duy trì điều này trong các artifact mới.

### 2.2. Thứ tự ưu tiên khi có khác biệt

1. Yêu cầu trực tiếp mới nhất của người dùng trong hội thoại/tài liệu này.
2. Định danh và credentials runtime trong Settings của store đã chọn.
3. Bằng chứng Shopify API theo đúng sản phẩm/biến thể và chính sách chính thức đã kiểm tra hiện hành.
4. Cấu hình biên tập đã biên soạn, có version và dẫn nguồn.
5. Snapshot research và handoff lịch sử.
6. Nội dung Zbigtee, tên file ảnh, alt, nhãn marketing và suy luận của AI.

Mâu thuẫn giữa nguồn chính thức không được giải quyết bằng cách chọn số thuận lợi hơn. Đánh dấu trường đang xung đột, tránh sử dụng claim đó; chỉ block bài cần claim chưa thể giải quyết, không mặc định khóa mọi bài của store.

## 3. Định danh store, Plan và cách tính bài mới

### 3.1. Mapping dùng lúc bàn giao

| Store ID | Storefront | Admin domain đang lưu | Zbigtee project ID | Default blog trong cấu hình |
| --- | --- | --- | --- | --- |
| `wrydeco` | `wrydeco.com` | `wrydeco.myshopify.com` | `01a0d177-b16d-7976-975a-d0b8a7681b18` | `buying-guides` |
| `dizzycustom` | `dizzycustom.com` | `d60b93-5.myshopify.com` | `01a0b243-525e-742c-b223-2c9ca25ce9aa` | `news` |
| `jeminise` | `jeminise.com` | `f4hgwc-hu.myshopify.com` | `01a0d179-1697-79ba-b6b8-f82bc9ad934a` | `buying-guides` |
| `chillgen` | `chillgen.com` | `bbjttb-n9.myshopify.com` | `01a0b240-d54d-786b-94af-1ea1afaf8465` | `buying-guides` |
| `preaureum` | `preaureum.com` | `m1sigk-r0.myshopify.com` | `01a0d17a-4379-7e79-90be-523d9fbdd0a4` | `buying-guides` |

Các myshopify domain phỏng đoán theo brand trong handoff cũ không được dùng thay mapping thực tế. Code cấu hình hiện dùng API version `2026-07`; triển khai phải đọc version mỗi store và đối chiếu schema trước khi viết query/mutation. Tài liệu này không cung cấp GraphQL operation đã validate.

Default blog/author hiện có chỉ là snapshot cấu hình, chưa là bằng chứng destination live hợp lệ. Phải kiểm tra blog qua API; không tìm thấy thì báo lỗi rõ ràng, không âm thầm chọn blog đầu tiên hoặc tự tạo container.

### 3.2. Snapshot số đề xuất đã xác minh

| Store | `create` | `improve` | Tổng | Cách chuẩn bị danh sách hướng đến 20 bài mới |
| --- | ---: | ---: | ---: | --- |
| WRYDECO | 20 | 5 | 25 | Chọn từ 20 create sau kiểm tra trùng và khả năng viết đúng catalog. |
| DizzyCustom | 25 | 2 | 27 | Ưu tiên 20 create; phần còn lại làm dự phòng. |
| Jeminise | 25 | 6 | 31 | Ưu tiên 20 create; phần còn lại làm dự phòng. |
| Chillgen | 24 | 0 | 24 | Ưu tiên 20 create; phần còn lại làm dự phòng. |
| Preaureum | 14 | 0 | 14 | Cần bổ sung tối thiểu 6 chủ đề create không trùng. |

Các con số là số đề xuất tại thời điểm quan sát, không phải số bài mới đã hoàn tất. Nếu khử trùng/loại chủ đề không có sản phẩm phù hợp làm số khả dụng còn dưới 20, báo deficit thực tế và bổ sung chủ đề phù hợp; không ép một proposal không đạt thành hợp lệ.

### 3.3. Điều kiện một bài được tính là mới

- Proposal có `action=create` và `targetPath=null`; thiếu hoặc mâu thuẫn các trường này thì chưa đủ điều kiện.
- Được tạo trong đợt chiến dịch sau baseline, chưa nằm trong danh sách Shopify articles có sẵn tại thời điểm bắt đầu.
- Không phải cập nhật bài cũ, đổi handle/blog, bản sao nội dung hoặc xuất bản lại preview lịch sử.
- Có mapping duy nhất giữa store, plan item, content ID và Shopify article ID.
- Shopify xác nhận đã tạo đúng store/blog và bài được public theo luồng đã chọn.
- Trong đợt nghiệm thu: qua toàn bộ gate và kiểm tra live, đồng bộ trạng thái Zbigtee thành công. Nếu một bước sau thất bại, giữ trạng thái pending/failure đúng thực tế, không tính hoàn tất.

Thư mục output hiện có 21 file `*_processed.json` lịch sử (WRYDECO 5, DizzyCustom 4, Jeminise 4, Chillgen 4, Preaureum 4). Đây là đầu mối rà soát baseline, không khẳng định có đúng 21 bài đang public. Baseline phải lấy cả dữ liệu Shopify live và mapping Zbigtee, có phân trang đầy đủ.

Thông báo vàng về `purpose=adjacent`, `source=territory`, `queries=[]` không tự nó là lỗi chặn. Chủ đề vẫn cần đúng ngôn ngữ site, đúng catalog và khác search intent của bài đã có. Không tự tạo số liệu GSC để hợp thức hóa đề xuất.

## 4. Hiện trạng code và phần phải sửa

| Thành phần | Thực tế hiện tại | Thay đổi cần triển khai |
| --- | --- | --- |
| `store_manager.py` | Đã có StoreConfig, file riêng từng store, OAuth/access token và blog cache. | Bổ sung liên kết profile; scope/identity checks; giữ credentials phía server; bảo toàn field cũ khi save. |
| `proxy_manager.py` | Đã có mandatory proxy gate, requests session và Playwright proxy; dùng `data/proxy.json`. | Dùng thống nhất cho mọi đường mới, retry, redirect, media, token; kiểm thử không có direct fallback. |
| `zbigtee_ui_operator.py` | Có session, đọc Kanban/preview và đánh dấu published; có safety blocklist. | Thêm luồng Plan/create selection/writer khi thiếu, chỉ sau xác minh giao diện hoặc tRPC thực tế. Không đoán endpoint/field chỉ dựa handoff. |
| `html_postprocessor.py` | Xử lý HTML, placeholders, FAQ, scoped CSS; đã tắt SVG fallback. Chưa có kiểm tra cứng 4–7 ảnh/word count như handoff mô tả. | Tách normalization, claim audit, media healing và validation; bỏ hardcode tên ảnh WRYDECO và thay ảnh tuần tự. |
| `shopify_publisher.py` | Gọi GraphQL bằng credentials store; xử lý ảnh bằng HEAD/GET, Files và một số media catalog; có fallback pool. | Thêm catalog evidence service; bỏ chọn ảnh catalog bất kỳ; thêm create-only và pagination/idempotency; blog không đúng phải fail. |
| `pipeline.py` | Có sync và comprehensive editor; một số đường cho phép bỏ verify, vẫn có thể mark published; có đường catch exception rồi bỏ qua. | Một bộ gate dùng chung cho UI/CLI/MCP; trạng thái rõ từng bước, không nuốt lỗi và không báo ok toàn luồng khi verify/sync thất bại. |
| `verify_live.py` | 12 checks hiện có; Desktop 1440×900, Mobile 390×844; chụp màn hình. | Bổ sung kiểm tra thật canonical/OG/meta, số ảnh, media identity, links; sửa điểm đo layout có thể bị che bởi DOM mutations. |
| `web_app.py` | Dashboard, Settings, editor, sync API. | Thêm section store profile, lưu/validate/version; hiển thị run/progress/report; dùng cùng pipeline có gate. |
| `cli.py` | Có serve, stores, test-store, fetch-zbigtee, postprocess, sync, verify. | Giữ tương thích; thêm campaign/pilot entrypoint hoặc MCP; không để `--no-verify` trở thành đường bypass của đợt nghiệm thu. |
| `test_suite.py` | Có test dùng thật Settings: reset proxy từ docs, ghi proxy hỏng, tạo/xóa temp store, đổi active store. | Tách test isolation trước khi chạy; không chạy nguyên suite cũ lên cấu hình thật rồi coi là test an toàn. |

Các khác biệt cần nhớ:

- Handoff nói processor sinh SVG, nhưng implementation hiện chặn SVG. **Tiếp tục chặn SVG placeholder**, không bật lại để vượt số ảnh.
- Handoff nói tự tìm/tạo blog; `resolve_blog` thực tế có fallback về blog đầu tiên. Đường mới phải yêu cầu đúng blog thay vì ngầm chuyển destination.
- HEAD 200, `naturalWidth>0`, tên file hay alt không xác minh ảnh thuộc sản phẩm nào.
- `find_article_by_handle`/`find_article_across_blogs` đang dùng giới hạn first 100 articles và first 25 blogs; cần pagination để tránh tạo trùng khi store lớn.
- Không thay claim bịa về lắp đặt bằng claim bịa “kèm ốc vít, DIY dễ dàng”. Câu thay thế cũng phải có bằng chứng.

## 5. Kiến trúc triển khai đề xuất

### 5.1. Luồng tổng thể

`Antigravity CLI → MCP Server local (stdio) → services trong module-5-blog → ProxyManager → Shopify API/storefront/media`

Luồng nội dung: `Plan → baseline/dedup → store profile → catalog evidence → brief → Zbigtee draft → normalize → fact audit → image heal → final audit → publish → live verify → Zbigtee sync → report`.

Antigravity chịu trách nhiệm điều phối, đánh giá ngữ nghĩa/ảnh và sửa nội dung dựa bằng chứng. MCP/pipeline chịu trách nhiệm thi hành ràng buộc, gọi API, lưu trạng thái và chặn thao tác không hợp lệ. Không dùng prompt như lớp bảo vệ duy nhất.

### 5.2. Module dự kiến

Tên file dưới đây là đề xuất cần tạo khi triển khai, không phải các file đã tồn tại.

| File/module | Trách nhiệm |
| --- | --- |
| `mcp_server.py` | MCP stdio entrypoint; register tools; validate input; trả structured results; stdout chỉ dành cho protocol. |
| `store_profile_manager.py` | Schema, load/save/version và biên soạn runtime profile từng store. |
| `shopify_catalog_service.py` | Tra cứu product/variant/publication/media qua API và proxy, phân trang, evidence cache. |
| `article_fact_auditor.py` | Claim inventory, đối chiếu nguồn và tạo fact report; quản lý unresolved claims. |
| `article_image_service.py` | Chọn media theo ngữ cảnh, xác minh nguồn, tải kiểm tra qua proxy, khử trùng và phân bổ ảnh. |
| `campaign_manager.py` | Baseline, manifest, hàng đợi, idempotency/locks, tiến độ và resume. |
| `acceptance_runner.py` | Chạy đúng cohort 3+3 và tổng hợp bằng chứng nghiệm thu. |
| `data/store_profiles/<store_id>.json` | Cấu hình biên tập được biên soạn; tách khỏi credential JSON. |
| `schemas/store_editorial_profile.schema.json` | Schema cấu hình; giới hạn và kiểm tra cấu trúc. |
| `data/campaigns/<campaign_id>/` | Manifest/baseline/cohort/journal; không chứa secrets. |
| `output/<store_id>/runs/<run_id>/` | Brief, HTML, fact/media audit, API publish result, live report và screenshots theo từng lần chạy. |

Tận dụng StoreManager/ProxyManager/publisher/processor hiện có, không viết một pipeline thứ hai bỏ qua luồng cũ. UI, CLI và MCP phải gọi chung service và common final gate.

### 5.3. Quy tắc trạng thái và bất biến

- Mọi request MCP có `store_id` tường minh, không dùng active store toàn cục làm mặc định trong campaign.
- MCP chỉ nhận store ID có trong registry được phép; không nhận đường dẫn tùy ý thay store ID dù legacy StoreManager/CLI có khả năng load file theo path.
- Binding `store_id → shop domain → project_id → profile revision → destination blog` được khóa trong run context. Thay đổi store giữa bước không làm run đang chạy đổi đích.
- Dùng lock theo store/content và khóa publish idempotency; tránh hai client cùng tạo một bài.
- Draft đã thay HTML, profile revision, facts hoặc media phải mất trạng thái ready, được audit lại trước publish.
- Report gắn content hash, input revision và config revision. Publish chỉ chấp nhận đúng revision đã kiểm tra.
- Store profile không được cho phép tắt proxy hoặc bỏ kiểm tra ownership/publication để “chạy cho xong”.
- Không expose tool chạy arbitrary GraphQL, arbitrary shell hay download URL tùy ý nhằm né transport và gate.

## 6. Section cấu hình riêng cho từng store

### 6.1. Vai trò của section

Section này trả lời: **“Với store này, Antigravity phải viết cho ai, theo giọng nào, dùng nhóm sản phẩm nào, kiểm chứng thuộc tính gì, được nói và không được nói điều gì?”**

Đây là hướng dẫn vận hành có cấu trúc, không phải nơi chứa toàn bộ trang About, chính sách, kết quả Firecrawl hoặc một bài quảng cáo giới thiệu brand. Fact cụ thể của từng sản phẩm vẫn phải lấy API lúc chạy; không biến research snapshot thành catalog vĩnh viễn.

### 6.2. Cách biên soạn từ research, bắt buộc không copy/paste

1. Đọc `editorial_profile_seed` và nguồn đi kèm của đúng store.
2. Tách ba loại: sự thật thương hiệu/chính sách có nguồn, gợi ý biên tập do suy luận, trường đang thiếu hoặc xung đột.
3. Viết lại thành mệnh lệnh ngắn phục vụ việc viết bài, theo ngôn ngữ output của site (mặc định English/US); nhãn UI có thể dùng tiếng Việt.
4. Chuẩn hóa policy thành trường có điều kiện/phạm vi/ngoại lệ và source reference; không chỉ nhập một số “30 ngày” hoặc “free shipping”.
5. Chuyển các lỗi thường gặp thành rule cấm và checklist thuộc tính phải xác minh. Chỉ thêm câu thay thế khi câu đó cũng có bằng chứng.
6. Chỉ đưa nhóm sản phẩm/chủ đề thuộc store này; collection URL vẫn là candidate chờ kiểm tra đích live.
7. Đánh dấu điều chưa biết, không điền giá trị phỏng đoán để vượt schema. Trường warranty chưa biết không lấy thời hạn refund để thay.
8. Kiểm tra lại chính sách hiện hành qua proxy trước khi kích hoạt; lưu version/diff và dữ liệu nguồn riêng.
9. Đọc thử runtime profile như Antigravity: nội dung phải đủ để ra quyết định viết, không cần nuốt cả JSON research 1,3 MB.

**Ví dụ chuyển hóa vai trò:** thay vì dán câu About “Our handbags are made with durable leather-style material…”, cấu hình Preaureum nên hướng dẫn: “Use leather-style unless the selected product provides a verified composition. Never infer genuine leather, waterproofing, or raised texture from a printed design.” Nguồn FAQ nằm trong metadata; không dán cả FAQ vào ô hướng dẫn.

### 6.3. Nhóm field và semantics

| Nhóm | Nội dung cần lưu |
| --- | --- |
| Identity/version | `schema_version`, `store_id`, revision, updated_at, status, research reference. Store/domain tham chiếu Settings, không nhập lại credentials. |
| Editorial identity | Brand summary ngắn, audience, locale, tone, writing priorities, preferred/avoided wording. |
| Catalog scope | Product families/collections được ưu tiên; excluded/out-of-scope themes; thuộc tính bắt buộc kiểm chứng theo loại sản phẩm. |
| Policies | Shipping regions/fees, processing/transit, returns và exceptions, cancellation, warranty/care; mỗi claim có source, scope, checked_at, trạng thái verified/unknown/conflict. |
| Fact rules | Claims cần bằng chứng, forbidden claims, cách xử lý khi thiếu fact, quy tắc giá/stock/reviews. |
| Media rules | 4–7 ảnh body phù hợp, featured image, association product/variant, visual review, dedup, alt/caption, ngưỡng resolution vận hành. |
| Article rules | English/US, đáp đúng intent; mặc định tối thiểu 1.200 từ hữu ích, hướng đến khoảng 1.800+ khi chủ đề cần; heading/FAQ/table/internal links có nguồn. Không nhồi chữ. |
| Linking/CTA | Destination domain chính thức, blog đích đã verify, collection/product link hợp ngữ cảnh, CTA không hứa quá khả năng. |
| Evidence/unknowns | Source IDs/URLs, fetched_at, quote/path tham chiếu, người/agent biên soạn, unresolved fields và phạm vi bị chặn. |
| Runtime instructions | Bản hướng dẫn ngắn được dựng từ các field trên; không chứa secrets và không cho tự override gate toàn cục. |

Các ngưỡng ảnh, proxy, ownership, API evidence và create-only của campaign là ràng buộc chung. Store có thể bổ sung rule chặt hơn, không được làm yếu các gate này.

### 6.4. Hành vi UI và lưu cấu hình

- Trên `/settings`, chọn store thì hiển thị một section riêng “Quy tắc viết bài cho store”, nhìn rõ brand/domain đang chỉnh.
- Dùng form nhóm field có cấu trúc + ô hướng dẫn biên tập ngắn; không chỉ một textarea raw JSON dài.
- Có chức năng đọc research seed để hỗ trợ biên soạn, preview runtime instructions, validate, lưu revision và xem nguồn/unknowns. Không có nút nhập nguyên toàn bộ research thành active profile.
- Chuyển store không làm mất draft chưa lưu; không lưu nhầm sang store khác.
- Save chỉ cập nhật profile của store đích; không ghi lại token/proxy hoặc xóa field cấu hình cũ.
- API/MCP đọc profile trả bản public, không trả credentials; Settings credential panel tiếp tục theo luồng hiện có.
- Validate cần chỉ rõ trường lỗi và ảnh hưởng; conflict ở thời gian ship không tự biến thành một con số mặc định.
- Runtime không có profile hợp lệ thì chưa được publish bài campaign. UI có thể cho xem và biên soạn draft.

## 7. Nội dung cấu hình cần biên soạn cho 5 store

Các nội dung dưới đây là định hướng cấu hình dựa snapshot research, phải diễn đạt lại thành field/rule phù hợp. Con số policy cần recheck khi kích hoạt; không hardcode vào source code.

### 7.1. WRYDECO

**Định hướng:** nội thất gỗ tự nhiên thủ công; giọng điềm tĩnh, cụ thể, hiểu không gian và cách sử dụng. Giúp người đọc chọn kích thước, bố trí và bảo quản; tránh cam kết lắp đặt/an toàn không có chứng cứ.

- Nhóm catalog đã quan sát: tree/corner/floating bookshelves, floating shelves, coffee tables, wine racks, wood sculpture, cat/parrot trees, mirrors và bed frames. Chỉ dùng sản phẩm thực sự liên quan bài đang viết.
- Trước khi mô tả: xác minh kích thước từng option, finish, loài gỗ nếu có, hình thức giao/assembly, khả năng mounting/anchoring và bộ phận đi kèm.
- “Oak”, “Walnut” trong tên finish không tự chứng minh sản phẩm làm từ loài gỗ đó.
- Nursery/cat/parrot theme không tự chứng minh an toàn trẻ em/vật nuôi, khả năng leo trèo hay tải trọng.
- Research ghi nhận miễn phí standard shipping cho đơn đủ điều kiện worldwide; processing khoảng 15–20 business days, transit 3–5, tổng 18–25, có ngoại lệ với hàng custom/oversized. Không biến thành ngày đến đảm bảo.
- Standard shipping không gồm assembly/installation/wall mounting/placement nếu không được xác nhận bằng văn bản. Không hứa dịch vụ miễn phí hoặc tự gán giá thợ lắp.
- Return 30 calendar days chỉ cho damage/defect/fulfillment error đủ điều kiện; không phải đổi ý được trả. Approved eligible return có store-paid shipping và cần hướng dẫn bằng văn bản.
- Warranty công bố 1-year limited từ delivery, theo phạm vi/exclusions. Không viết 10 năm, lifetime hoặc thay mới vô điều kiện.
- Có cửa sổ đổi/hủy miễn phí 6 giờ; phần sau 6 giờ trước shipment chưa đủ rõ thì không tự đặt phí/quyền lợi. Đã ship thì không hủy in transit.
- Care: khăn mềm khô/hơi ẩm, tránh nhiệt/nắng và lau tràn; bôi dầu mỗi 6–12 tháng chỉ cho oil finish phù hợp.
- Author snapshot: `WRYDECO Studio`; blog snapshot `buying-guides`, phải kiểm tra live.

### 7.2. DizzyCustom

**Định hướng:** emblem tên/chữ kim loại cá nhân hóa cho xe; giọng trực tiếp, tập trung text, kích thước, finish và bề mặt gắn.

- Xác minh chất liệu, kích thước, maximum characters theo option, finish, adhesive và hướng dẫn gắn/tháo cho sản phẩm cụ thể.
- Không lấy một giới hạn số ký tự cho mọi size; không suy ra mọi bề mặt đều tương thích.
- Không hứa tháo không hại sơn, vĩnh viễn không phai, waterproof tuyệt đối, hợp pháp mọi phương tiện hoặc bảo hành trọn đời chỉ vì product copy có từ marketing.
- Không trích customer count/review/country count làm bằng chứng nếu chưa được xác thực.
- **Ba nhóm policy đang xung đột:** thời gian production/transit, phí ship `$6.95` so với “free shipping”, deadline báo lỗi 24 giờ so với 30 ngày.
- Shipping policy còn mô tả direct-to-garment không phù hợp catalog metal emblem. Không chọn số trong trang đó làm authoritative mà không xử lý mâu thuẫn.
- Cấu hình phải có `conflict` và rule “không đưa số cụ thể cho trường này”; vẫn có thể viết bài lựa chọn/thiết kế không phụ thuộc claim đó, dẫn người đọc đến policy/support hiện hành.
- Không tự sửa policy live của store trong task blog.
- Author snapshot `DizzyCustom Studio`, blog snapshot `news`.

### 7.3. Jeminise

**Định hướng:** bedding in họa tiết, blanket/quilt/comforter, cá nhân hóa và quà tặng; giọng ấm áp, rõ loại sản phẩm, size và thành phần set.

- Xác minh fabric composition, kích thước/size, set contents, kỹ thuật in và care từng sản phẩm.
- Printed patchwork/embroidered effect không đồng nghĩa ghép vải/thêu thủ công thật. Ảnh có gối không chứng minh mọi option kèm gối.
- Không tự gán 100% cotton, hypoallergenic, chứng nhận hay warmth rating.
- Research ghi nhận free standard shipping US/Canada; supported international khoảng `$5.99 USD/order`, không gồm duties/taxes. Processing khoảng 3 business days, transit 7–14, tổng 10–17, đều là ước tính.
- Hàng personalized/custom/POD/made-to-order thường final sale khi production bắt đầu; claim damage/defect/wrong/missing cần báo trong 7 calendar days từ recorded delivery, đúng điều kiện.
- Đổi/hủy phụ thuộc production; không đặt mặc định cửa sổ 2 giờ.
- Preview có thể yêu cầu trước production; không hứa mọi sản phẩm có automatic live preview.
- FAQ gợi ý cold gentle wash, mild detergent, tránh bleach/high heat; kiểm tra care cụ thể trước khi áp dụng cho một item.
- Chưa có cơ sở cho separate warranty duration; không lấy 7 ngày/return deadline thành bảo hành.
- Author snapshot `JEMINISE HOME`, blog snapshot `buying-guides`.

### 7.4. Chillgen

**Định hướng:** thảm personalized cho home/classroom/studio và quà tặng; giọng thân thiện, thực tế, giúp đo không gian và chọn bố cục.

- Xác minh fiber/backing, kích thước/shape, care/washability, intended placement và personalization thực tế.
- Không gán wool chỉ vì có bài cũ nói natural wool; không suy ra toàn catalog machine washable, non-slip, child-safe, stainproof hoặc dùng outdoor.
- Không nói artwork/album art/nhân vật/team logo được cấp phép nếu chưa có chứng cứ. Chủ đề có trong catalog không chứng minh quyền sở hữu trí tuệ.
- Research ghi nhận chỉ supported street addresses contiguous US gồm Washington, D.C.; loại Alaska/Hawaii, territories, P.O. Box, APO/FPO/DPO. Free standard, không minimum; processing 4–7 business days rồi transit 7–14, không guarantee.
- Standard non-custom đủ điều kiện có thể request return trong 30 ngày, unused/unwashed/uncut/unaltered, đúng packaging và prior authorization.
- Custom/personalized/made-to-order thường final sale sau processing bắt đầu; giữ ngoại lệ store error/remedy theo policy. Không hứa mọi return được cấp prepaid label.
- Care dùng hướng dẫn đúng sản phẩm, không một công thức giặt chung cho toàn store.
- Có ảnh sample music rug mang alt mô tả welcome doormat; alt không được quyết định danh tính ảnh. Cần đối chiếu API + xem ảnh thật.
- Author snapshot `CHILLGEN HOME`, blog snapshot `buying-guides`.

### 7.5. Preaureum

**Định hướng:** handbag leather-style cá nhân hóa, thể hiện sở thích/câu chuyện và quà tặng; giọng có cảm xúc nhưng cụ thể về tính năng và lựa chọn.

- Nhóm chủ đề đã quan sát: book lover, nurse, custom photo/text, butterfly, dragon, black cat, Highland cow, faith, holiday và các sở thích khác.
- Xác minh material composition, dimensions, compartments/straps/closure, personalization và included accessories theo product/variant.
- Dùng “leather-style” khi chỉ có bằng chứng FAQ ở mức đó; không mặc định genuine leather hay cả catalog là PU.
- “3D-effect” không chứng minh bề mặt nổi, chạm, dập hoặc thêu. Không dùng mô tả xúc giác sai với artwork in.
- Tên/ảnh “handbag and wallet set” không chứng minh option đang chọn kèm wallet. Phải chỉ rõ selected variant và set contents.
- Personalization/preview chỉ khi product page và dữ liệu liên quan cho phép; không hứa preview cho mọi sản phẩm.
- Research ghi nhận processing 2–5 business days; US free standard với transit 7–12 business days sau processing; international phí tại checkout và tùy destination.
- Eligible item unused/original packaging có return request 30 ngày; custom/personalized/final sale có exclusions. Damage/defect/wrong item báo trong 7 ngày. Đây không phải blanket 30-day return cho túi custom.
- Đổi/hủy sau processing/production/fulfillment không đảm bảo; không đặt cửa sổ hủy 2 giờ.
- Care: khăn mềm hơi ẩm; tránh ngâm, machine wash, hóa chất mạnh, nhiệt/nắng lâu. Không suy ra waterproof từ hướng dẫn lau ẩm.
- Author snapshot `PreAureum`, blog snapshot `buying-guides`.

## 8. Shopify API làm nguồn kiểm chứng sản phẩm và ảnh

### 8.1. Credentials và transport

- Resolve credentials bằng `StoreManager` theo `store_id` của run. Backend lấy/refresh token bằng luồng đã có; Antigravity không tự lấy token để gọi `requests`/curl tùy ý.
- Đọc API version từ cấu hình store; đối chiếu tài liệu/schema chính thức khi triển khai. Validate mọi GraphQL operation mới trước khi sử dụng, gồm field publication/media và article mutation; không dựa vào query mẫu nhớ từ phiên bản khác.
- Xác nhận shop identity trả về khớp store/domain trong run trước khi dùng kết quả catalog.
- Kiểm tra scopes thật sự cần cho sản phẩm/media, publication, blog/article và các field phụ trợ. Thiếu quyền thì báo cụ thể, không chuyển qua scrape để giả lập API verification.
- Không yêu cầu quyền order/customer để làm blog. Không tự mở rộng quyền app ngoài nhu cầu.
- Tận dụng `ShopifyPublisher._graphql` hoặc tách shared client dùng cùng StoreManager/ProxyManager; không tạo transport không proxy.
- Request có timeout hữu hạn, retry có backoff cho lỗi transient/throttling và xử lý GraphQL errors/userErrors rõ ràng. 401 chỉ refresh có giới hạn, không lặp vô hạn.
- Tự động retry mutation cần reconcile theo idempotency trước; timeout sau request không có nghĩa mutation chưa chạy.

### 8.2. Catalog evidence record

Mỗi sản phẩm được giới thiệu hoặc dùng làm cơ sở so sánh cần record tối thiểu:

| Nhóm | Nội dung |
| --- | --- |
| Identity | Store ID, shop identity, product GID, handle, title, URL chính thức, checked_at, API version. |
| Visibility | Product status và bằng chứng publication ở kênh Online Store phù hợp; không chỉ `ACTIVE`. |
| Variants | Variant GID, selected options, size/finish/material khi có nguồn, SKU nếu cần phân biệt; giá/currency/availability có thời điểm. |
| Product facts | Description/field/metafield đã được xác minh schema; giữ nguyên source field và đoạn hỗ trợ. Tên marketing không tự thành thông số kỹ thuật. |
| Media | Media ID, loại media, status, image URL, dimensions và association product/variant. Alt chỉ là metadata phụ. |
| Public check | URL storefront đúng sản phẩm, truy cập được qua proxy; không kết thúc ở password page, not-found template hoặc redirect sang sản phẩm khác. |
| Limitations | Trường không có dữ liệu, xung đột giữa text/variant, publication không đủ quyền và thuộc tính chưa chứng minh. |

Phân trang đầy đủ khi tìm catalog, variants, media, blogs và articles theo nhu cầu; không coi `first:10` là toàn bộ dữ liệu. Dùng API search/filter để thu hẹp rồi xác minh chính xác product ID; không tải mù toàn catalog cho mỗi bài.

### 8.3. “Có trên store live” phải được xác định thế nào

1. Product ID thuộc shop đã chọn, không phải shop khác có ảnh cùng CDN.
2. Không phải draft/archived; có bằng chứng publication thích hợp cho storefront và ngữ cảnh thị trường đang dùng.
3. URL public tương ứng truy cập đúng trang sản phẩm qua proxy; HTTP 200 một mình chưa đủ.
4. Selected variant và các thuộc tính được bài mô tả tồn tại trong dữ liệu đã đọc.
5. Nếu CTA nói “available/in stock/buy now” hoặc giá cụ thể: recheck availability/price của lựa chọn tương ứng. Sản phẩm published nhưng sold out không được mô tả là đang còn hàng.
6. Nếu chỉ đề cập sản phẩm sold out trong ngữ cảnh biên tập, phải nói đúng trạng thái, không dùng làm gợi ý mua đang có sẵn. Mặc định ưu tiên sản phẩm có thể mua.

API là nguồn identity/facts/publication; live HTTP/browser check xác nhận trang hiển thị thật. Hai lớp bổ sung nhau, không thay thế nhau. Không đủ bằng chứng publication thì trạng thái là unknown/blocked, không `verified=true`.

### 8.4. Mapping claim tới bằng chứng

Ví dụ record mang tính hợp đồng dữ liệu, chưa phải Shopify API code:

| Field | Ý nghĩa |
| --- | --- |
| `claim_id`, `location` | Câu/ô bảng/FAQ/caption/title/meta/alt nào đang chứa claim. |
| `claim_text`, `claim_type` | Nội dung và loại: material, dimensions, included items, price, shipping, warranty… |
| `source_type` | Shopify product/variant field, policy page hoặc nguồn biên tập ngoài đã được phép. |
| `source_ref`, `source_excerpt` | Product/variant GID + API field path, hoặc policy source ID/URL + đoạn chứng minh. |
| `checked_at`, `scope`, `status` | Thời điểm, phạm vi áp dụng và verified/unsupported/conflict/unknown. |
| `resolution` | Giữ, sửa có căn cứ, bỏ claim, thay đoạn hay block bài; có lý do và content hash. |

Không đưa giá/stock/countdown lịch sử trong research thành thông tin hiện hành. Nếu không cần giá để đáp ứng intent, ưu tiên tránh ghi số dễ hết hạn; nếu cần, ghi đúng option/currency và thời điểm kiểm tra.

Cache tách theo store + API version + product/variant ID. Mặc định đề xuất: kiểm tra lại giá/availability/publication ngay trước publish; fact tương đối ổn định trong cùng run không quá 24 giờ; policy đọc lại trước đợt chạy và khi phát hiện thay đổi. Đây là lựa chọn vận hành cần cấu hình, không phải quy định của Shopify. Proxy hỏng hoặc evidence stale thì không dùng cache để lách gate publish.

## 9. Proxy Settings bắt buộc, không có ngoại lệ ngầm

### 9.1. Mọi đường giao tiếp cần đi qua proxy

| Đường đi | Yêu cầu |
| --- | --- |
| OAuth/token refresh và shop identity | Requests session do ProxyManager cấp. |
| Admin GraphQL/REST đang được giữ lại | Cùng transport bắt buộc; không tạo client trực tiếp riêng. |
| Storefront/product/article/policy URL | GET/HEAD/redirect/retry đều qua proxy. |
| Shopify Files/media/CDN/custom-domain CDN | Kiểm tra và tải bytes/hash/dimensions qua proxy; không nhờ dịch vụ cloud fetch thay. |
| Playwright browser và APIRequestContext nếu có | Truyền proxy đúng context/launch, không context phụ thiếu proxy. |
| Chrome dùng kiểm tra live | Chỉ dùng khi chứng minh traffic Shopify/media trong phiên đó đi qua proxy Settings. Chrome mở được website không chứng minh đã đúng route. |
| Local dashboard hiển thị ảnh Shopify từ xa | Các request ảnh phát sinh từ browser cũng phải đúng route; có thể dùng asset relay đã được kiểm soát, không tạo open proxy. |
| Firecrawl hoặc dịch vụ đọc URL khác | Không được fetch Shopify trực tiếp nếu không hỗ trợ chính xác proxy Settings; dùng local fetch qua proxy rồi phân tích nội dung công khai đã tải. |

Loopback giữa Antigravity và tool local không phải request tới Shopify, có thể truy cập trực tiếp. Không cần ép mọi request Zbigtee qua proxy Shopify, nhưng bất kỳ request Shopify/CDN nào phát sinh từ luồng đó vẫn phải tuân thủ gate.

### 9.2. Hành vi bắt buộc của transport

- Nguồn config duy nhất là Settings/proxy manager; không hardcode host/port/password, không reset từ docs khi chạy campaign.
- Đường campaign/readiness phải phát hiện Settings proxy bị thiếu và fail-closed trước bootstrap. Không để constructor tự seed lại proxy từ `docs/proxy-credentials.md` rồi che mất tình trạng thiếu cấu hình; luồng khởi tạo/cấu hình chủ động trên Settings phải tách riêng.
- Requests session không nhận proxy/direct override từ agent. Kiểm soát env proxy/`NO_PROXY` để không bỏ qua proxy; duy trì `trust_env=False` trên session Shopify.
- Bật TLS verification, không dùng `verify=False` để giải quyết lỗi proxy.
- Proxy check có thời hạn và gắn fingerprint của config. Thay config phải vô hiệu kết quả check cũ và session/browser liên quan.
- Retry, redirect và xử lý token expiration không được tạo request trực tiếp.
- Domain allowlist và redirect validation ngăn gửi credential Admin tới host lạ. Không gửi access token cho CDN/storefront.
- Proxy route lỗi thì trả `PROXY_BLOCKED`; không đổi sang proxy Firecrawl/stealth/system hoặc kết nối trực tiếp.
- Báo cáo ghi thời điểm probe, kết quả route và fingerprint/config reference đã redact. Không lưu password, token hoặc raw credential URL.
- Exit-IP probe chỉ là một bằng chứng. Không hardcode rằng exit IP luôn bằng proxy host; proxy có thể có kiến trúc/egress khác. Chứng minh cả transport binding và request thực tế qua proxy.

### 9.3. Test fail-closed

Test bằng dependency injection/temp config hoặc transport stub: proxy thiếu, authentication lỗi, timeout, thay revision, retry sau 401, redirect và browser context mới. Assert không có lần gọi direct network, không có publish và không có mark Zbigtee published.

Không ghi proxy hỏng vào `data/proxy.json` thật để test. `test_suite.py` cũ cần được tách/sửa trước khi dùng, vì đang reset/ghi Settings thật.

## 10. Xử lý ảnh: chữa thiếu ảnh có kiểm chứng

### 10.1. Quy tắc đầu ra

- **4–7 ảnh thực sự phù hợp trong body**, phân bố ở các mục có liên quan; không tính logo/theme icons/ảnh footer.
- Featured image là yêu cầu riêng. Có thể dùng cùng media với một ảnh body nếu phù hợp, nhưng hero không làm tăng số ảnh body; không cần ép thành 5–8 ảnh độc nhất toàn trang.
- Ảnh phải gắn với sản phẩm live của đúng store đã xác minh API. Không lấy Files bất kỳ chỉ vì trùng tên; Files không liên kết sản phẩm chưa đủ điều kiện ảnh sản phẩm.
- Không dùng SVG, placeholder, ảnh stock ngẫu nhiên, screenshot chữ hay ảnh AI giả làm ảnh sản phẩm để đạt số lượng.
- Ngưỡng chất lượng đề xuất có cấu hình: body ưu tiên tối thiểu khoảng 1.000 px cạnh dài, hero khoảng 1.600 px nếu nguồn có; không upscale rồi coi là ảnh gốc chất lượng cao. Trường hợp không đủ nguồn cần xử lý có lý do, không âm thầm pass.
- Alt/caption mô tả ảnh thực tế, đúng variant/design và đoạn văn; không nhồi từ khóa hoặc gán tính năng không nhìn thấy/không có nguồn.

### 10.2. Thuật toán pipeline

1. Parse tất cả img/figure/placeholder và nhu cầu ảnh từng section; phân biệt URL thật với tên file placeholder từ Zbigtee.
2. Canonicalize URL nhận diện asset: bỏ tham số biến thể hiển thị như width/height/crop khi phù hợp, giữ thông tin phân biệt asset/version cần thiết. Không xóa mọi query string một cách mù quáng.
3. Map ảnh hiện có về API media record của đúng product/variant. Ảnh chỉ đến từ preview chưa đủ được duyệt.
4. Tạo candidate pool từ sản phẩm liên quan search intent và section. Chấm theo product/design/variant/scene/angle; không chỉ theo keyword alt.
5. Tải ảnh candidate qua proxy để kiểm tra content type, decode, dimensions, asset identity; lấy cryptographic hash và perceptual hash khi cần để phát hiện ảnh trùng đổi URL/crop nhẹ.
6. Antigravity xem ảnh thật qua công cụ có khả năng hiển thị ảnh; đối chiếu màu, pattern, shape, phụ kiện, view và nội dung caption. Nếu chưa có khả năng visual review, để pending; không tự gắn visual_verified=true từ filename.
7. Loại bản trùng trong bài, nhất là cặp figure liên tiếp. Trùng alt không tự chứng minh trùng ảnh; khác alt không chứng minh ảnh khác.
8. Với chỗ thiếu ảnh: chọn từ candidate đã đạt identity/visual/context. Nếu không có ảnh cho một claim/diagram chưa tồn tại, viết lại section dựa ảnh/fact có thật hoặc loại section đó; không thay sơ đồ đo bằng một ảnh decor không liên quan.
9. Cập nhật URL/alt/caption/dimensions/responsive markup rồi audit lại toàn bài.
10. Tính lại 4–7 body images sau dedup và kiểm tra hero riêng. Nếu chưa đủ, tiếp tục sửa có giới hạn; không publish khi thiếu.

### 10.3. Dedup và phân bổ

Trong cùng bài: asset ID/source URL đã chuẩn hóa + hash dùng phát hiện trùng. Perceptual similarity là tín hiệu review, không tự xóa hai góc chụp hữu ích của cùng sản phẩm.

Giữa các bài: ưu tiên đa dạng hero và thứ tự ảnh nếu có nguồn, nhưng không cố thay bằng ảnh sai để đạt uniqueness toàn chiến dịch. Bốn góc chụp phù hợp của cùng sản phẩm vẫn có thể dùng trong một bài; không bắt buộc bốn product ID khác nhau.

Ảnh đã CDN transform có thể chuyển domain/resolution. Cho phép phiên bản đã chứng minh cùng asset; không chấp nhận URL bất kỳ chỉ vì nằm trên `cdn.shopify.com`.

### 10.4. Media manifest bắt buộc

Mỗi ảnh ghi `media_id`, `product_id`, optional `variant_id`, store ID, source API field/URL, asset/hash, checked_at, kích thước, vị trí section, caption/alt, lý do chọn và kết quả visual review. Manifest gắn content hash để phát hiện bài đổi ảnh sau audit.

Giữ khả năng giải thích: ảnh nào có sẵn, ảnh nào được bổ sung, ảnh nào bị loại và vì sao. Bỏ cơ chế chọn tuần tự từ `_collect_store_live_fallback_images`/hardcode tên ảnh trong processor khỏi đường campaign mới.

## 11. Kiểm duyệt thông tin và chất lượng nội dung

### 11.1. Những nơi đều phải quét claim

Title, meta description, summary, headings, đoạn văn, bảng so sánh, CTA, FAQ hiển thị, JSON-LD, alt/caption và featured alt. Sửa body nhưng để FAQ schema hứa warranty sai vẫn là thất bại.

### 11.2. Nhóm claim phải có evidence

- Product identity, material/species/composition, size/fit/load, finish/color, set contents và included hardware.
- Personalization/preview/customization, production method, tính năng và intended use.
- Price/currency/discount, stock, shipping regions/fees/time, tax/duty và deadlines.
- Returns/cancellation/refund/warranty, installation/white-glove/support services.
- Safety/certification, waterproof/non-slip/allergy, durability và các absolute claims.
- Sales/reviews/customer numbers, licensing, nguồn gốc và tuyên bố “best/guaranteed”.

### 11.3. Cách sửa khi thiếu hoặc sai thông tin

| Tình huống | Cách xử lý |
| --- | --- |
| Có evidence đúng và đủ scope | Viết lại cho rõ, giữ điều kiện/ngoại lệ và lưu source mapping. |
| Claim phụ không có evidence | Bỏ hoặc diễn đạt thành hướng dẫn kiểm tra, không thay bằng một khẳng định mới. |
| Claim quyết định search intent nhưng thiếu evidence | Chuyển bài về draft/needs_review hoặc đổi angle có căn cứ; chưa publish. |
| Policy conflict | Không đưa con số/cam kết đó vào nội dung; nêu hướng tra policy/support nếu phù hợp. Không tự sửa policy store. |
| Sản phẩm không có/không live/sai store | Loại hoặc chọn sản phẩm live đúng chủ đề; cập nhật cả ảnh, bảng, links và FAQ. |
| Table chứa sản phẩm/variant bịa | Dựng lại từ sản phẩm/variant thật, chỉ so các thuộc tính có nguồn. |
| Câu bị bịa có giá/installation/warranty | Xóa/sửa theo source; không chỉ dùng regex xóa vài từ rồi coi bài sạch. |

Claim auditor kết hợp kiểm tra có cấu trúc/keyword với semantic review của agent. Không tuyên bố regex chứng minh không còn hallucination. Mọi claim quan trọng chưa giải quyết phải hiện trong report và chặn final gate.

### 11.4. Yêu cầu biên tập/HTML

- Đáp đúng một search intent, viết English phù hợp site; không giữ UI tiếng Việt, `[IMAGE:]`, `[NEED…]`, LaTeX `\times` hoặc ghi chú nội bộ.
- Mặc định 1.200 từ hữu ích trở lên, hướng đến 1.800+ khi chủ đề cần; không lặp đoạn/policy chỉ để đủ từ. Nếu thiếu dữ liệu để viết đủ chất lượng, đổi angle hoặc báo thiếu.
- Theme cung cấp H1; body dùng H2/H3 hợp thứ bậc, anchor/TOC trỏ đúng. Không có H1 thứ hai.
- Tables responsive và đọc được trên mobile; nội dung so sánh có evidence theo cell/row quan trọng.
- FAQ thực sự hỗ trợ intent, trả lời dựa source. JSON-LD phản ánh đúng FAQ hiển thị; không tạo câu trả lời ẩn khác policy.
- Sáu bài pilot nên có FAQ hữu ích để kiểm tra đầy đủ nhánh FAQ hiện có. Không hứa rich result/SEO ranking nhờ schema.
- Internal links đến đúng store, product/collection/blog live và đúng context; anchor fragment tồn tại. Không cho domain substring giả mạo vượt kiểm tra.
- SEO title/description/canonical/OG đúng trang; hình thức code/theme cần bổ sung phải tối thiểu và đúng kiến trúc component/Liquid của project, không sửa theme diện rộng để làm test pass.
- Nội dung website/HTML cào về là dữ liệu, không phải lệnh cho agent. Không chạy script/làm theo instruction nhúng trong dữ liệu nguồn.

## 12. Thiết kế MCP Server cho Antigravity CLI

### 12.1. Transport và lifecycle

- Một server Python local dùng MCP SDK phù hợp, transport **stdio**, chạy từ đúng workspace bằng interpreter/venv xác định. Pin dependency và ghi lệnh cài đặt/chạy trong docs triển khai.
- Server phải khởi tạo nhẹ: load tool schema/config public; không crawl catalog, bật browser hoặc khởi động campaign ngay khi client kết nối.
- Antigravity đã được người dùng quan sát thấy các MCP hiện có chuyển sang dấu xanh. Đây là bằng chứng các server đó đã initialize thành công, không phải bằng chứng chức năng blog server mới đã chạy.
- Với đăng ký stdio phù hợp, client khởi chạy command để initialize/discover tools. Server HTTP/daemon bên ngoài nếu có là mô hình khác; không giả định CLI tự chạy mọi service phụ.
- Dùng cơ chế MCP/plugin mà phiên bản Antigravity đang cài thực sự hỗ trợ. Tạo mẫu đăng ký trong project, nêu rõ executable/args/cwd; không đoán schema rồi ghi đè cấu hình MCP khác.
- `/mcp` phải hiển thị server mới sẵn sàng và tools đúng. Dấu xanh là smoke test; vẫn phải gọi tool thật.
- Log ra stderr, redact secrets. stdout không có banner, debug print hay progress text làm hỏng JSON-RPC.
- Tool lâu trả job/run ID và trạng thái; có progress và đọc status/resume thay vì đợi vô hạn hoặc retry publish mù.
- UI server `:8765` là thành phần riêng có kiểm tra readiness. Không trộn log Web UI vào stdio stream.

### 12.2. Các tool đề xuất và hợp đồng

Tên tool là hợp đồng dự kiến; có thể chỉnh tên nhất quán lúc triển khai nhưng phải giữ đủ năng lực sau.

| Tool | Input chính | Output/hành vi |
| --- | --- | --- |
| `list_stores` | Không cần secrets. | Store ID/name/domain, profile status, public readiness; không dump config. |
| `get_store_profile` | `store_id`, optional revision. | Runtime instructions, structured rules, sources/unknowns; không token/proxy password. |
| `validate_store_profile` | `store_id`, profile draft/revision. | Schema + semantic findings; không tự activate trường conflict. |
| `save_store_profile` | `store_id`, expected revision, allowed fields. | Lưu profile biên soạn của đúng store; reject stale revision/credential fields. |
| `check_store_readiness` | `store_id`. | Proxy, identity, auth/scopes, profile, blog, Zbigtee readiness; có checked_at. |
| `list_plan_candidates` | `store_id`, filters, pagination. | Proposal create/improve đầy đủ, evidence và lý do eligible/excluded. |
| `prepare_campaign` | Explicit store IDs, campaign ID, mode/limits. | Baseline + manifest; planning không tự accept/write/publish. |
| `add_plan_topics` | `store_id`, reviewed topic records. | Kiểm tra trùng và tạo Plan items bằng đường đã xác minh; không tự nhận là đã có chỉ từ file local. |
| `prepare_article_brief` | Store, plan item, campaign/run. | Profile revision, intent, facts/products/media candidates, claim exclusions và outline. |
| `generate_or_fetch_draft` | Store, plan/content ID, brief revision. | Trigger hoặc lấy draft Zbigtee theo capability thực tế, lưu source payload và trạng thái. |
| `query_store_catalog_assets` | Store, query/collection/product IDs/variant IDs. | API-backed facts, publication/media association và unknowns. |
| `sanitize_article_claims` | Store, run/draft revision. | Claim findings, proposed edits, evidence map; không tự tuyên bố sửa xong nếu unresolved. |
| `heal_article_images` | Store, run/draft revision, section needs. | Revised media placement + candidates/manifest; thiếu visual review thì pending. |
| `validate_article` | Store, run/content hash. | Bộ prepublish gates, ready token/digest và blocking findings. |
| `publish_and_verify_article` | Store, run ID, approved digest, create-only mode/idempotency key. | Publish đúng destination, verify, sync Zbigtee theo state; trả truthful terminal hoặc job ID. |
| `get_run_status` | Store, run/job ID. | State, progress, findings, artifact paths; không re-run mutation. |
| `resume_run` | Store, run ID. | Reconcile trạng thái ngoài rồi tiếp tục bước thiếu, không tạo bản trùng. |
| `run_acceptance_pilot` | Campaign ID và cohort cố định 3+3. | Chạy đúng 6 bài, qua services/MCP thực tế, tạo báo cáo nghiệm thu tổng hợp. |

Không buộc agent gửi toàn bộ HTML/research/ảnh base64 qua MCP mỗi bước. Dùng artifact ID/path trong workspace được validate; ngăn path traversal/đường dẫn sang store khác. Tool có filesystem input chỉ đọc file thuộc run/workspace cho phép.

### 12.3. Envelope trả về

Mỗi kết quả cần có `ok`, `store_id`, `campaign_id/run_id` khi phù hợp, `state`, `stage`, `summary`, `findings`, `artifact_paths`, `checked_at` và `next_actions` cụ thể. `ok` toàn workflow chỉ true khi đủ mọi bước bắt buộc; job accepted/running không có nghĩa đã đạt.

Các mã lỗi ổn định đề xuất: `INVALID_STORE`, `STORE_IDENTITY_MISMATCH`, `PROFILE_INVALID`, `PROXY_BLOCKED`, `AUTH_REQUIRED`, `SCOPE_MISSING`, `PLAN_NOT_CREATE`, `BASELINE_DUPLICATE`, `CATALOG_NO_MATCH`, `PRODUCT_NOT_LIVE`, `FACT_UNSUPPORTED`, `POLICY_CONFLICT`, `MEDIA_UNVERIFIED`, `INSUFFICIENT_IMAGES`, `CONTENT_TOO_SHORT`, `BLOG_NOT_FOUND`, `STALE_VALIDATION`, `PUBLISH_FAILED`, `PUBLISH_OUTCOME_UNKNOWN`, `LIVE_VERIFY_FAILED`, `ZBIGTEE_SYNC_PENDING`.

Mỗi lỗi chỉ rõ có retry được không và phải sửa gì. Exception quan trọng không bị `except: pass` rồi trả `ok=true`.

### 12.4. Write boundaries

- Read-only tools không accept Plan, đổi status Zbigtee, tạo blog hay publish.
- Agent phải gọi đúng tool ghi để tạo Plan item, trigger writer, save profile và publish; có audit của action đó.
- Tool publish campaign không expose delete article, move blog hoặc update arbitrary existing article.
- Comprehensive editor và legacy CLI vẫn cần common gate để không trở thành đường bypass. Nếu giữ mode sửa bài cũ, phải tách rõ khỏi `create_only` và không tính vào mục tiêu mới.

## 13. Bổ sung 6 chủ đề cho Preaureum

Sáu mục dưới đây là ứng viên đã có cơ sở từ research. Chưa được thêm vào Zbigtee, chưa xác minh đủ product/media và chưa chắc khác toàn bộ 14 đề xuất hiện có. Antigravity cần lấy Plan live + existing articles để khử trùng trước khi chốt.

| # | Title/intent ứng viên bằng tiếng Anh | Căn cứ catalog/policy | Điều phải tránh/xác minh |
| --- | --- | --- | --- |
| 1 | **How to Choose a Personalized Handbag Gift for a Book Lover** | `/collections/book-lover` | Chọn sản phẩm live, size/options thật; không tạo quyền lợi gift packaging chưa có nguồn. |
| 2 | **Photo and Text Personalization for Handbags: Preparing a Clear Design** | `/collections/custom-photo-text` | Xác minh product hỗ trợ upload/text và constraint thực tế; không bịa DPI, dung lượng hay automatic preview. |
| 3 | **Nurse-Themed Handbag Gifts: Choosing a Meaningful Everyday Design** | `/collections/nurse` | Không suy ra túi chịu khử khuẩn, dùng y tế hoặc fit thiết bị nghề nghiệp chưa kiểm chứng. |
| 4 | **How to Style a Butterfly-Themed Handbag for Everyday Outfits** | `/collections/butterfly` | Mô tả pattern/color đúng ảnh; không gọi in 3D là nổi/embossed. |
| 5 | **Black Cat or Highland Cow Handbag: Choosing Artwork That Fits Your Style** | `/collections/black-cat`, `/collections/highland-low-leather-handbags` | So sánh design của product thật; không gán chất liệu/cấu trúc khác nhau chỉ vì artwork. |
| 6 | **How to Care for a Printed Leather-Style Handbag** | FAQ/care Preaureum | Không khẳng định genuine leather/PU/waterproof hoặc đưa chất tẩy/routine không được hỗ trợ. |

### 13.1. Quy trình chốt chủ đề

1. Đọc 14 create hiện có và tất cả bài/preview lịch sử, so semantic intent chứ không chỉ title/slug.
2. Với từng chủ đề: xác minh collection URL, sản phẩm thật, khả năng viết đủ nội dung có ích và 4–7 media phù hợp.
3. Tạo brief gồm primary intent, outline, product IDs, source refs, differentiator so với nội dung đã có và các claim cấm.
4. Nếu trùng hoặc không đủ evidence/media, đổi ứng viên theo catalog đã xác minh; vẫn cần 6 chủ đề create độc lập, không thêm six variations của cùng intent.
5. Thêm vào Zbigtee bằng UI hoặc API đã kiểm tra thực tế, `action=create`, không target trang cũ. Lưu returned plan ID và đọc lại xác nhận.
6. Không đoán rằng tRPC `plan.accept` tự sinh một bài hoàn chỉnh; kiểm tra capability, trạng thái writer, thời gian chờ và payload thực tế.
7. Ghi rõ sáu topic nào đã thêm, topic nào thay thế và lý do; không chỉ sửa con số local từ 14 thành 20.

## 14. Workflow triển khai cho một bài viết mới

### 14.1. State machine

`DISCOVERED → ELIGIBLE → RESERVED → BRIEF_READY → DRAFT_READY → FACTS_REVIEWED → MEDIA_REVIEWED → PREPUBLISH_READY → SHOPIFY_CREATED → LIVE_VERIFIED → ZBIGTEE_SYNCED → COMPLETED`

Các nhánh lỗi độc lập cần có: `BLOCKED_PROFILE`, `BLOCKED_PROXY`, `BLOCKED_FACTS`, `BLOCKED_MEDIA`, `PUBLISH_OUTCOME_UNKNOWN`, `LIVE_FAILED`, `ZBIGTEE_SYNC_PENDING`. Có thể dùng model trạng thái khác tương đương, nhưng phải phân biệt **đã public trên Shopify** với **đã nghiệm thu hoàn tất**.

### 14.2. Trình tự bắt buộc

1. Kiểm tra đúng workspace, store ID, proxy readiness, shop identity, API/scopes, profile revision và destination blog.
2. Đọc Plan/Kanban live; giữ snapshot nguồn và timestamp. Filter `create + targetPath=null`, khử trùng với baseline và chiến dịch hiện tại.
3. Reserve item trong manifest bằng idempotency key và lock. Chưa reserve được thì không trigger writer song song.
4. Lập brief từ profile đã biên soạn, intent, product/variant/media evidence và các claim không được dùng.
5. Accept/trigger writer theo luồng Zbigtee đã kiểm chứng. Nếu đang writing thì poll có backoff, báo progress; không accept lại một proposal mỗi lần poll.
6. Lấy preview payload mới; ghi lại content ID, Plan ID, source URL, timestamps và raw content hash.
7. Normalize HTML trước, chưa chặn luôn vì thiếu ảnh có thể chữa được. Tách lỗi cấu trúc không thể xử lý khỏi missing-image findings có thể sửa.
8. Audit claim toàn bài; Antigravity chỉnh nội dung theo evidence, không tự khẳng định code regex đã duyệt semantic.
9. Dùng image service bổ sung/thay/xóa ảnh đúng context; xem ảnh thực tế, lưu media manifest và kết quả review.
10. Rebuild summary/meta/FAQ schema/alt sau khi sửa body, đảm bảo không còn claim cũ ở các vùng khác.
11. Render local preview bằng tool và kiểm tra chất lượng, heading/table/image placement; mọi remote media request vẫn qua proxy.
12. Chạy final gate trên revision đã ổn định: profile, create-only/dedup, facts, media, 4–7 body images, word count, metadata, link và proxy.
13. Recheck dữ liệu dễ biến động và existing article identity trước mutation. Publish đúng store/blog; lưu article ID/URL ngay khi nhận được, trước bước verify/Zbigtee.
14. Read back qua API để kiểm tra article ID, body/metadata, visibility và URL đúng revision đã publish.
15. Kiểm tra live Desktop/Mobile qua tool; có screenshots, request/DOM findings và kết quả thị giác. Lỗi thì sửa **đúng article đã tạo trong run**, audit lại và verify lại.
16. Chỉ sau live verified mới mark Zbigtee published; đọc lại trạng thái/mapping để xác nhận. Nếu sync lỗi, giữ `ZBIGTEE_SYNC_PENDING`, không tạo Shopify article mới để retry.
17. Đóng run khi đầy đủ bằng chứng; increment campaign counter đúng một lần cho một article ID mới hợp lệ.

### 14.3. Quy tắc sửa bài trong đợt create-only

Create-only ngăn cập nhật bài đã tồn tại trước baseline, không ngăn fix bài vừa được chính run này tạo. Retry/fix phải dùng article ID đã lưu, đối chiếu ownership và campaign mapping; không chỉ tìm một handle rồi update bất cứ bài nào trùng.

Nếu handle đụng bài cũ: báo collision hoặc chọn handle mới sau khử trùng intent; không tự overwrite. Nếu publication outcome không rõ do timeout: query/reconcile trước khi retry. Không dùng delete-and-create hay move-blog để xử lý collision.

### 14.4. Nguồn content và bước viết

Zbigtee vẫn là nơi quản lý Plan và draft. Công cụ local là nơi kiểm chứng, chuẩn hóa và publish. Nếu cần sửa lại nội dung sau draft, lưu bản cuối và mapping source để lần fetch sau không âm thầm ghi đè phiên bản đã duyệt.

Không giả định backend Zbigtee có endpoint writer/plan với schema như handoff. Có thể dùng Chrome/Playwright để tìm flow thực tế và public API contract từ traffic được phép; giữ nguyên blocklist với nút hủy/xóa/trả Plan/request changes ngoài nhiệm vụ. Tác vụ đọc Plan không tự thay đổi trạng thái. Thao tác tạo topic/accept/write/publish chỉ diễn ra trong bước thực thi tương ứng.

## 15. Thứ tự triển khai và đầu ra từng mốc

### Mốc A — Baseline và bảo vệ dữ liệu

- Đọc tài liệu này, handoff, research và code trong workspace.
- Inventory entrypoints, dependencies và mọi điểm gọi Shopify/API/media/browser; chỉ rõ đường nào có proxy, đường nào còn rủi ro bypass.
- Lưu baseline campaign và snapshot cấu hình được bảo vệ; backup credentials/proxy chỉ ở vị trí local có bảo vệ, không đưa vào report/git.
- Kiểm tra các file output lịch sử và current articles/Plan; đánh dấu protected existing article IDs.
- Không chạy nguyên `test_suite.py` trước khi xử lý test đang sửa Settings thật.

**Đầu ra:** baseline manifest, sơ đồ transport/entrypoint, danh sách issue cần sửa; chưa có article mutation.

### Mốc B — Shared transport, catalog evidence và profile

- Hoàn thiện shared proxy-backed client, error model, scope/identity/publication checks và pagination.
- Xây schema/manager và section Settings riêng từng store.
- Biên soạn 5 profile từ research theo mục 6–7; thể hiện unknowns/conflicts rõ, recheck policy khi activate.
- Dựng runtime profile public cho Antigravity; không gửi full research/credentials.

**Đầu ra:** 5 profile đọc lại đúng store; catalog evidence endpoint; tests isolation cho proxy, credentials và profile revision.

### Mốc C — Fact/image services và common gate

- Tách processor thành các bước để missing images có thể chữa trước final validation.
- Bỏ hardcode filename/fallback ngẫu nhiên; triển khai association API + visual review + image manifest/dedup.
- Claim audit toàn bộ bề mặt nội dung; không giữ unsupported policy claims.
- Dùng chung gate cho UI/CLI/MCP, sửa false-success paths và no-verify bypass trong campaign.
- Sửa publisher blog resolution, create-only/idempotency/pagination và retry reconcile.
- Nâng live verifier theo mục 17, đặc biệt kiểm tra layout trước các DOM modifications có thể che lỗi.

**Đầu ra:** một draft chưa đạt phải bị chặn có lý do; một draft đạt sinh report evidence đầy đủ, chưa cần chạy 100 bài.

### Mốc D — MCP và campaign orchestration

- Tạo entrypoint stdio, tool schemas, job/status/resume và logging không phá protocol.
- Kết nối với các services thực; không dùng tool wrapper chỉ trả mock thành công.
- Chuẩn bị mẫu đăng ký MCP theo Antigravity phiên bản đang dùng; giữ các server/plugin sẵn có.
- Xác minh initialize, tool discovery rồi gọi readiness/profile/catalog qua Antigravity thực tế.
- Triển khai Plan selection, writer/fetch flow thực tế và 6 chủ đề Preaureum sau dedup.

**Đầu ra:** Antigravity dùng được MCP mới, đủ dữ liệu để vận hành và có state/manifest thật.

### Mốc E — Chạy tool và nghiệm thu 6 bài

- Khởi chạy Web UI/pipeline/MCP thật theo mục 16.
- Chốt cohort đúng 3 create mới đầu tiên/store cho Preaureum và WRYDECO.
- Chạy đủ workflow cho từng bài, fix khi cần trên đúng ID, lưu mọi evidence.
- Chạy kiểm tra create-only, cross-store isolation, retry/idempotency và proxy fail-closed bằng cơ chế không sửa Settings thật.
- Tổng hợp báo cáo đạt/chưa đạt; không nhân scope test thành 20 bài/store.

**Đầu ra:** 6 bài mới live có báo cáo, hoặc danh sách bài chưa đạt với lý do và trạng thái ngoài hệ thống trung thực. Chỉ tuyên bố nghiệm thu đạt khi đủ 6.

## 16. Kịch bản nghiệm thu thực tế: 3 Preaureum + 3 WRYDECO

### 16.1. Số lượng và lựa chọn cohort

| Store | Bài mới phải chạy | Existing/improve được tính | Article E2E test cho 3 store còn lại |
| --- | ---: | ---: | ---: |
| Preaureum | 3 | 0 | Không áp dụng |
| WRYDECO | 3 | 0 | Không áp dụng |
| DizzyCustom/Jeminise/Chillgen | 0 trong đợt nghiệm thu | 0 | 0 |
| **Tổng** | **6** | **0** | **0** |

“Đầu tiên” nghĩa là ba item create đủ điều kiện đầu tiên của từng store trong queue triển khai đã chốt, theo thứ tự ưu tiên ổn định và có lưu sort/selection rule. Đọc dữ liệu live, filter invalid/improve/baseline duplicate trước, rồi đóng băng cohort bằng Plan ID và content ID khi có.

Không dùng lại 4 bài Preaureum/5 bài WRYDECO lịch sử trong output làm sáu bài mới. Không hardcode content IDs từ ví dụ CLI cũ. Ba bài Preaureum có thể đến từ create hiện có hoặc topic mới thêm, miễn là đúng thứ tự queue, không trùng và được ghi rõ.

Nếu đã chọn/chạy một bài rồi gặp lỗi thì bài đó vẫn là ca nghiệm thu cần sửa; không bỏ khỏi báo cáo để chọn bài dễ hơn và giấu thất bại. Trường hợp phát hiện đầu vào vốn không đủ điều kiện phải ghi lý do thay thế và cập nhật manifest minh bạch trước khi tiếp tục.

### 16.2. Bắt buộc khởi chạy công cụ

**Không được nghiệm thu chỉ bằng đọc code, mock report, unit test, script curl rời rạc hay mở một bài cũ bằng Chrome.**

Trình tự đề xuất khi thực thi:

1. Kiểm tra port và tiến trình tool đã có; reuse instance đúng workspace/version nếu phù hợp. Không kill tiến trình lạ để chiếm port.
2. Nếu cần start Web UI, từ workspace chạy entrypoint hiện có bên dưới bằng môi trường Python đã cài dependency.
3. Start MCP stdio thông qua Antigravity registration; `/mcp` thấy server sẵn sàng, gọi read-only tools thật trước.
4. Mở dashboard và Settings, kiểm tra section profile của cả 5 store hiển thị/lưu tách biệt. Thử nghiệm cross-store draft/edit bằng fixtures, không sửa credentials.
5. Từ Antigravity gọi pipeline/MCP đã triển khai để chạy cohort 6 bài, quan sát progress trên tool và báo cáo.
6. Kiểm tra article live qua verifier thực và review screenshot. Chrome có thể bổ sung kiểm tra nhìn thấy trên browser nếu đã bảo đảm route proxy.

Lệnh Web UI dưới đây **đã có trong CLI hiện tại**, chỉ chạy trong giai đoạn triển khai/test, không chạy khi đọc plan:

```powershell
python cli.py serve --host 127.0.0.1 --port 8765 --no-browser --raw-server
```

`--raw-server` tránh đi qua wrapper có hành vi quản lý/kill port owner. Nếu port đang dùng, xác minh instance hoặc chọn port trống và ghi vào report; không đổi cấu hình hệ thống chỉ để test.

Lệnh kiểm tra live hiện có, thay bằng URL/handle **thực của bài vừa tạo**, không dùng URL ví dụ cũ:

```powershell
python cli.py verify --store preaureum --url "ACTUAL_NEW_ARTICLE_URL" --handle "ACTUAL_HANDLE"
python cli.py verify --store wrydeco --url "ACTUAL_NEW_ARTICLE_URL" --handle "ACTUAL_HANDLE"
```

Hai lệnh verify là bước kiểm tra bổ sung hoặc chạy lại verifier, không thay thế việc chứng minh bài đã được xử lý/publish qua tool mới.

Entry point MCP `python mcp_server.py` và acceptance runner là **cần triển khai**, chưa được giả định tồn tại. Khi hoàn thành, Antigravity ghi lại lệnh registration/chạy chính xác theo code thực tế. Hợp đồng của pilot tool phải khóa store IDs `preaureum,wrydeco`, `new_articles_per_store=3`, create-only và live verification bắt buộc; không mặc định mở rộng toàn chiến dịch.

### 16.3. Lưu bằng chứng cho từng bài

- Campaign/run ID, store, thứ tự 1/2/3, Plan ID, content ID, action/targetPath và lý do đủ điều kiện mới.
- Profile revision, shop/domain/blog identity và baseline comparison.
- Brief/raw preview/final HTML, content hashes và các thay đổi sửa claim.
- Product/variant/publication evidence, fact report và media manifest có visual review.
- Số từ, số body images sau dedup, featured image và kết quả prepublish gate.
- Shopify article ID, create timestamp, operation outcome, readback và public URL.
- Proxy readiness/transport evidence đã redact; không chỉ ghi một chuỗi “proxy used”.
- Live report, screenshots Desktop/Mobile và nhận xét visual review thật.
- Zbigtee status/mapping đọc lại sau sync; nếu chưa sync phải ghi pending.
- Lịch sử retry/fix, các lỗi đã gặp và tình trạng cuối, kể cả khi lần chạy cuối pass.

Lưu screenshot local UI tránh vùng credentials; redact nếu cần. Không lưu session cookies, token, proxy password hoặc full auth headers trong trace/HAR/report.

### 16.4. Chạy lại không tạo trùng

Chọn ít nhất một trong sáu run đã hoàn tất, gọi lại bằng cùng campaign/content/idempotency key. Kết quả phải trả mapping bài đã có hoặc resume bước cần thiết; không tạo article ID thứ hai, không increment counter lần hai và không chọn blog khác.

Mô phỏng các tình huống lỗi ở transport/state bằng isolated tests: unknown outcome sau mutation, verify failure sau create, Zbigtee sync failure và profile đổi sau validate. Không cần cố tình làm hỏng 6 bài public để tạo lỗi. Ca retry live chỉ dùng lại article/run đã tạo, không xuất bản bài thứ bảy chỉ để test.

## 17. Bộ tiêu chí nghiệm thu

### 17.1. 12 checks hiện có phải được chạy thật và hiểu đúng

| Check ID hiện có | Hiện kiểm tra | Yêu cầu áp dụng cho 6 bài |
| --- | --- | --- |
| `http_status_ok` | HTTP 200, không ở password URL. | Đúng article live, không soft 404/password HTML/redirect sai store. |
| `single_h1_matches_title` | Một H1 khớp title. | Một H1 do theme, đúng bài và đúng title cuối. |
| `hero_featured_image_loaded` | Hero load được. | Load được và đúng approved media/product; không chỉ lấy ảnh đầu để pass. |
| `excerpt_dek_visible` | Có đoạn excerpt/fallback đủ dài. | Summary/dek phù hợp và thực sự hiển thị; metadata ẩn không được giả làm excerpt visible. |
| `all_body_images_loaded` | Hiện chỉ cần ít nhất 1 img, không broken. | Tăng kiểm tra đúng **4–7 body images** đã duyệt, load/decode được. |
| `no_svg_fallback_rendered` | Không thấy SVG selector đang dùng. | Không SVG placeholder/diagram trong body; kiểm tra đầy đủ body, không chỉ `svg[role=img]`. |
| `tables_responsive` | Table có wrapper. | Có wrapper nếu cần và thực sự không làm tràn trang/che nội dung. |
| `faq_section_english` | FAQ English hoặc không có. | Với pilot có FAQ: heading/content đúng ngôn ngữ, có ích và có nguồn. |
| `faq_json_ld_valid` | Parse được FAQPage top-level. | FAQ schema hợp lệ, không mâu thuẫn FAQ visible; hỗ trợ cấu trúc JSON-LD thực tế khi cần. |
| `no_vietnamese_leftovers` | Không có một số marker. | Không còn marker/placeholder/note nội bộ/LaTeX; không chỉ đúng vài chuỗi được hardcode. |
| `internal_links_valid` | Hiện chủ yếu xem prefix/domain substring. | Parse URL thật, đúng host/target live, anchor đúng, không redirect sang store khác. |
| `mobile_layout_clean` | Không horizontal overflow trên 390×844. | Không overflow toàn trang; ảnh/table/text/CTA đọc được trên mobile thực tế. |

Không đổi check thành pass chỉ vì xóa tính năng khỏi bài. Các trường hợp không áp dụng phải được report đúng `not_applicable` và giải thích; với 6 bài pilot thiết kế có FAQ nên kiểm tra FAQ thực sự được thực hiện. Không làm giả `12/12` bằng cách bỏ checks thất bại.

### 17.2. Gate bổ sung bắt buộc cho cả 6 bài

1. **Mới và đúng store:** action=create, targetPath=null, không baseline duplicate; article ID mới sau baseline và đúng project/domain/blog.
2. **Profile:** dùng đúng revision profile riêng store, viết đúng phạm vi/giọng và các forbidden claims.
3. **API facts:** các sản phẩm/variant được mô tả có API evidence và live publication; bảng/FAQ/metadata không có claim unsupported quan trọng.
4. **Media:** 4–7 ảnh body sau dedup, có hero, API association + review thị giác; không sai design, màu, option hay set contents.
5. **Policy:** đúng scope/ngoại lệ; không warranty/delivery/return/installation bịa. Unknown/conflict không bị biến thành cam kết.
6. **Nội dung:** đạt ngưỡng từ hữu ích, đúng intent, không sao chép bài cũ/nhồi policy để đạt số.
7. **SEO metadata:** title và meta description đúng revision; canonical đúng URL chính thức sạch query test/tracking; Open Graph title/description/URL/image hợp lệ và khớp bài/hero.
8. **Links/HTTP:** product/collection/internal links đúng destination, không broken/soft 404; có kiểm tra các URL thật được bài dùng.
9. **Desktop & Mobile:** Desktop 1440×900 và Mobile 390×844 có screenshots; ảnh/table/TOC/readability không bị che hoặc tràn; không chỉ kiểm tra scrollWidth.
10. **API readback/freshness:** body/meta/visibility đọc lại đúng bản cuối; live page chứa nội dung mới tương ứng. Cache-buster đơn lẻ không chứng minh freshness.
11. **Proxy:** mọi Shopify request trong API/media/browser/retry đi qua Settings proxy; isolated failure tests chứng minh không fallback direct.
12. **Đồng bộ và idempotency:** Zbigtee published sau verify, mapping đúng; rerun không tạo thêm article hay đếm thêm.

Handoff mô tả canonical/Open Graph như đã nằm trong 12 checks, nhưng code hiện không kiểm tra chúng. Phải bổ sung thật vào verifier/report; không chỉ đổi mô tả check cũ.

### 17.3. Sửa các điểm có thể gây false pass trong live verifier

- Đo layout trước khi script test sửa `height`, `max-height`, `overflow` trên html/body/main. Không cưỡng ép CSS hết overflow rồi dùng kết quả đó chứng minh trang không lỗi.
- Có thể đóng popup phù hợp để chụp ảnh, nhưng không ẩn thành phần đang gây lỗi thật; ghi hành động đã thực hiện.
- Trigger lazy-load bằng scroll, chờ decode có timeout. Với mobile, dùng context/viewport thích hợp rồi kiểm tra lại responsive sources và ảnh tải thực tế, không chỉ resize sau khi desktop đã tải xong.
- Dùng selector giới hạn đúng article body; logo/nav/footer không làm tăng image/word count và không trở thành hero fallback.
- Validate FAQ visible với JSON-LD, không chỉ JSON.parse thành công. Không tự bịa FAQ để thỏa schema.
- HTTP/header/canonical/OG checks có expected values rõ; lưu findings đủ xem lại, không chỉ boolean.
- `verification_report.ok=false` phải làm workflow/acceptance fail, kể cả Shopify create đã thành công.

### 17.4. Ma trận test kỹ thuật có ý nghĩa

| Nhóm | Ca cần chứng minh | Dữ liệu/phạm vi |
| --- | --- | --- |
| Profile | Lưu A không đổi B; revision conflict; không nhận credential fields; unknown policy không auto-fill. | Fixtures cho 5 store, UI smoke và schema. |
| Proxy | Thiếu/sai auth/timeout/retry/redirect/browser phụ không có direct call. | Temp config, injected client/route recording; không sửa Settings thật. |
| Product gate | Sai store, active nhưng chưa publish, draft/archived, thiếu scope, variant không khớp, sold out bị mô tả in-stock. | API fixtures + live evidence trên 6 bài. |
| Media | Cùng ảnh khác width/query, alt sai, Files không gắn product, ảnh sai variant, 3/8 ảnh, hero broken. | Asset fixtures + API/visual manifests của 6 bài. |
| Facts | Warranty/installation/return/price bịa; claim nằm trong FAQ/schema/caption; policy conflict. | Fixtures từ lỗi đã quan sát, không mirror implementation. |
| Publish | Blog không tồn tại, handle trùng protected article, timeout outcome unknown, retry cùng ID. | Mock transport cho failure, live rerun của một bài đã tạo. |
| Workflow | Verify fail không mark published; sync fail giữ pending; đổi body/profile sau audit làm ready digest stale. | State tests + 6 run thực. |
| UI/MCP | Server initialize/discover, tool call thật, Settings profile đúng store, lỗi đúng schema, stdout sạch. | Antigravity + local Web UI thực tế. |
| Live | 12 checks được nâng và extended gates. | Chỉ 3 bài mới Preaureum + 3 bài mới WRYDECO. |

Chạy regression phù hợp sau khi sửa code; không cần lặp kiểm tra rộng khi code không đổi và các checks đã đạt. Không thêm test hình thức chỉ để đạt số lượng. Không dùng test suite hiện tại có side effect như bước mặc định trước khi tách isolation.

## 18. Logging, resume và xử lý thất bại

### 18.1. Mỗi action phải truy vết được

- Correlation gồm campaign, store, run, Plan/content ID, article ID khi đã tạo và profile/content revision.
- Mỗi step có started_at, finished_at, outcome, error code, retry count và artifact reference.
- Không log auth headers, cookies, access/refresh token, client secret, proxy password hoặc credential URLs. Sanitize cả exception từ thư viện HTTP.
- Artifact paths phải thuộc workspace và được phân quyền/loại khỏi version control nếu chứa dữ liệu vận hành nhạy cảm.

### 18.2. Partial success không được báo thành complete

| Trạng thái thực tế | Phải làm |
| --- | --- |
| Proxy hỏng trước API/publish | Dừng, giữ draft; báo `PROXY_BLOCKED`. |
| Shopify mutation timeout, không rõ kết quả | Reconcile theo manifest/identity trước retry. |
| Shopify đã public nhưng live verify fail | Lưu URL/ID, báo `LIVE_FAILED`, sửa đúng bài của run, chưa mark Zbigtee published. |
| Live đã đạt, Zbigtee sync lỗi | Giữ `ZBIGTEE_SYNC_PENDING`; retry sync/readback, không publish thêm. |
| Worker/client đóng giữa chừng | Resume từ journal sau xác minh external state; không dựa mỗi state local. |
| Profile/policy/catalog đổi làm evidence hết hạn | Invalidate ready state, audit phần ảnh hưởng và kiểm tra lại trước publish. |

Không tự xóa bài public hoặc hạ trạng thái của bài cũ để làm sạch kết quả. Nếu cần rollback bài vừa tạo, ghi rõ ID thuộc run và hành động phục hồi; ưu tiên sửa đúng bài. Các thao tác ảnh hưởng bài ngoài campaign không nằm trong task này.

Giới hạn fix loop mặc định đề xuất 3 lần cho một lỗi, có thể tiếp tục khi có thay đổi/bằng chứng mới; hết giới hạn thì giữ lỗi cụ thể và artifact cho xử lý, không bỏ gate. Một bài không đủ ảnh/thông tin không được pass bằng cách hạ threshold.

## 19. Bộ artifact bàn giao sau khi triển khai

1. Source code MCP/services đã tích hợp, dependencies pin và hướng dẫn chạy/đăng ký Antigravity chính xác.
2. Schema + 5 profile đã **biên soạn** riêng store; revision, source refs, unknowns và conflicts.
3. Runbook giải thích credentials/proxy server-side, tools nào ghi dữ liệu, cách xem status/resume và lỗi thường gặp.
4. Baseline campaign, danh sách create eligible/excluded, mapping protected articles và sáu topic Preaureum đã dedup/thêm thật hoặc danh sách thay thế có lý do.
5. Acceptance cohort 6 bài có thứ tự, IDs/URLs thật, state cuối và các artifact ở mục 16.3.
6. Test reports cho logic chung và báo cáo chạy tool thật; không chỉ console “success”.
7. Bảng tiến độ phân biệt mục tiêu 20/store với số bài thực sự hoàn tất trong đợt test; không tự nâng counter các store chưa chạy.
8. Danh sách thiếu quyền/thông tin/policy conflict còn lại và ảnh hưởng cụ thể, không giấu trong generic warning.

### 19.1. Báo cáo nghiệm thu tổng hợp

Tạo `output/acceptance/<acceptance_run_id>/acceptance_report.md` và bản JSON máy đọc được, gồm:

| Trường | Nội dung bắt buộc |
| --- | --- |
| Environment | Workspace, code revision nếu có, Python/MCP/Antigravity versions thực tế, tool URL/port và thời gian chạy. |
| Execution evidence | Lệnh start tool, MCP initialize/tool calls/run IDs, UI screenshots đã redact. |
| Cohort | Chính xác 6 hàng: Preaureum #1–#3, WRYDECO #1–#3. |
| Newness | Baseline exclusion, create evidence, Plan/content/article IDs, không update bài có sẵn. |
| Quality | Word/image counts, fact/media/profile/proxy gates, 12 core + extended checks và visual review. |
| Publication | Actual URL, API readback, live status và Zbigtee readback. |
| Recovery | Retry/fix history, rerun idempotency result, pending/error nếu còn. |
| Verdict | PASS chỉ khi cả 6 bài hoàn tất mọi điều kiện; nếu chưa đủ ghi FAIL/PARTIAL cùng nguyên nhân. |

Không điền bảng bằng dữ liệu giả định từ plan. Lúc chưa chạy thì ghi “chưa chạy”, không tick pass.

## 21. Đặc Tả Kiến Trúc & Cải Tiến Kỹ Thuật Chuẩn Hóa Đã Chốt (Post-Audit Hardening Specification)

Sau quá trình kiểm toán độc lập bằng ChatGPT (với điểm số tăng mạnh từ 61/100 lên ~91/100) và triển khai thực tế trên catalog WRYDECO, các cải tiến kỹ thuật sau đã được đóng băng và áp dụng làm chuẩn mực vận hành bắt buộc:

### 21.1. Chuẩn Hóa Khâu Lập Brief (`prepare_article_brief`)
1. **Trích xuất từ khóa trước khi truy vấn:** Tuyệt đối không gọi `search_products` khi query rỗng. Phải bóc tách `clean_kw` từ `raw_topic_title` bằng regex trước khi truy vấn catalog.
2. **Định tuyến Collection thông minh (Smart Collection Mapping):** Tự động mapping từ khóa sang handle collection chuẩn (`wine` + `wall` -> `wall-mounted-wine-rack`, `tree` + `shelf` -> `tree-bookshelves`, `fluted` -> `floating-shelves`...).
3. **Guardrail Giới hạn 30 phần tử ZBigTee (30-Item Cap Guard):** ZBigTee API giới hạn mảng `verified_facts` tối đa 30 phần tử. Bắt buộc đặt **100% sản phẩm catalog thật có đầy đủ handle, giá, kích thước, ảnh lên vị trí 0..4** (đầu danh sách) để đảm bảo AI Writer luôn nhận đủ dữ liệu spec thực tế cho Decision Table.
4. **Nghiêm cấm Fallback mù:** Nếu tìm kiếm không có kết quả, chỉ fallback trong cùng Collection đã mapping; tuyệt đối không fallback sang sản phẩm ngẫu nhiên ở đầu store (như gương, tranh) khi bài viết nói về kệ/bàn ghế.
5. **Đồng bộ Artifact & Metadata:** Chuẩn hóa quy ước lưu file preview về `input/{store_id}/{content_id}_preview.json`; metadata run record phải cập nhật đầy đủ `handle`, `shopify_url`, `public_url` và tự động xóa `last_error_code` khi retry thành công.

### 21.2. Chuẩn Hóa Khâu Chữa Lành Ảnh (`article_image_service.py`)
1. **Bộ lọc Stopword thương mại & biên tập:** Bổ sung các từ `buying`, `guide`, `tips`, `ideas`, `review`, `reviews`, `best`, `fit`, `capacity`, `dimensions` vào danh sách `STOPWORDS` để tránh gửi query rác lên Shopify GraphQL làm trả về 0 sản phẩm.
2. **Ưu tiên Verified Catalog Pool:** Ưu tiên 1 luôn là trích xuất ảnh từ các sản phẩm đã được xác thực trong Brief và Bảng so sánh (Decision Table) trước khi mở rộng tìm kiếm tự do ngoài catalog.
3. **Phân bổ và định danh ảnh:** Đảm bảo 4–7 ảnh sản phẩm trong body + 1 ảnh hero khác biệt; kiểm tra perceptual hash (ahash, dhash, sha256) chống trùng lặp.

### 21.3. Chuẩn Hóa Khâu Hậu Xử Lý HTML & Fact Audit
1. **Thuật toán Chữa lành Giá (`heal_corrupted_prices`):** Sử dụng regex negative lookbehind `(?<=[(\s>]),\d{3}` để chống nuốt dấu `$` và chống cụt số (`range from .10 to ,371.10` -> `$2,348.10 to $3,371.10`), đồng thời không làm hỏng các chuỗi giá hợp lệ có dấu phẩy ngăn cách hàng nghìn.
2. **Bảo toàn thẻ HTML trong FAQ:** Loại bỏ việc bọc mù `html.escape()` lên câu trả lời FAQ. Giữ nguyên các thẻ HTML hợp lệ (`<a href="...">`, `<strong>`, `<em>`, `<p>`), xóa bỏ triệt để lỗi biến link thành `&lt;a&gt;`.
3. **Nhận diện Ngữ cảnh Phủ định (Negation Context Awareness):** Trong `article_fact_auditor.py`, các kiểm tra chính sách cấm (forbidden claims) phải nhận diện câu phủ định hợp lệ (`not`, `does not`, `never`, `rather than`) và câu hỏi FAQ (`does ... include ...?`). Không phạt nhầm các câu khẳng định đúng chính sách store.
4. **Chuẩn hóa Domain Nội bộ:** Tự động chuyển đổi các link nội bộ trỏ về subdomain kỹ thuật (`wrydeco.myshopify.com`) sang domain chính thức `https://wrydeco.com`.

### 21.4. Chuẩn Hóa Khâu Kiểm Thử & Vận Hành
1. **Bộ Test Suite cô lập 9/9 Passed:** `test_suite.py` chạy toàn bộ 9 tests trong môi trường tạm thời (`tempfile.TemporaryDirectory()`), đảm bảo `zero_live_config_side_effects: true` 100%, không bao giờ làm sửa đổi hay rò rỉ side-effect lên file cấu hình thật `data/stores.json` và `data/proxy.json`.
2. **Quy tắc Batch Production Tối ưu:** Khuyến nghị chạy theo batch từ **3 đến 5 bài / lần prompt** qua MCP server `wrydeco-blog-scaling-mcp` để tối ưu hóa context window và độ ổn định mạng.
3. **Cơ chế Fallback Live Verification:** Khi custom domain công khai gặp lỗi routing 404 từ mạng ngoài, hệ thống tự động fallback kiểm tra trên `myshopify_url` để xác thực tính toàn vẹn của layout, hình ảnh và DOM mà không làm nghẽn tiến trình xuất bản.
4. **Tích hợp Thông báo Đa Kênh (`mod-notifications`):** Tự động gửi đồng thời Windows Desktop Toast (`mod toast`) và Remote Mobile Notification (`mod notify send` qua ntfy) ngay khi mỗi batch hoàn tất.



