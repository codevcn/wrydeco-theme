# Product SKU Rules — WRYDECO Scraper

Cập nhật: **12/10/2026 (Asia/Saigon)**. Đây là quy tắc hiện hành cho tính năng set SKU trong scraper. Dữ liệu lịch sử cuối tài liệu không phải kết quả kiểm thử của phiên bản mới.

## 1. Chọn prefix theo tags cấu hình

Prefix lấy từ `overrides.tags` của dòng sản phẩm trong manifest, không lấy từ URL hay trạng thái có metafield Amazon.

- Bất kỳ tag nào chứa `amazon`, không phân biệt hoa/thường: prefix `amz`, định danh ASIN 10 ký tự từ link Amazon trong manifest.
- Không tag nào chứa `amazon`: prefix `wry`, định danh rút gọn từ handle Shopify hiện có. Ví dụ `organic-fluid-console` → `ORGFLU`.
- `source_amazon`, `Amazon`, `amazon_import` đều chọn `amz`. `amzon` không phải alias.
- Thiếu tags sử dụng mặc định hiện hành của tool là `source_amazon`; truyền `tags: []` để chọn `wry`.
- Prefix viết thường; thành phần định danh/thuộc tính viết hoa. SKU cũ đúng cấu trúc nhưng prefix viết hoa vẫn được giữ nếu không trùng (so sánh bảo thủ không phân biệt hoa/thường).
- Thêm nguồn mới bằng `prefix_rules` có thứ tự trong `scraper/sku_rules.json`; rule khớp đầu tiên thắng. `default_prefix` là fallback. Mỗi rule khai báo `tag_contains`, `prefix`, `identity` (`asin` hoặc `handle`).

## 2. Cấu trúc

`{prefix}-{identity}-{FINISH}-{SIZE}[-{EXTRA}...]-{INDEX}`

Ví dụ: `amz-B0HB4TTLJY-NAT-W65H60D10-01`.

- Chỉ chữ ASCII, chữ số và dấu nối; không dấu cách/ký tự marketing.
- Mã mới tối đa **40 ký tự** (giới hạn của tool; không phải tuyên bố giới hạn SKU của Shopify).
- INDEX là số dương, tối thiểu 2 chữ số: `01`, `02`, … `99`, `100`; không quay vòng về `00`.
- Không có finish hoặc size trong dữ liệu option: dùng `NA`, không suy đoán từ ảnh, title hoặc giá.
- Default Title: mã phụ `DEFA`.
- Không có giá trị thực tế sau khi làm sạch: dừng riêng sản phẩm, ghi lỗi để người dùng xử lý.

## 3. Màu / finish luôn viết tắt

| Giá trị sạch | Mã |
| --- | --- |
| Natural / Natural Finish | NAT |
| Warm Wood | WARM |
| Dark Warm Wood | DK-WARM |
| Cool Dark Wood | CD-WOOD |
| Light Oak / Oak | L-OAK / OAK |
| Walnut / Dark Walnut | WAL / DK-WAL |
| Black / Black Wood | BLK |
| Custom / Custom Finish | CUST |
| White / Red / Blue / Green | WHT / RD / BLU / GRN |
| Grey / Gray / Gold / Silver | GRY / GRY / GLD / SLV |
| Brown / Tan | BRN / TN |
| Same as Main Image Color / As Picture | IMG |

Finish mới luôn dùng mã rút gọn: lấy tối đa 3 ký tự mỗi từ, với từ ngắn lấy ít hơn độ dài gốc, ghép bằng dấu nối; tối đa 7 ký tự. Ví dụ `Champagne Oak` → `CHA-OA`, `Mystic` → `MYS`. Nếu quá dài, giữ phần đầu và thêm 4 ký tự SHA-256 xác định từ giá trị, không dùng ngẫu nhiên. Bổ sung alias/mã chính thức trong `finish_codes` khi cần.

## 4. Size mới không cần bảng cố định

- Phân tích số trước hoặc sau nhãn W/H/D/L, giữ thứ tự chiều được cung cấp.
- `65"Wx65"Hx7"D` → `W65H65D7`.
- `W72 x H38 x D15` → `W72H38D15`.
- `30''W x 30''H x 22''D` → `W30H30D22`.
- `16'' x 12''` → `16X12`: không tự gán nhãn W/H.
- Số thập phân dùng P (`10.5` → `10P5`); khoảng dùng T (`10-12` → `10T12`).
- Đơn vị cm/mm/ft được giữ bằng hậu tố CM/MM/FT, không tự chuyển sang inches; trộn đơn vị thì dừng.
- `Custom Larger Size` → `CUST`. Các nhãn size dạng chữ khác dùng mã rút gọn xác định.
- Không bỏ thầm phần chiều chưa hiểu: dùng fallback từ toàn nhãn. Thành phần size tối đa 16 ký tự, rút gọn kèm digest nếu cần.

