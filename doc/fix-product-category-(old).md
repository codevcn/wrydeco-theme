Store của bạn đặt ngôn ngữ tiếng Việt, nên khi export Shopify ghi cột Product Category bằng tên taxonomy đã dịch sang tiếng Việt (Đồ gỗ > Giá > Giá sách và kệ đứng > Tủ & kệ sách treo). Store US chỉ nhận đúng tên tiếng Anh trong Shopify Standard Product Taxonomy → báo "invalid product category… will not be set".

Bản chất category vẫn đúng, chỉ là ngôn ngữ của chuỗi sai.

Cách tôi lấy tên tiếng Anh

Không tự dịch. Tôi query Admin API lấy category.fullName của từng sản phẩm (API luôn trả tiếng Anh), rồi đối chiếu theo từng handle với giá trị tiếng Việt trong CSV. Kết quả: 75/75 sản phẩm khớp, và 10 giá trị tiếng Việt map 1-1 sang đúng 10 giá trị tiếng Anh — không có trường hợp nào mơ hồ.

┌────────────────────────────────────────────┬─────────────────────────────────────────────────────────┬─────┐
│ Tiếng Việt (CSV cũ) │ Tiếng Anh (đã thay) │ SP │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ Đồ gỗ > Giá > Giá sách và kệ đứng > Tủ & │ Furniture > Shelving > Bookcases & Standing Shelves > │ 28 │
│ kệ sách treo │ Floating Bookcases & Shelves │ │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ Đồ gỗ > Giá > Giá sách và kệ đứng │ Furniture > Shelving > Bookcases & Standing Shelves │ 19 │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ … > Giường và khung giường > Giường thấp │ … > Beds & Bed Frames > Platform Beds & Bed Frames │ 7 │
│ và khung giường │ │ │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ … > Tủ & kệ sách đặt góc │ … > Corner Bookcases & Shelves │ 6 │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ Nhà và vườn > Trang trí > Tác phẩm nghệ │ Home & Garden > Decor > Artwork > Sculptures & Statues │ 4 │
│ thuật > Điêu khắc & Tượng │ │ │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ … > Đầu đầu giường │ Furniture > Beds & Accessories > Headboards │ 4 │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ … > Bàn trang trí > Bàn cà phê │ Furniture > Tables > Accent Tables > Coffee Tables │ 3 │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ … > Bàn trang trí > Bàn console │ Furniture > Tables > Accent Tables > Console Tables │ 2 │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ … > Kệ để máy đĩa than │ … > Media Storage Cabinets & Racks > Turntable Stands │ 1 │
├────────────────────────────────────────────┼─────────────────────────────────────────────────────────┼─────┤
│ … > Giường và khung giường │ Furniture > Beds & Accessories > Beds & Bed Frames │ 1 │
└────────────────────────────────────────────┴─────────────────────────────────────────────────────────┴─────┘

Một cái bẫy tôi phải xử lý

Đồ gỗ > Giá > Giá sách và kệ đứng là tiền tố của 3 chuỗi dài hơn. Nếu thay chuỗi ngắn trước, 3 chuỗi kia sẽ bị cắt cụt thành category sai. Tôi thay chuỗi dài trước, ngắn sau để loại hẳn khả năng đó.

Xác minh sau khi ghi

So sánh từng ô giữa bản gốc và bản mới:

- Số dòng: 2897 → 2897 (không đổi)
- Số ô thay đổi: đúng 75 — bằng đúng số sản phẩm có category
- Cột bị thay đổi: chỉ Product Category, không cột nào khác
- 10 giá trị category mới đều nằm trong danh sách tên tiếng Anh lấy từ API
- Không còn ký tự tiếng Việt nào trong cột category
- Line ending giữ nguyên LF, không có BOM (giống bản gốc)

Đúng ràng buộc bạn đặt ra: 2.896 dòng dữ liệu, chỉ 75 ô của một cột duy nhất bị đụng tới.

File backup bản gốc tôi để ở scratchpad (products_export_1.csv.bak) phòng khi bạn cần đối chiếu.

Import lại thử — thông báo lỗi category sẽ không còn. Nếu store US vẫn báo invalid ở một dòng nào đó, gửi tôi ảnh mới, nhiều khả năng là do phiên bản taxonomy giữa 2 store lệch nhau chứ không phải do ngôn ngữ nữa.
