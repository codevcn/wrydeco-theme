# BÁO CÁO TIẾN ĐỘ CÀO SẢN PHẨM & TRẠNG THÁI AMAZON

*Ngày thực hiện: 24/09/2026*
*Dữ liệu đối chiếu: `todo/feed-product/FURNITURE LISTING.xlsx` vs `backup/product-data/from-real-store/products_export_1.csv`*

---

## I. TỔNG QUAN SỐ LIỆU ĐỐI SOÁT

| Hạng mục | Số lượng | Tỷ lệ | Ghi chú |
| :--- | :---: | :---: | :--- |
| **Tổng sản phẩm trong file LISTING** | **180** | 100% | Bỏ qua 2 dòng tiêu đề đầu và các dòng trống |
| **Đã cào về Shopify CSV** | **119** | **66.1%** | Đã có trong `products_export_1.csv` |
| **Chưa được cào về Shopify CSV** | **61** | **33.9%** | Danh sách cần xử lý |

> **Lưu ý về file Shopify Real Store:**
> - File CSV thực tế có 178 sản phẩm (`Handle`), trong đó:
>   + 119 sản phẩm map khớp với ASIN trong file LISTING.
>   + 2 ASIN trong file LISTING (`B0H7BQ8WZS`, `B0H7B833DF`) được map vào 2 cặp sản phẩm variant khác nhau trên Shopify (mỗi ASIN tạo ra 2 sản phẩm).
>   + 10 sản phẩm trên Shopify không có `amazon_link` (chủ yếu là nhóm gương treo tường thủ công `organic-...-wall-mirror`, `rustic-...-wall-mirror` và `custom-wood-certificate-for-richard`).

---

## II. KẾT QUẢ KIỂM TRA TRỰC TIẾP TRÊN AMAZON (CHO 61 SẢN PHẨM CHƯA CÀO)

Hệ thống đã sử dụng **Playwright MCP** để mở từng link sản phẩm Amazon thực tế và kiểm tra chính xác các nút chức năng, trạng thái kho hàng:

| Trạng thái trên Amazon | Số lượng | Tỷ lệ | Ý nghĩa nghiệp vụ |
| :--- | :---: | :---: | :--- |
| 🟡 **Có nút 'Customize Now'** | **49** | **80.3%** | Sản phẩm có tùy biến kích thước / option |
| 🔴 **Báo 'Currently Unavailable'** | **1** | **1.6%** | Sản phẩm tạm hết hàng / ngừng bán |
| 🟢 **Có sẵn (Add to Cart / Buy Now)** | **0** | **0.0%** | Sản phẩm chuẩn, mua trực tiếp được ngay |
| ⚪ **'See All Buying Options'** | **2** | **3.3%** | Không có buybox trực tiếp, mua qua seller phụ |
| ❌ **Link lỗi / Page Not Found (Dog 404)** | **9** | **14.8%** | Link đã bị xóa / ASIN không còn tồn tại trên Amazon |

---

### 1. Danh sách 49 sản phẩm có nút màu vàng 'Customize Now'
Các sản phẩm này trên Amazon có nút vàng **Customize Now**, cho phép khách chọn tùy biến chi tiết trước khi đặt hàng:

| Row Excel | ASIN | Danh mục | Giá tham khảo | Tên sản phẩm | Link Amazon |
| :---: | :---: | :--- | :---: | :--- | :--- |
| 26 | `B0H6BWCCTX` | BOOKSHELF | $744.00 | Handcrafted Tree Branch Floating Shelf – Unique Natural Wood Wall Shelf, Sculptural Art Display Bookcase for Living Room, Study, Bedroom & Home Library (1 Floating Shelf) (C03) | [Xem Link](https://www.amazon.com/dp/B0H6BWCCTX) |
| 27 | `B0H6BXNZCJ` | BOOKSHELF | $744.00 | Handcrafted Tree Branch Floating Shelf – Unique Natural Wood Wall Shelf, Sculptural Art Display Bookcase for Living Room, Study, Bedroom & Home Library (1 Floating Shelf) (C04) | [Xem Link](https://www.amazon.com/dp/B0H6BXNZCJ) |
| 30 | `B0H6C7MZ5R` | BOOKSHELF | $899.00 | Handcrafted Tree Branch Floating Shelves – Unique Natural Wood Wall Shelf Set, Sculptural Art Display Bookcase for Living Room, Study, Bedroom & Home Library (2 Level Shelves) (C1) | [Xem Link](https://www.amazon.com/dp/B0H6C7MZ5R) |
| 40 | `B0H6DB6S6X` | BOOKSHELF | $998.95 | Handcrafted Tree Branch Floating Shelf – Unique Natural Wood 3-Level Wall Bookcase, Sculptural Art Display Shelf for Living Room, Study, Bedroom & Home Library (C1) | [Xem Link](https://www.amazon.com/dp/B0H6DB6S6X) |
| 41 | `B0H39168ZT` | CAT TREE | $297.95 | Wall Mounted Cat Tree, Natural Wood Floating Cat Climbing Tree with Perches, Large Cat Wall Furniture for Indoor Cats (Option 4) | [Xem Link](https://www.amazon.com/dp/B0H39168ZT) |
| 42 | `B0H38XX6XP` | PARROT TREE | $990.00 | Handmade Wood Parrot Play Stand, Natural Solid Wood Bird Playground with Perches, Swing, Food Tray for Small Birds (Option 4) | [Xem Link](https://www.amazon.com/dp/B0H38XX6XP) |
| 47 | `B0H3YVJ6DQ` | COFFEE TABLE | $990.00 | Handcrafted Wooden Coffee Table with Sculptural Base, Rustic Modern Living Room Center Table for Farmhouse, Boho & Natural Home Decor (Option 1) | [Xem Link](https://www.amazon.com/dp/B0H3YVJ6DQ) |
| 48 | `B0H3Z94YZL` | CONSOLE TABLE | $990.00 | Handcrafted Wooden Coffee Table with Sculptural Base, Rustic Modern Living Room Center Table for Farmhouse, Boho & Natural Home Decor (Option 2) | [Xem Link](https://www.amazon.com/dp/B0H3Z94YZL) |
| 49 | `B0H3ZHFT3K` | CONSOLE TABLE | $990.00 | Handcrafted Wooden Coffee Table with Sculptural Base, Rustic Modern Living Room Center Table for Farmhouse, Boho & Natural Home Decor (Option 3) | [Xem Link](https://www.amazon.com/dp/B0H3ZHFT3K) |
| 50 | `B0H3Z9QM4L` | COFFEE TABLE | $3,513.00 | Sculptural Wooden Coffee Table with Organic Cutout Base, Rustic Modern Living Room Center Table for Boho, Farmhouse & Natural Home Decor (Option 4) | [Xem Link](https://www.amazon.com/dp/B0H3Z9QM4L) |
| 51 | `B0H3ZTTCM6` | COFFEE TABLE | $3,378.00 | Sculptural Wooden Coffee Table with Organic Cutout Base, Rustic Modern Living Room Center Table for Boho, Farmhouse & Natural Home Decor (Option 5) | [Xem Link](https://www.amazon.com/dp/B0H3ZTTCM6) |
| 53 | `B0H44RKD1X` | Floating Shelf | $529.00 | Handcrafted Wooden Wall Shelf with Organic Bowl Design, Rustic Floating Display Shelf for Entryway, Living Room & Boho Home Decor (Option 5) | [Xem Link](https://www.amazon.com/dp/B0H44RKD1X) |
| 54 | `B0H454G1YM` | Wooden Lamp Base | $995.00 | Handcrafted Wooden Lamp Base with Sculptural Cutout Design, Replacement Floor Lamp Stand Base for Rustic, Boho & Organic Modern Decor | [Xem Link](https://www.amazon.com/dp/B0H454G1YM) |
| 55 | `B0H456G3C2` | Wooden Lamp Base | $565.00 | Black Wooden Lamp Base with Sculptural Crescent Design, Handcrafted Table Lamp Stand Base Only for Boho, Rustic & Organic Modern Decor (Option 5) | [Xem Link](https://www.amazon.com/dp/B0H456G3C2) |
| 56 | `B0H45BKCNJ` | Tree Coat Rack  | $975.00 | Wooden Tree Coat Rack with Branch Hooks, Freestanding Entryway Hat Stand for Bags, Jackets, Scarves & Boho Home Decor | [Xem Link](https://www.amazon.com/dp/B0H45BKCNJ) |
| 58 | `B0H4M1RC52` | Wooden Fruit Bowl | $85.19 | Handcrafted Wooden Fruit Bowl with Natural Live Edge Look, Rustic Decorative Serving Bowl for Kitchen, Dining Table & Home Decor | [Xem Link](https://www.amazon.com/dp/B0H4M1RC52) |
| 59 | `B0H4LVSYZZ` | Floating Shelf | $990.00 | Wooden Ornate Black Wall Shelf with Carved Floral Detail, Gothic Victorian Floating Display Shelf for Books, Candles & Vintage Home Decor (Option 5) | [Xem Link](https://www.amazon.com/dp/B0H4LVSYZZ) |
| 60 | `B0H4LW9JKH` | Wooden Plant Stand | $1,250.00 | Wooden Plant Stand with Tree-Inspired Shelves, Freestanding Indoor Plant Display Rack for Living Room, Entryway & Boho Home Decor (OPTION 4) | [Xem Link](https://www.amazon.com/dp/B0H4LW9JKH) |
| 62 | `B0H5P5B9ZM` | Wood Floor Lamp Base | $995.45 | Wood Floor Lamp Base Only, Sculptural Driftwood Standing Light Base, Rustic Boho Coastal Decor, Choose Finish and Size | [Xem Link](https://www.amazon.com/dp/B0H5P5B9ZM) |
| 63 | `B0H5PPDZ9D` | Wall Decorative Sculpture | $978.45 | PREAUREUM Driftwood Wall Decorative Sculptural Wood Light Cover, Rustic Coastal Boho Wall Decor for Living Room, Bedroom, Entryway | [Xem Link](https://www.amazon.com/dp/B0H5PPDZ9D) |
| 64 | `B0H5PSN8ZG` | End Table | $649.00 | Solid Wood End Table, Sculptural Round Side Table with Organic Pedestal Base, Rustic Modern Accent Table for Living Room Bedroom | [Xem Link](https://www.amazon.com/dp/B0H5PSN8ZG) |
| 65 | `B0H5PWM7CB` | Bedside Table | $1,673.00 | Handmade Solid Wood Nightstand, Rustic Modern Bedside Table with 3 Storage Shelves, Wooden Bedroom Accent Furniture (Option 1) | [Xem Link](https://www.amazon.com/dp/B0H5PWM7CB) |
| 70 | `B0H5VC6YFV` | Standing bookshelf | $1,684.00 | 6 Tier Tree Branch Floor Shelf Solid Wood Bookcase, Wall Mounted Vintage Bookshelf for Rustic Home Decor (Rustic Bookshelf) | [Xem Link](https://www.amazon.com/dp/B0H5VC6YFV) |
| 71 | `B0H5VLX973` | Standing bookshelf | $1,838.02 | Tree Branch Floor Shelf Solid Wood Bookcase, Wall Mounted Live Edge Shelves for Vintage Rustic Home Decor (Option 5) | [Xem Link](https://www.amazon.com/dp/B0H5VLX973) |
| 75 | `B0H5V97HX3` | Standing bookshelf | $1,684.00 | Tree Branch Floor Shelf Solid Wood Bookcase, Wall Mounted Vintage Bookshelf for Home Decor Living Room Library | [Xem Link](https://www.amazon.com/dp/B0H5V97HX3) |
| 79 | `B0H622L8ND` | Rustic Wine Rack  | $897.00 | Rustic Wine Rack for Kitchen Island, Sculptural Wooden Bottle Holder, 3-Tier Countertop Display Shelf for Home Bar Decor (Option 3) | [Xem Link](https://www.amazon.com/dp/B0H622L8ND) |
| 82 | `B0H61RDSQ4` | Jewelry Tree Organizer Stand | $325.98 | Organic Solid Walnut Jewelry Tree Organizer Stand, Branch Necklace Holder with Tray Base for Rings, Bracelets & Dresser Decor (OPTION 3) | [Xem Link](https://www.amazon.com/dp/B0H61RDSQ4) |
| 83 | `B0H61XK3PR` | Floating Shelf | $398.00 | Boho Sun Wall Shelf, Wooden Sunburst Floating Shelf for Living Room Decor, Plant Display Wall Mounted Shelf, 4 Sizes (Option 4) | [Xem Link](https://www.amazon.com/dp/B0H61XK3PR) |
| 84 | `B0H626Z2Z1` | Entryway Shoe Bench Rack | $1,320.00 | Handmade Entryway Shoe Bench Rack, Solid Wood Rustic Bench with Lower Shoe Storage Shelf, Living Room Hallway Furniture (Option 2, Wood) | [Xem Link](https://www.amazon.com/dp/B0H626Z2Z1) |
| 85 | `B0H621CFVC` | Storage Cabinet | $3,415.00 | Handcrafted Record Player Stand, Solid Wood Turntable Cabinet with Vinyl Storage & Sculptural Horn Design for Living Room Decor (Option 2) | [Xem Link](https://www.amazon.com/dp/B0H621CFVC) |
| 86 | `B0H61Y2M1W` | Standing bookshelf | $3,215.00 | Rustic Tree Bookshelf, Solid Wood 70" H x 60" W Nature Inspired Bookcase with Open Shelves for Living Room Wall Decor (Option 2) | [Xem Link](https://www.amazon.com/dp/B0H61Y2M1W) |
| 87 | `B0H626NQW3` | Fireplace Mantel Shelf | $980.45 | Rustic Fireplace Mantel Shelf, Solid Wood Wall Mounted Mantel for Living Room and Family Room Decor, Floating Shelf for Seasonal Display, Multiple Sizes (Option 2) | [Xem Link](https://www.amazon.com/dp/B0H626NQW3) |
| 88 | `B0H626BQQX` | Coat Rack | $3,405.00 | Rustic Coat Rack with Shoe Shelf, 70” H x 60” W Entryway Hall Tree Organizer for Mudroom, Hallway, Foyer Storage (Option 5) | [Xem Link](https://www.amazon.com/dp/B0H626BQQX) |
| 89 | `B0H622F9MV` | Tree Wine Rack  | $1,980.62 | Tree Wine Rack Wall Decor, Rustic Solid Wood Wine Holder with Metal Bottle Shelves, Home Bar Furniture for Living Room, 3 Sizes (Option 1) | [Xem Link](https://www.amazon.com/dp/B0H622F9MV) |
| 91 | `B0H6FHFGT2` | Floating Shelf | $125.45 | Handcrafted Live Edge Floating Shelves Many Sizes, Solid Wood Wall Shelf for Living Room, Bedroom, Kitchen, Rustic Farmhouse Decor | [Xem Link](https://www.amazon.com/dp/B0H6FHFGT2) |
| 94 | `B0H6FGCCVP` | Storage Cabinet | $2,585.00 | Modern Wooden Record Stand, Solid Wood Vinyl Record Storage Cabinet with Turntable Shelf, Sculptural Media Console for Bedroom Living Room (OPTION 1) | [Xem Link](https://www.amazon.com/dp/B0H6FGCCVP) |
| 99 | `B0H6J7MGYS` | Floating Shelf | $116.45 | Floating Plant Shelf, Solid Wood Wall Mounted Shelves for Small Plants, Handmade Hanging Shelf Home Decor (Option 5) | [Xem Link](https://www.amazon.com/dp/B0H6J7MGYS) |
| 101 | `B0H6J42LT7` | Floating Shelf | $198.31 | Floating Wood Shelf Art, Mountain Sculpture Wall Shelf, Solid Wood Live Edge Wavy Floating Shelf, Wall Mounted Home Decor (Option 1) | [Xem Link](https://www.amazon.com/dp/B0H6J42LT7) |
| 102 | `B0H6J3639N` | Floating Shelf | $130.80 | Tree of Life Floating Display Shelf, Solid Wood Wall Shelf, Farmhouse Rustic Floating Shelf, Handmade Wooden Wall Decor for Plants, Candles, Small Decor (Tree of Life) | [Xem Link](https://www.amazon.com/dp/B0H6J3639N) |
| 104 | `B0H6JJJ889` | Floating Shelf | $246.20 | Handmade Live Edge Curved Wall Shelf, Wavy Floating Suar Wood Shelf, Solid Wood Wall Mounted Shelf for Books, Plants & Home Decor (Option 1) | [Xem Link](https://www.amazon.com/dp/B0H6JJJ889) |
| 105 | `B0H6J599V2` | Floating Shelf | $98.95 | Rustic Live Edge Wood Floating Shelf, Solid Wood Wall Mounted Storage Shelf with Natural Edge Back, Decorative Display Shelf for Plants Books Living Room Decor (Option 1) | [Xem Link](https://www.amazon.com/dp/B0H6J599V2) |
| 160 | `B0H9QN4RJ5` | Table | $2,975.00 | Handcrafted Solid Wood Accent Table – Unique Natural End Table, Sculptural Art Furniture for Living Room, Bedroom, Study, Entryway & Home Décor | [Xem Link](https://www.amazon.com/dp/B0H9QN4RJ5) |
| 161 | `B0H9Q5TLW6` | Table | $2,975.00 | Handcrafted Solid Wood Accent Table – Unique Natural End Table, Sculptural Art Furniture for Living Room, Bedroom, Study, Entryway & Home Décor | [Xem Link](https://www.amazon.com/dp/B0H9Q5TLW6) |
| 162 | `B0H9Q7ST9C` | Table | $2,975.00 | Handcrafted Solid Wood Accent Table – Unique Natural End Table, Sculptural Art Furniture for Living Room, Bedroom, Study, Entryway & Home Décor | [Xem Link](https://www.amazon.com/dp/B0H9Q7ST9C) |
| 163 | `B0H9Q9R79V` | Table | $2,975.00 | Handcrafted Solid Wood Accent Table – Unique Natural End Table, Sculptural Art Furniture for Living Room, Bedroom, Study, Entryway & Home Décor | [Xem Link](https://www.amazon.com/dp/B0H9Q9R79V) |
| 168 | `B0HBBCBQ7K` | CONSOLE TABLE | $2,899.00 | Handcraft Tree Branch Wood Console Table, Rustic Organic Entryway Sofa Table, Accent Narrow Hallway Display Table for Living Room, Foyer, Entryway, The Vermont Foliage | [Xem Link](https://www.amazon.com/dp/B0HBBCBQ7K) |
| 169 | `B0HB4XSS9Y` | CONSOLE TABLE | $2,994.00 | Handcraft Curved Wood Console Table, Organic Sculptural Entryway Sofa Table, Mid-Century Accent Narrow Hallway Display Table for Living Room, Foyer, Entryway, Walnut Finish, The Moore Silhouette | [Xem Link](https://www.amazon.com/dp/B0HB4XSS9Y) |
| 170 | `B0H8D2L7QH` | Bathroom vanity | $5,969.00 | Handcraft Live Edge Solid Wood Floating Bathroom Vanity Base with Open Storage Shelf - Wall Mounted Rustic Natural Wood Console for Vessel Sinks, The Yellowstone Lodge, Frontier Homestead | [Xem Link](https://www.amazon.com/dp/B0H8D2L7QH) |
| 181 | `B0HC7BYBN8` | TV stand | $2,985.00 | Rustic Tree Branch TV Stand, Floating Natural Solid Wood Media Console, Wabi-Sabi Solid Wood Entertainment Center, Handcrafted TV Shelf for Living Room, Natural Wood, Ancient Reach | [Xem Link](https://www.amazon.com/dp/B0HC7BYBN8) |

---

### 2. Danh sách 1 sản phẩm có thông báo 'Currently Unavailable'
Các sản phẩm này đang tạm hết hàng hoặc bị ẩn trên Amazon (không có nút mua hay tùy biến):

| Row Excel | ASIN | Danh mục | Tên sản phẩm | Ghi chú / Trạng thái kho | Link Amazon |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 117 | `B0H6Y5KXFN` | Corner bookshelf | Handcrafted Tree Branch Floating Shelf – Unique Natural Wood Multi-Layer Wall Shelf for Living Room Corner, Sculptural Art Bookcase for Study & Home Library (C2) | Currently unavailable. We don't know when or if this item will be back in stock. | [Xem Link](https://www.amazon.com/dp/B0H6Y5KXFN) |

---

### 3. Danh sách các sản phẩm ở trạng thái khác (11 sản phẩm)

#### a. Có nút Add to Cart / Buy Now thông thường (In Stock):
| Row Excel | ASIN | Danh mục | Giá | Tên sản phẩm | Link Amazon |
| :---: | :---: | :--- | :---: | :--- | :--- |

#### b. 'See All Buying Options' (Mua qua danh sách người bán):
| Row Excel | ASIN | Danh mục | Giá | Tên sản phẩm | Link Amazon |
| :---: | :---: | :--- | :---: | :--- | :--- |
| 14 | `B0H6B6GNR4` | BOOKSHELF | $995.95 | Handcrafted Rustic Tree Branch Bookshelf for Living Room Bedroom, Natural Wood Shelf, Custom Wood Wall Shelf with 8-Tier Shelves, 6 ft x 7 ft | [Xem Link](https://www.amazon.com/dp/B0H6B6GNR4) |
| 171 | `B0H8CZ9XWL` | Bathroom vanity | $209.99 | Handcraft Live Edge Solid Wood Floating Bathroom Vanity Base with Open Storage Shelf - Wall Mounted Rustic Natural Wood Console for Vessel Sinks, The Yellowstone Lodge, Appalachian Timber | [Xem Link](https://www.amazon.com/dp/B0H8CZ9XWL) |

#### c. Link 404 / Bị xóa khỏi Amazon (Dog of Amazon):
| Row Excel | ASIN | Danh mục | Trạng thái | Link Amazon |
| :---: | :---: | :--- | :--- | :--- |
| 24 | `B0H6YTPGF8` | BOOKSHELF | Trang báo lỗi `Page Not Found` (Chó Amazon) | [Xem Link](https://www.amazon.com/dp/B0H6YTPGF8) |
| 128 | `B0H7SZGHQQ` | Standing bookshelf | Trang báo lỗi `Page Not Found` (Chó Amazon) | [Xem Link](https://www.amazon.com/dp/B0H7SZGHQQ) |
| 130 | `B0H7T88PBJ` | Standing bookshelf | Trang báo lỗi `Page Not Found` (Chó Amazon) | [Xem Link](https://www.amazon.com/dp/B0H7T88PBJ) |
| 154 | `B0H8DM8L6T` | Corner bookshelf | Trang báo lỗi `Page Not Found` (Chó Amazon) | [Xem Link](https://www.amazon.com/dp/B0H8DM8L6T) |
| 155 | `B0H8F1YTQW` | NURSERY | Trang báo lỗi `Page Not Found` (Chó Amazon) | [Xem Link](https://www.amazon.com/dp/B0H8F1YTQW) |
| 156 | `B0H8DQ152G` | Corner bookshelf | Trang báo lỗi `Page Not Found` (Chó Amazon) | [Xem Link](https://www.amazon.com/dp/B0H8DQ152G) |
| 157 | `B0H8DM477Y` | Corner bookshelf | Trang báo lỗi `Page Not Found` (Chó Amazon) | [Xem Link](https://www.amazon.com/dp/B0H8DM477Y) |
| 158 | `B0H8DKLXQ4` | Corner bookshelf | Trang báo lỗi `Page Not Found` (Chó Amazon) | [Xem Link](https://www.amazon.com/dp/B0H8DKLXQ4) |
| 159 | `B0H8DMNP15` | Corner bookshelf | Trang báo lỗi `Page Not Found` (Chó Amazon) | [Xem Link](https://www.amazon.com/dp/B0H8DMNP15) |

---

## III. KHUYẾN NGHỊ HÀNH ĐỘNG TIẾP THEO
1. **Đối với nhóm Customize Now**: Cần cào cả thông tin các options tùy biến để thiết lập biến thể tương ứng trên Shopify.
2. **Đối với nhóm 404 (Page Not Found)**: Nên cập nhật lại link ASIN mới trong file Excel hoặc loại bỏ khỏi danh sách cào.
3. **Đối với nhóm Currently Unavailable**: Xem xét có nên tiếp tục cào hay chờ hàng active lại trên Amazon.