## 5. Loại từ marketing khi cào và trước khi tạo SKU

Danh sách mở rộng được tại `marketing_phrases`: Recommended, Best Selling, Best Seller, Bestselling, Popular, Most Popular, Best Choice, Top Rated, Customer Favorite, Staff Pick, Editor's Choice, Popular Size, Best Size, Best for Office, v.v.

- Không phân biệt hoa/thường; hỗ trợ dấu nối, gạch dưới và khoảng trắng giữa các từ.
- Hậu tố ngữ cảnh như Size/Finish/Color/Option ngay sau cụm marketing được xóa cùng cụm; `Most Popular Size` không để sót `Most` hay `Size`.
- Chỉ xóa cụm từ nguyên vẹn: `Popularis` không bị xóa bởi rule `popular`.
- Dọn ngoặc rỗng và dấu phân cách thừa.
- `24"W x 28"H x 14"D - Recommended` → `W24H28D14`.
- `Walnut (Most Popular)` → `WAL`.
- Khi cào, tool xác minh giá trên tất cả lựa chọn DOM gốc trước, rồi làm sạch cả `option_types`, `variants.options` và `selection`. Nhãn đã làm sạch được dùng khi tạo biến thể Shopify, không chỉ trong SKU. Giá, ASIN và chỉ số DOM được giữ; nhãn cũ lưu ở `source_value` để audit.
- Ví dụ nhãn `47''Wx 30''H x 16''D (Popular size)` được lưu lên Shopify thành `47''Wx 30''H x 16''D`; `Custom size` và câu trả lời lắp ráp được giữ.
- Nếu nhiều tổ hợp thành cùng options sau khi làm sạch, chỉ gộp khi giá đã xác minh bằng nhau; lưu nguồn trong `merged_sources`/`source_options`. Khác giá hoặc nhãn trống thì dừng sản phẩm, không ghi Shopify.
- Bước dựng payload Shopify cũng áp dụng bộ lọc để bảo vệ pricing cache/preset và Wood Finish cũ.
- Bộ lọc khi cào không tự sửa nhãn trên sản phẩm đã tồn tại. Tiếp tục checkpoint đã chạy `productSet` vẫn ghép theo options đã lưu để xác minh/sửa SKU.

## 6. Option phụ, độ dài và chống trùng

Option phụ cũng được làm sạch rồi ánh xạ/viết tắt. FLOW = Flowers, LEAF = Leafs/Leaves, YESC = Yes Custom Name/Text; giá trị mới dùng mã xác định. Hai câu trả lời lắp ráp thực tế dùng NASM (tự lắp) và YASM (hẹn lắp ráp chuyên nghiệp).

Khi tổng SKU quá dài, rút gọn chuỗi thuộc tính kèm digest 4 ký tự. Không cắt prefix, định danh ASIN hoặc đuôi INDEX. Audit giữ đủ thông tin trước và sau rút gọn.

- Kiểm tra trùng trong sản phẩm và namespace SKU liên quan trên toàn store, có pagination.
- So sánh bảo thủ không phân biệt hoa/thường, dù Shopify xem SKU là case-sensitive.
- Nếu trùng: tăng INDEX, dựng lại SKU, kiểm tra lại đến khi có mã chưa sử dụng. Không chỉ báo lỗi rồi bỏ qua.
- Giữ SKU đúng chuẩn và không trùng của biến thể sống sót khi chạy lại/đảo thứ tự; dự trữ mã cũ trước khi cấp mã mới.
- Giữ cùng mã trong retry bằng kế hoạch đã lưu. Nhiều sản phẩm có cùng ASIN/handle rút gọn vẫn được kiểm tra và cấp lại mã khi cần.
- Shopify worker giữ khóa SKU trong tiến trình server khi apply. Thay đổi đồng thời từ app bên ngoài được phát hiện ở vòng xác minh; không có cam kết khóa các app Shopify khác.

## 7. Tích hợp và verification loop

Batch: cào → kiểm chứng giá → nội dung đã validate → ghép đủ options (kể cả Wood Finish) → lập SKU plan → ghi cùng `productSet` → đọc lại và kiểm tra SKU → tiếp tục media/metafields/channels.

- `sku_plan.json` lưu options gốc, mã, original/cleaned/code, preserved, collisions_resolved và phiên bản rule.
- `final_config.json` chứa SKU từng biến thể và plan; `apply_progress.json` thêm `sku_verified`.
- Retry checkpoint cũ thiếu SKU dùng `productVariantsBulkUpdate` theo ID; không cần chạy lại productSet.
- Khi `product_set` đã hoàn tất, retry dùng options từ `final_config.json`; checkpoint cũ chưa có file này dựng lại options theo hành vi cũ. Không áp bộ lọc mới để đổi nhãn trong một lượt tiếp tục chỉ xác minh SKU.
- Vòng xác minh tối đa 3 lượt: đọc toàn bộ biến thể, ghép bằng option name/value (không ghép theo vị trí), kiểm tra ownership, cấp lại mã bị trùng, ghi phần lệch, rồi đọc lại độc lập.
- Chỉ hoàn tất khi mọi biến thể có mã đúng plan, không rỗng và không trùng. Chưa hội tụ thì `needs_attention`; Retry Shopify tiếp tục từ plan.
- Dry run đọc Shopify và xuất plan nhưng không ghi dữ liệu Shopify.
- SKU tự động là một phần của flow **Chạy batch**. Hai nút Preview SKU/Set SKU, API `/api/shopify/sku-plan`, `/api/shopify/set-skus` và panel kết quả riêng đã được gỡ ngày 12/10/2026. Logic tạo mã, chống trùng, xác minh và retry của batch vẫn giữ nguyên.
- Dashboard dùng **VIEW LINKS** để cuộn instant về danh sách sản phẩm và **VIEW PROGRESS** để cuộn instant về Tiến trình; chừa khoảng cách dưới header cố định.

## 8. Dữ liệu lịch sử ngày 11/10/2026

Báo cáo cũ ghi 251 sản phẩm, 7.848 biến thể, 7.217 AMZ và 631 WRY, 0 SKU trống/trùng. Đây là số liệu lịch sử do báo cáo trước cung cấp, không phải số liệu live đã xác minh cho lần triển khai mới. Quy tắc cũ chọn prefix bằng link Amazon và cho phép 41 ký tự đã được thay bằng quy tắc ở trên.


## 9. Verification loop thực tế ngày 12/10/2026

Các ghi nhận Preview/Set SKU và panel Variant SKU dưới đây là lịch sử kiểm thử trước khi gỡ các thao tác thủ công; flow batch tự tạo SKU vẫn hoạt động.

- Chạy batch qua Chrome với B0HB4TTLJY → 10369383071801, B0HB4VK5CR → 10369382973497, B0HB577VSJ → 10369346175033, B0HB4RVK2B → 10369346043961. Bỏ B0HB4XFVW4 theo yêu cầu.
- Tags: source_amazon, scraper_tool; product type: console-table.
- Cả 4 sản phẩm applied, mỗi sản phẩm 50 biến thể (200 tổng).
- Dữ liệu thật phát hiện Popular Size, Best Size, Best for Office; đã bổ sung rule và test hồi quy, rồi set SKU lại qua UI.
- 126 tests pass. Preview UI hiển thị 200 rows; Set SKU hiển thị Verified on Shopify; chạy lại giữ nguyên 200/200 mã.
- Đối chiếu độc lập qua Admin GraphQL quét 8.048 biến thể toàn catalog: 200 SKU test không rỗng, không trùng nhau hoặc với sản phẩm khác, đúng rule mới; dài nhất 39 ký tự.
- Set SKU giữ nguyên giá, options, media, tags, type, title/SEO/publications. Riêng metafield judgeme.review_widget_data của một sản phẩm cập nhật tên từ aaa sang tên mới sau batch; thay đổi metadata app này được ghi riêng, không tính là ghi từ payload SKU.
- Audit chi tiết: .runtime/verification/sku-verification.json; snapshots trước/sau và screenshot nằm cùng thư mục. Đây là trạng thái tại thời điểm kiểm thử, không phải cam kết cho thay đổi từ app bên ngoài trong tương lai.

### Bổ sung: làm sạch nhãn khi cào và cải thiện Dashboard

- 139 tests pass, gồm fixture browser cho customization và PDP variations, nhãn rỗng, trùng options cùng/khác giá, pricing cache và tiếp tục checkpoint cũ.
- Đối chiếu pricing thật đã lưu từ 4 ASIN ở trên: loại marketing khỏi 120 nhãn size trong 200 biến thể, giữ nguyên toàn bộ giá và số tổ hợp. Kết quả ở `.runtime/verification/marketing-cleanup.json`; không ghi lại sản phẩm trên store trong lượt kiểm thử bổ sung này.
- Chrome UI: Preview đủ 200 rows; Variant SKU mặc định đóng, click/Enter mở đóng; VIEW LINKS nằm trên VIEW LOG, cuộn instant về danh sách và chừa khoảng cách dưới header cố định. Screenshot: `.runtime/verification/sku-collapsed-view-links.png`.
