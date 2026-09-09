# BẢN ĐỀ XUẤT PHƯƠNG ÁN & CẤU TRÚC NỘI DUNG CHUẨN: [COLLECTION BUYING GUIDE / SEO CONTENT]

> **Tài liệu tham chiếu dự án**: `todo/fix/todo.md`, `todo/TAM/results/seo-collection.csv`, `todo/TAM/wrydeco-final-us-seo-plan-2026-08-24.md`  
> **Nguyên tắc cốt lõi**: SSR-First Technical SEO, Semantic HTML5, Wrydeco Design System, Zero-Duplicate Intent, EEAT & Conversion Optimization.

---

## MỤC LỤC
1. [PHẦN I: BẢN ĐỀ XUẤT PHƯƠNG ÁN TỔNG THỂ (OVERVIEW & TECHNICAL ARCHITECTURE)](#phần-i-bản-đề-xuất-phương-án-tổng-thể)
   - [1. Mục tiêu & Vị trí trong cấu trúc trang](#1-mục-tiêu--vị-trí-trong-cấu-trúc-trang)
   - [2. Cấu trúc Nội dung chuẩn (Content Architecture)](#2-cấu-trúc-nội-dung-chuẩn)
   - [3. Kiến trúc Kỹ thuật trên Shopify (Technical Architecture)](#3-kiến-trúc-kỹ-thuật-trên-shopify)
   - [4. Đề xuất Bố cục Giao diện (UI/UX Styling)](#4-đề-xuất-bố-cục-giao-diện-uiux-styling)
   - [5. Lộ trình Triển khai từng bước (Action Plan)](#5-lộ-trình-triển-khai-từng-bước)
2. [PHẦN II: ĐỀ XUẤT CẤU TRÚC NỘI DUNG CHUẨN CHO TỪNG COLLECTION ĐANG PUBLISH](#phần-ii-đề-xuất-cấu-trúc-nội-dung-chuẩn-cho-từng-collection-đang-publish)
   - [Nhóm 1: Dòng Trụ Cột Chiến Lược - Tree Bookshelves (Chiếm ~70% Danh mục)](#nhóm-1-dòng-trụ-cột-chiến-lược---tree-bookshelves)
     - [1. Handcrafted Tree Bookshelves (`tree-bookshelves`)](#1-handcrafted-tree-bookshelves-tree-bookshelves)
     - [2. Wall-Mounted Tree Bookshelves (`wall-mounted-tree-bookshelves`)](#2-wall-mounted-tree-bookshelves-wall-mounted-tree-bookshelves)
     - [3. Corner Tree Bookshelves (`corner-bookshelf`)](#3-corner-tree-bookshelves-corner-bookshelf)
     - [4. Rustic Tree Bookshelves (`bookshelf-rustic`)](#4-rustic-tree-bookshelves-bookshelf-rustic)
     - [5. Tree Branch Wall Shelves & Floating Bookshelves (`floating-bookshelf`)](#5-tree-branch-wall-shelves--floating-bookshelves-floating-bookshelf)
     - [6. Standing Tree Bookshelves (`standing-bookshelf`)](#6-standing-tree-bookshelves-standing-bookshelf)
     - [7. Sculptural & Curved Wood Bookshelves (`bookshelf-modern`)](#7-sculptural--curved-wood-bookshelves-bookshelf-modern)
   - [Nhóm 2: Dòng Nội Thất Phòng Ngủ & Điêu Khắc Nghệ Thuật](#nhóm-2-dòng-nội-thất-phòng-ngủ--điêu-khắc-nghệ-thuật)
     - [8. Solid Wood Platform Beds & Live Edge Headboards (`bed-frame-with-headboard`)](#8-solid-wood-platform-beds--live-edge-headboards-bed-frame-with-headboard)
     - [9. Signature Pieces (`signature-pieces`)](#9-signature-pieces-signature-pieces)
     - [10. Handcrafted Wooden Floor Sculptures (`wooden-floor-sculpture`)](#10-handcrafted-wooden-floor-sculptures-wooden-floor-sculpture)
     - [11. Handcrafted Wood Wall Mirrors (`mirror`)](#11-handcrafted-wood-wall-mirrors-mirror)
   - [Nhóm 3: Dòng Bàn Gỗ Tự Nhiên & Kệ Trang Trí](#nhóm-3-dòng-bàn-gỗ-tự-nhiên--kệ-trang-trí)
     - [12. Sculptural Solid Wood Coffee Tables (`coffee-tables`)](#12-sculptural-solid-wood-coffee-tables-coffee-tables)
     - [13. Handcrafted Solid Wood Console Tables (`console-table`)](#13-handcrafted-solid-wood-console-tables-console-table)
     - [14. Handcrafted End Tables (`end-table`)](#14-handcrafted-end-tables-end-table)
     - [15. Floating Wood Shelves (`floating-shelves`)](#15-floating-wood-shelves-floating-shelves)
   - [Nhóm 4: Kệ Rượu & Trang Trí Chuyên Dụng](#nhóm-4-kệ-rượu--trang-trí-chuyên-dụng)
     - [16. Wall-Mounted Wood Wine Racks (`wall-mounted-wine-rack`)](#16-wall-mounted-wood-wine-racks-wall-mounted-wine-rack)
     - [17. Handcrafted Wood Wine Racks (`wine-racks`)](#17-handcrafted-wood-wine-racks-wine-racks)
   - [Nhóm 5: Trang Điều Hướng & Danh Mục Mua Sắm Tổng Hợp](#nhóm-5-trang-điều-hướng--danh-mục-mua-sắm-tổng-hợp)
     - [18. New Arrivals (`new-arrivals`)](#18-new-arrivals-new-arrivals)
     - [19. Explore All Pieces (`all`)](#19-explore-all-pieces-all)

---

# PHẦN I: BẢN ĐỀ XUẤT PHƯƠNG ÁN TỔNG THỂ

## 1. Mục tiêu & Vị trí trong cấu trúc trang

Trong hệ thống trang danh mục của Wrydeco, section **`[COLLECTION BUYING GUIDE / SEO CONTENT]`** nằm ở vị trí chiến lược:

```text
HEADER / MEGA MENU
↓
BREADCRUMB
↓
[COLLECTION HERO] (H1 + Short Intro 70-120 words)
↓
[SUBCOLLECTION NAVIGATION]
↓
FILTER + SORT
↓
PRODUCT GRID (Danh sách sản phẩm chính)
↓
RELATED COLLECTIONS (Slider 4 cards đã hoàn thiện)
↓
★ [COLLECTION BUYING GUIDE / SEO CONTENT] (VỊ TRÍ NÀY) ★
~400–700 words, 3–4 H2s, H3s, Quick Facts, FAQ Accordion
↓
TRUST / BRAND VALUE (Cam kết gỗ thịt, thủ công, bảo hành)
↓
FOOTER
```

### Hai vai trò cốt lõi:
1. **Technical SEO (SSR-First & Semantic Crawlability)**:
   - Cung cấp nội dung chuyên sâu từ **400 đến 700 từ**, được server-render trực tiếp trong mã nguồn HTML ban đầu (không phụ thuộc vào JavaScript/Client Hydration).
   - Sử dụng thẻ `<h2>` và `<h3>` có cấu trúc rõ ràng, tích hợp từ khóa mang tính thương mại và truy vấn thông tin mua sắm (Commercial Investigation Intent).
   - Tạo mạng lưới liên kết nội bộ tự nhiên (**Internal Links**) kết nối chặt chẽ giữa Collection cha, Collection con, các trang hướng dẫn kỹ thuật (*Installation Lab, Size Guide*) và dịch vụ đặt làm theo yêu cầu (*Custom Bespoke*).
2. **Tối ưu hóa Tỷ lệ Chuyển đổi (CRO & Trải nghiệm Người dùng)**:
   - Sản phẩm của Wrydeco là nội thất gỗ tự nhiên nguyên khối cao cấp (giá dao động từ $400 đến $2,500+). Khách hàng Mỹ khi mua dòng sản phẩm này thường có những lo ngại thực tế:
     - *Khả năng chịu tải của các nhánh cây là bao nhiêu?*
     - *Tường thạch cao (drywall studs) có lắp đặt an toàn được không?*
     - *Vân gỗ tự nhiên có bị cong vênh, nứt nẻ hay sai màu thực tế không?*
     - *Cách bảo dưỡng và làm sạch lớp phủ sáp/dầu mờ như thế nào?*
   - Section này đóng vai trò như một **Chuyên gia Nội thất Trực tuyến**, giải tỏa hoàn toàn các băn khoăn trước khi khách rời khỏi trang.

---

## 2. Cấu trúc Nội dung chuẩn

Mỗi bài Buying Guide trên từng Collection được chuẩn hóa theo mô-đun 5 phần:

1. **Section Heading (`H2` chính mang tính chủ đề)**:
   - Tiêu đề sang trọng, chứa từ khóa chính kết hợp góc nhìn thẩm mỹ kiến trúc.
   - *Ví dụ*: *"The Architectural Guide to Tree & Sculptural Bookshelves"*.
2. **Khối Nội dung Chuyên sâu (3–4 mục `H2` / `H3`, độ dài 400–700 từ)**:
   - **Mục 1: Form, Scale & Spatial Fit**: Phân tích kiểu dáng, diện tích mặt sàn, chiều cao trần, cách tính khoảng lọt lòng giữa các kệ.
   - **Mục 2: Solid Wood Craftsmanship & Grain Character**: Phân tích chất liệu gỗ thịt (Walnut, Oak, Ash), độ ẩm tiêu chuẩn sấy lò (kiln-dried 8-12%), vân gỗ độc bản tự nhiên.
   - **Mục 3: Structural Integrity, Wall Mounting & Load Capacity**: Chi tiết phụ kiện neo tường chịu lực, khả năng gắn vào khung xương tường (wall studs), tải trọng từng tầng.
   - **Mục 4: Care, Longevity & Custom Bespoke**: Hướng dẫn lau dầu sáp, chống sốc nhiệt/ẩm và giới thiệu năng lực tùy chỉnh kích thước theo mặt bằng.
3. **Bảng / Khung Thông số Vàng (Quick Facts & Golden Specs)**:
   - Tóm tắt 4–6 thông số cốt lõi: Tải trọng trung bình, loại tường tương thích, thời gian lắp đặt, cấp độ gỗ, thời gian bảo hành.
4. **Mục Hỏi Đáp Nhanh (Collapsible FAQ Schema JSON-LD)**:
   - 3–4 câu hỏi trọng tâm của người dùng, sẵn sàng đánh dấu Schema `FAQPage` để tăng tỷ lệ xuất hiện Rich Snippets trên kết quả tìm kiếm Google.
5. **Đường dẫn Liên kết Nội bộ (Strategic Internal Links)**:
   - Liên kết tự nhiên dẫn khách hàng và Googlebot tới: Collection cha/con liên quan, Trang hướng dẫn lắp đặt ([Installation Guide](/pages/installation-guide)), Hướng dẫn kích thước ([Size Guide](/pages/size-guide)), và [Bespoke Customization](/pages/custom-furniture).

---

## 3. Kiến trúc Kỹ thuật trên Shopify

Để đảm bảo hiệu năng cao nhất, dễ quản trị và chuẩn SEO:

1. **Lưu trữ dữ liệu qua Metafield (Shopify 2.0)**:
   - Định nghĩa Metafield cho Collection: `custom.buying_guide` (kiểu dữ liệu `rich_text_field` hoặc metaobject liên kết).
   - Merchant có thể cập nhật nội dung riêng cho từng collection trực tiếp trong Shopify Admin mà không cần sửa code Liquid.
2. **Cơ chế Fallback thông minh (Graceful Fallback)**:
   - Nếu một collection chưa kịp điền nội dung riêng, Liquid section sẽ tự động:
     - Nhận diện `handle` của collection và hiển thị nội dung chuẩn theo taxonomy cha (Tree, Table, Bed, Sculpture).
     - Hoặc nếu không có nội dung phù hợp, section sẽ tự động ẩn đi hoàn toàn mà không để lại bất kỳ khoảng trắng (whitespace) hay lỗi layout shift (CLS).
3. **Section Liquid: `sections/collection-buying-guide.liquid`**:
   - Sử dụng thẻ ngữ nghĩa chuẩn: `<section class="collection-guide">`, `<article>`, `<header>`, `<h2>`, `<h3>`, `<p>`, `<ul>`.
   - Toàn bộ nội dung chữ được render sẵn từ Server (`SSR`), đảm bảo Googlebot index 100% nội dung ngay lần crawl đầu tiên.

---

## 4. Đề xuất Bố cục Giao diện (UI/UX Styling)

Kế thừa hệ thống nhận diện **Wrydeco Luxury Woodcraft**:

* **Layout 2 Cột (Two-Column Editorial Layout)**:
  - **Cột bên trái (~30%)**: 
    - Cố định nhẹ khi cuộn trang (`position: sticky; top: 100px`).
    - Chứa: Eyebrow (`EDITORIAL GUIDE`), Tiêu đề tóm tắt, Menu mục lục mini (Jump Links trượt mượt mà đến từng `H2`), và Khung *Quick Facts Box* nền gỗ ấm.
  - **Cột bên phải (~70%)**:
    - Nội dung bài đọc phong cách tạp chí kiến trúc (*Architectural Digest / Elle Decor*).
    - Phông chữ Serif trang nhã cho Heading (`Playfair Display` hoặc `Canela`), phông Sans-serif dễ đọc cho văn bản (`Neue Haas Grotesk` hoặc `Inter`, 16.5px - 17.5px, line-height 1.75).
    - Các đoạn trích dẫn (Callout Boxes) có viền mảnh màu nâu gỗ ấm, tạo điểm nhấn nghỉ mắt cho độc giả.
* **Tối ưu trên Mobile & Tablet**:
  - Tự động co về layout **1 cột duy nhất**.
  - Bảng Quick Facts xếp trên hoặc dưới bài viết, mục lục mini chuyển thành thanh trượt ngang tinh gọn (Horizontal Pill Nav) giúp khách lướt đọc mượt mà.

---

## 5. Lộ trình Triển khai từng bước

1. **Bước 1**: Tạo cấu trúc Metafield `custom.buying_guide` trên Shopify Admin qua GraphQL API script.
2. **Bước 2**: Viết code Liquid & CSS cho section mới `sections/collection-buying-guide.liquid`.
3. **Bước 3**: Nhúng section vào `templates/collection.json` tại vị trí ngay dưới `related_collections`.
4. **Bước 4**: Nạp nội dung chuẩn cho các collection ưu tiên (P0 & P1) từ dữ liệu đã được nghiên cứu.
5. **Bước 5**: Dùng `playwright-cli` kiểm tra hiển thị responsive (Desktop, Tablet, Mobile), kiểm tra HTML SSR crawlable, và thông báo qua `mod notify`.

---

# PHẦN II: ĐỀ XUẤT CẤU TRÚC NỘI DUNG CHUẨN CHO TỪNG COLLECTION ĐANG PUBLISH

Sau đây là toàn bộ cấu trúc nội dung chi tiết cho từng collection hiện đang được publish trên online store:

---

## Nhóm 1: Dòng Trụ Cột Chiến Lược - Tree Bookshelves

### 1. Handcrafted Tree Bookshelves (`tree-bookshelves`)
* **Vai trò**: Canonical Parent Category (Pillar Page) - Sở hữu toàn bộ ý định tìm kiếm lớn về kệ sách hình cây.
* **Số lượng sản phẩm hiện tại**: 106 sản phẩm.
* **Primary Keyword**: `tree bookshelf` (Search Intent: Transactional parent category).
* **Secondary Keywords**: `tree bookshelves`, `tree shaped bookshelf`, `tree branch bookshelf`, `wooden tree bookcase`, `solid wood tree bookshelf`.
* **SEO Title**: `Tree Bookshelves | Handcrafted Wood Designs | Wrydeco`
* **Meta Description**: `Explore handcrafted tree bookshelves in wall-mounted, corner and freestanding designs shaped for sculptural storage and distinctive interiors.`

#### Cấu trúc Heading & Nội dung định hướng (550–650 words):
* **H2: Sculptural Form Meets Functional Architecture**
  - Giới thiệu khái niệm đưa thiên nhiên vào không gian sống: Cây sách không chỉ là nơi chứa sách mà là một tác phẩm điêu khắc trung tâm (architectural statement piece).
  - So sánh 3 cấu trúc chính: *Wall-Mounted* (tiết kiệm sàn), *Corner* (tận dụng góc chết), và *Freestanding* (độc lập, linh hoạt di chuyển).
* **H2: Selecting the Ideal Scale & Room Placement**
  - Hướng dẫn đo đạc: Chiều cao trần nhà (tiêu chuẩn 8ft, 9ft hoặc trần cao cathedral).
  - Khoảng lùi thị giác (visual clearance): Cần chừa tối thiểu 12–18 inch hai bên nhánh để dáng cây được tỏa sáng tự nhiên.
* **H2: Solid Hardwoods, Finishes & Natural Grain Variation**
  - Phân tích 3 loại gỗ chủ đạo: Gỗ óc chó đen Bắc Mỹ (American Black Walnut), Sồi trắng (White Oak), và Tần bì (Ash).
  - Độ ẩm chuẩn sấy lò (kiln-dried 8–10%) ngăn ngừa nứt nẻ và cong vênh theo mùa thời tiết Mỹ.
  - Lớp hoàn thiện dầu sáp thực vật tự nhiên (matte hard-wax oil), an toàn tuyệt đối cho gia đình có trẻ nhỏ.
* **H2: Engineering, Load Capacity & Child-Safe Anchoring**
  - Tải trọng thiết kế: 15–25 lbs trên mỗi nhánh độc lập.
  - Bộ phụ kiện neo tường chống lật (heavy-duty anti-tip steel hardware) đi kèm mọi sản phẩm.
* **Quick Facts Box**:
  - *Average Capacity*: 60–120 books (tùy kích thước nhánh)
  - *Wall Stud Spacing*: Tương thích chuẩn 16" / 24" on-center US studs
  - *Material*: 100% Solid Kiln-Dried Hardwood (Zero MDF / Veneer)
  - *Lead Time*: Sẵn kho xuất 3–5 ngày hoặc 3–4 tuần cho đơn Bespoke
* **Recommended FAQs**:
  - *How are tree bookshelves anchored securely?*
  - *Can these shelves hold heavy art and hardcover books?*
  - *How do I choose between wall-mounted and standing models?*

---

### 2. Wall-Mounted Tree Bookshelves (`wall-mounted-tree-bookshelves`)
* **Vai trò**: Child Collection - Dành riêng cho kệ sách dạng cây gắn tường (không chạm đất).
* **Số lượng sản phẩm hiện tại**: 42 sản phẩm.
* **Primary Keyword**: `wall mounted tree bookshelf` (Search Intent: Transactional form).
* **Secondary Keywords**: `wall tree bookshelf`, `wall hanging tree bookshelf`, `tree branch wall mounted bookcase`.
* **SEO Title**: `Wall-Mounted Tree Bookshelves | Wood Designs | Wrydeco`
* **Meta Description**: `Shop wall-mounted tree bookshelves with sculptural branch forms designed to create expressive storage without occupying valuable floor space.`

#### Cấu trúc Heading & Nội dung định hướng (450–550 words):
* **H2: Floating Architecture: Elevating Books Without Floor Footprint**
  - Lý do nên chọn mẫu gắn tường: Mở rộng diện tích sàn nhà, lý tưởng cho căn hộ cao cấp, phòng đọc sách nhỏ, hoặc phòng khách cần sự thông thoáng.
* **H2: Measuring Wall Span, Height & Vertical Projection**
  - Hướng dẫn tính toán độ phủ tường: Tổng chiều ngang (thường từ 48" đến 96"), chiều cao và độ nhô ra khỏi tường (depth 7"–9").
  - Đảm bảo độ nhô không cản trở lối đi lại chính trong phòng.
* **H2: Wall Compatibility: Drywall, Wood Studs & Masonry Installation**
  - Hướng dẫn bắt ốc trực tiếp vào xương gỗ tường thạch cao (wood studs) để đạt độ vững chắc tối đa.
  - Hướng dẫn dùng nở chuyên dụng (heavy-duty toggle bolts) cho các vị trí nhánh phụ không trùng xương tường.
* **H2: Curating Your Branch Display: Books, Sculptures & Greenery**
  - Nghệ thuật sắp đặt (styling tips): Đặt sách nghiêng theo chiều dốc của nhánh cây, đan xen chậu cây rủ nhỏ và đồ gốm thủ công.
* **Quick Facts Box**:
  - *Installation Type*: Direct Wall Anchor (Floating)
  - *Projection Depth*: 7.5" – 9" from wall
  - *Recommended Wall*: Drywall with Wood/Metal Studs, Brick, or Concrete
* **Recommended FAQs**:
  - *Is it safe to install on standard drywall?*
  - *Is all mounting hardware included in the package?*
  - *Can one person install the shelf alone?*

---

### 3. Corner Tree Bookshelves (`corner-bookshelf`)
* **Vai trò**: Child Collection - Giải pháp xử lý góc phòng (Problem-solving Category).
* **Số lượng sản phẩm hiện tại**: 29 sản phẩm.
* **Primary Keyword**: `corner tree bookshelf` (Search Intent: Form / Awkward space solution).
* **Secondary Keywords**: `corner tree bookcase`, `tree corner shelf`, `corner branch bookshelf`.
* **SEO Title**: `Corner Tree Bookshelves | Handcrafted Wood | Wrydeco`
* **Meta Description**: `Transform unused corners with handcrafted tree bookshelves in wall-mounted and floor-supported designs for living rooms, nurseries and reading spaces.`

#### Cấu trúc Heading & Nội dung định hướng (450–550 words):
* **H2: Transforming Neglected Corners into Sculptural Sanctuaries**
  - Giải quyết bài toán góc chết 90 độ trong phòng khách, phòng ngủ hoặc góc đọc sách riêng tư (reading nook).
* **H2: Precision Measuring: Dual-Wall Spans & 90-Degree Geometry**
  - Cách đo chính xác cả 2 cạnh tường (Wall A và Wall B).
  - Lưu ý về phào chân tường (baseboards) và ổ cắm điện nằm ẩn trong góc.
* **H2: Floor-Supported vs. Floating Corner Engineering**
  - So sánh: Mẫu có chân đế chạm sàn (tải trọng lớn hơn, chịu sách nặng) vs. Mẫu treo tường góc (thanh thoát, nhẹ mắt).
* **H2: Child-Safe Rounded Edges for Nurseries & Family Rooms**
  - Các góc cạnh của cành cây được vát cong thủ công (hand-beveled), sơn dầu thực vật không mùi hữu cơ (zero VOC).
* **Quick Facts Box**:
  - *Angle Alignment*: True 90° Corner Fit
  - *Dual Wall Clearance*: Cần tối thiểu 24"–36" mỗi bên góc tường
  - *Safety Standard*: Child-safe rounded branch tips & anti-tip anchors
* **Recommended FAQs**:
  - *Will it fit if my corner is slightly imperfect (not exactly 90 degrees)?*
  - *How do I measure the two walls correctly?*
  - *Are corner models suitable for children's bedrooms?*

---

### 4. Rustic Tree Bookshelves (`bookshelf-rustic`)
* **Vai trò**: Style Segment - Phân khúc phong cách Rustic, Wabi-Sabi, Mộc mạc tự nhiên.
* **Số lượng sản phẩm hiện tại**: 20 sản phẩm.
* **Primary Keyword**: `rustic tree bookshelf` (Search Intent: Style/Aesthetic search).
* **Secondary Keywords**: `rustic tree bookcase`, `rustic branch bookshelf`, `natural wood tree shelf`.
* **SEO Title**: `Rustic Tree Bookshelves in Natural Wood | Wrydeco`
* **Meta Description**: `Explore rustic tree bookshelves with branch-inspired silhouettes, natural wood character and statement storage for warm, distinctive interiors.`

#### Cấu trúc Heading & Nội dung định hướng (400–500 words):
* **H2: The Organic Appeal of Visible Wood Character & Raw Edges**
  - Định nghĩa phong cách Rustic của Wrydeco: Tôn vinh các mắt gỗ tự nhiên (knots), đường nứt tự nhiên đã xử lý ổn định, và vân gỗ lượn sóng sống động.
* **H2: Organic Finishes: Matte Wax, Smoked Oak & Natural Walnut**
  - Sự khác biệt giữa sơn công nghiệp bóng loáng và lớp hoàn thiện dầu thẩm thấu sâu, giữ nguyên xúc giác gỗ ấm áp khi chạm tay.
* **H2: Harmonizing Rustic Tree Shelves with Modern & Transitional Homes**
  - Cách phối hợp đồ gỗ mộc mạc vào không gian hiện đại (Modern Rustic / Warm Minimalism) để tạo sự cân bằng thị giác hoàn hảo.
* **Quick Facts Box**:
  - *Wood Character*: Heavy grain, natural knots, subtle organic curves
  - *Finish Texture*: Low-sheen matte tactile wood feel
  - *Complementary Styles*: Modern Farmhouse, Cabin Luxe, Wabi-Sabi
* **Recommended FAQs**:
  - *Do rustic shelves have rough edges that could snag books?*
  - *How should I clean and dust natural wood textures?*

---

### 5. Tree Branch Wall Shelves & Floating Bookshelves (`floating-bookshelf`)
* **Vai trò**: Form Category - Kệ sách và kệ nhánh cây treo tường cỡ vừa và nhỏ.
* **Số lượng sản phẩm hiện tại**: 19 sản phẩm.
* **Primary Keyword**: `tree branch wall shelf` (Search Intent: Compact sculptural shelf).
* **Secondary Keywords**: `floating tree bookshelf`, `wall mounted branch bookshelf`, `sculptural wood wall shelf`.
* **SEO Title**: `Tree Branch Wall Shelves & Floating Bookshelves | Wrydeco`
* **Meta Description**: `Explore tree branch wall shelves and floating bookshelves with sculptural natural-wood forms for books, plants and collected objects.`

#### Cấu trúc Heading & Nội dung định hướng (400–500 words):
* **H2: Branch-Form Wall Accents: Combining Sculpture with Everyday Utility**
  - Dòng sản phẩm nhỏ gọn hơn kệ cây khổng lồ, phù hợp làm điểm nhấn trên bàn làm việc, đầu giường, hoặc lối vào sảnh.
* **H2: Weight Distribution Across Asymmetric Branch Structures**
  - Giải thích nguyên lý cân bằng trọng lực: Đặt các đồ vật nặng (sách bìa cứng) ở gần thân gốc, vật nhẹ (đồ decor, nến thơm) ở ngọn nhánh.
* **H2: Concealed Mounting Systems for an Effortless Floating Look**
  - Hệ thống pat sắt chịu lực âm gỗ (concealed bracketry) tạo cảm giác nhánh cây mọc tự nhiên ra từ bức tường.
* **Quick Facts Box**:
  - *Depth Profile*: 6" – 8" compact footprint
  - *Load Capacity*: 10–15 lbs per branch tier
  - *Ideal For*: Small curated collections, art ceramics, trailing plants

---

### 6. Standing Tree Bookshelves (`standing-bookshelf`)
* **Vai trò**: Form Category - Kệ cây đứng tự do có chân đế chạm sàn (Freestanding).
* **Số lượng sản phẩm hiện tại**: 13 sản phẩm.
* **Primary Keyword**: `standing tree bookshelf` (Search Intent: Floor-standing furniture).
* **Secondary Keywords**: `freestanding tree bookshelf`, `floor standing tree bookcase`.
* **SEO Title**: `Standing Tree Bookshelves | Freestanding Wood | Wrydeco`
* **Meta Description**: `Shop standing tree bookshelves and freestanding wood bookcases designed for sculptural storage without a floating wall installation.`

#### Cấu trúc Heading & Nội dung định hướng (400–500 words):
* **H2: Freestanding Freedom: Sculptural Wood Without Wall Drilling**
  - Giải pháp tối ưu cho người thuê nhà (renters) hoặc các mảng tường không thể khoan vít (tường kính, tường thạch cao yếu).
* **H2: Weighted Base Engineering & Center-of-Gravity Balance**
  - Thiết kế chân đế gỗ đặc nguyên khối nặng, hạ thấp trọng tâm giúp cây đứng vững chãi kể cả khi chất đầy sách.
* **H2: Room Placement & Safety Guidelines**
  - Vị trí đặt lý tưởng: Bên cạnh ghế tựa đọc sách (armchair), góc phòng làm việc, hoặc làm vách ngăn ước lệ trong phòng lớn.
  - Khuyến nghị an ninh: Kèm dây đai an toàn chống lật khi gia đình có trẻ nhỏ hoặc thú cưng hiếu động.
* **Quick Facts Box**:
  - *Base Design*: Heavy solid wood weighted footplate
  - *No-Mount Option*: Stands independently; optional tether included
  - *Portability*: Easy to reposition across rooms

---

### 7. Sculptural & Curved Wood Bookshelves (`bookshelf-modern`)
* **Vai trò**: Modern Design Category - Kệ sách uốn cong, vòm cong điêu khắc (phi hình cây).
* **Số lượng sản phẩm hiện tại**: 9 sản phẩm.
* **Primary Keyword**: `sculptural bookshelf` (Search Intent: High-design modern bookcase).
* **Secondary Keywords**: `curved bookshelf`, `modern wood bookcase`, `organic bookshelf`.
* **SEO Title**: `Sculptural & Curved Wood Bookshelves | Wrydeco`
* **Meta Description**: `Shop sculptural wood bookshelves with curved, arched and organic forms designed as functional display furniture for modern interiors.`

#### Cấu trúc Heading & Nội dung định hướng (400–500 words):
* **H2: Architectural Curves: Breaking the Monotony of Linear Shelving**
  - Khám phá các thiết kế kệ uốn lượn, hình vòm mềm mại, tạo dòng chảy thị giác êm ái cho không gian phòng khách hiện đại.
* **H2: Double-Sided Finishing: Functional Room Dividers**
  - Cả mặt trước và mặt sau đều được chà nhám và phủ bóng tỉ mỉ, cho phép sử dụng kệ như một vách ngăn nghệ thuật giữa phòng khách và phòng ăn.
* **H2: Displaying Art, Ceramics & Large-Format Architecture Tomes**
  - Các ô kệ được phân chia kích thước linh hoạt, phù hợp cho cả sách nghệ thuật khổ lớn (coffee table books) và tượng điêu khắc.

---

## Nhóm 2: Dòng Nội Thất Phòng Ngủ & Điêu Khắc Nghệ Thuật

### 8. Solid Wood Platform Beds & Live Edge Headboards (`bed-frame-with-headboard`)
* **Vai trò**: High-Ticket Core Category - Giường ngủ gỗ tự nhiên & Đầu giường bìa gỗ tự nhiên.
* **Số lượng sản phẩm hiện tại**: 12 sản phẩm.
* **Primary Keyword**: `solid wood platform beds` (Search Intent: Transactional high-ticket furniture).
* **Secondary Keywords**: `tree branch bed`, `wood platform bed with headboard`, `live edge wood headboard`.
* **SEO Title**: `Solid Wood Platform Beds & Headboards | Wrydeco`
* **Meta Description**: `Explore handcrafted solid wood platform beds, branch canopy beds and live edge headboards designed as distinctive bedroom centerpieces.`

#### Cấu trúc Heading & Nội dung định hướng (500–600 words):
* **H2: The Bedroom Centerpiece: Organic Form Meets Restful Stability**
  - Tầm quan trọng của một chiếc giường gỗ thịt: Sự ấm áp, vững chãi, không có tiếng cót két (noise-free solid joinery).
* **H2: Mattress Compatibility & Slat System Architecture**
  - Thiết kế giát giường thanh gỗ thông/sồi dày dặn, khoảng cách nan chuẩn 2.5–3", hỗ trợ tối ưu cho đệm Memory Foam, Hybrid và Lò xo mà **không cần hộp lò xo đệm phụ (No box spring required)**.
* **H2: Live Edge & Sculptural Branch Headboard Selection**
  - Đầu giường bìa tự nhiên (Live Edge): Mỗi tấm gỗ giữ nguyên đường cong tự nhiên của thân cây, độc nhất vô nhị trên thế giới.
* **H2: White-Glove Delivery, Weight & Precision In-Room Assembly**
  - Trọng lượng khung giường đặc (>180 lbs), hướng dẫn khớp mộng và thời gian lắp ghép khoảng 45 phút.
* **Quick Facts Box**:
  - *Standard Sizes*: Queen, King, California King
  - *Box Spring*: Not needed (solid slat foundation included)
  - *Weight Rating*: 900+ lbs static capacity
  - *Joinery*: Heavy-duty internal steel connection brackets with solid wood cladding

---

### 9. Signature Pieces (`signature-pieces`)
* **Vai trò**: Brand Curated Hub - Tuyển tập các tác phẩm nghệ thuật nội thất biểu tượng của Wrydeco.
* **Số lượng sản phẩm hiện tại**: 12 sản phẩm.
* **Primary Keyword**: `sculptural wood furniture` (Search Intent: Luxury statement & collector furniture).
* **Secondary Keywords**: `statement furniture`, `functional art furniture`, `nature inspired furniture`.
* **SEO Title**: `Signature Sculptural Wood Furniture | Wrydeco`
* **Meta Description**: `Discover Wrydeco signature furniture: sculptural bookshelves, organic tables, wood art and statement designs created for distinctive interiors.`

#### Cấu trúc Heading & Nội dung định hướng (450–550 words):
* **H2: Where Woodworking Transcends Utility into Functional Art**
  - Triết lý sáng tạo đằng sau bộ sưu tập Signature: Mỗi tác phẩm được đục đẽo, gọt giũa thủ công hàng chục giờ bởi các nghệ nhân mộc bậc thầy.
* **H2: Curated Selection: From Sculptural Bookcases to Statement Tables**
  - Hướng dẫn điều hướng: Giới thiệu các biểu tượng tiêu biểu và gắn link trực tiếp về từng danh mục tương ứng.
* **H2: Bespoke Commissions & One-of-a-Kind Collector Provenance**
  - Cam kết tính độc bản: Cung cấp chứng nhận nguồn gốc gỗ và khả năng đặt chế tác riêng theo kích thước biệt thự, penthouse.

---

### 10. Handcrafted Wooden Floor Sculptures (`wooden-floor-sculpture`)
* **Vai trò**: Decor Category - Tượng điêu khắc gỗ đứng sàn trang trí sảnh, phòng khách.
* **Số lượng sản phẩm hiện tại**: 4 sản phẩm.
* **Primary Keyword**: `wood floor sculpture` (Search Intent: Fine art wood decor).
* **Secondary Keywords**: `wooden floor sculpture`, `tall wood sculpture`, `sculptural wood decor`.
* **SEO Title**: `Wooden Floor Sculptures | Handcrafted Wood Art | Wrydeco`
* **Meta Description**: `Explore handcrafted wooden floor sculptures with organic silhouettes and open-cutout forms for living rooms, entryways and curated interiors.`

#### Cấu trúc Heading & Nội dung định hướng (400–450 words):
* **H2: Three-Dimensional Spatial Art for Grand Interiors**
  - Tác phẩm điêu khắc đứng sàn tạo tiêu điểm thị giác (focal point) cho tiền sảnh (foyer), góc thông tầng hoặc cạnh cửa kính lớn.
* **H2: Carved Silhouettes, Hollow Twists & Light-Play**
  - Kỹ thuật đục rỗng thân gỗ tạo hiệu ứng bóng đổ và ánh sáng xuyên qua đầy tính điện ảnh.
* **H2: Stability, Care & Weight Considerations**
  - Đế gỗ đúc nặng chống xô lệch, lớp sáp bảo vệ chống bám bụi và hướng dẫn vị trí tránh ánh nắng trực tiếp gay gắt.

---

### 11. Handcrafted Wood Wall Mirrors (`mirror`)
* **Vai trò**: Accent Decor Category - Gương treo tường khung gỗ tự nhiên uốn lượn.
* **Số lượng sản phẩm hiện tại**: 9 sản phẩm.
* **Primary Keyword**: `wood wall mirror` (Search Intent: Decorative artisanal mirror).
* **Secondary Keywords**: `sculptural wood mirror`, `rustic wooden wall mirror`, `organic wooden mirror`.
* **SEO Title**: `Handcrafted Wood Wall Mirrors | Sculptural Frames | Wrydeco`
* **Meta Description**: `Shop handcrafted wood wall mirrors with organic carved frames and natural timber edges to bring light, warmth and artistry to walls.`

#### Cấu trúc Heading & Nội dung định hướng (400–450 words):
* **H2: Reflecting Natural Warmth: Mirrors with Sculptural Wood Frames**
  - Gương không chỉ để soi mà là một bức tranh mở rộng không gian, phản chiếu ánh sáng tự nhiên vào sâu trong phòng.
* **H2: High-Clarity Glass & Hand-Carved Timber Edges**
  - Kính tráng bạc chất lượng cao không méo hình, kết hợp khung viền gỗ sồi/óc chó uốn lượn tự nhiên.
* **H2: Dual-Orientation Heavy-Duty French Cleat Mounting**
  - Hệ thống móc treo chữ Z âm tường (French Cleat) chịu lực, cho phép treo ngang hoặc treo dọc an toàn tuyệt đối.

---

## Nhóm 3: Dòng Bàn Gỗ Tự Nhiên & Kệ Trang Trí

### 12. Sculptural Solid Wood Coffee Tables (`coffee-tables`)
* **Vai trò**: Furniture Pillar - Bàn trà phòng khách gỗ tự nhiên dáng lượn sóng, live edge, gốc cây.
* **Số lượng sản phẩm hiện tại**: 5 sản phẩm.
* **Primary Keyword**: `solid wood coffee table` (Search Intent: Transactional living room furniture).
* **Secondary Keywords**: `sculptural coffee table`, `organic coffee table`, `live edge coffee table`.
* **SEO Title**: `Sculptural Solid Wood Coffee Tables | Wrydeco`
* **Meta Description**: `Explore sculptural solid wood coffee tables with organic waves, live edges and root-inspired bases designed as distinctive living-room centerpieces.`

#### Cấu trúc Heading & Nội dung định hướng (450–550 words):
* **H2: Anchoring the Living Space with Organic Movement**
  - Bàn trà dáng sóng lượn (wave table) hoặc dáng rễ cây tạo sự mềm mại, phá vỡ các khối vuông vức của ghế sofa.
* **H2: Proportions & Sofa Clearance Guidelines**
  - Tỷ lệ chuẩn: Chiều dài bàn nên bằng 1/2 đến 2/3 chiều dài ghế sofa; chiều cao bàn thấp hơn hoặc bằng đệm sofa 1–2 inch; chừa khoảng cách 14–18 inch để chân thoải mái.
* **H2: Heat, Spill & Daily Living Protection**
  - Lớp phủ chống thấm nước (water-resistant natural sealers) chịu được cốc cà phê nóng và dễ dàng lau sạch bằng khăn ẩm.

---

### 13. Handcrafted Solid Wood Console Tables (`console-table`)
* **Vai trò**: Furniture Category - Bàn console lối vào (entryway) và sau sofa.
* **Số lượng sản phẩm hiện tại**: 2 sản phẩm.
* **Primary Keyword**: `solid wood console table` (Search Intent: Narrow hallway / entry table).
* **Secondary Keywords**: `handcrafted console table`, `sculptural console table`, `entryway console table`.
* **SEO Title**: `Solid Wood Console Tables | Handcrafted Designs | Wrydeco`
* **Meta Description**: `Explore handcrafted solid wood console tables with sculptural forms, organic edges and natural wood grain for entryways, hallways and living spaces.`

#### Cấu trúc Heading & Nội dung định hướng (400–450 words):
* **H2: First Impressions: Sculptural Entryway & Hallway Console Tables**
  - Tạo điểm nhấn chào đón ngay cửa vào với dáng bàn thanh mảnh nhưng giàu cá tính.
* **H2: Slim Depth Profiles for High-Traffic Corridors**
  - Độ sâu bàn tối ưu (11"–14") giúp đặt vừa vặn các hành lang hẹp mà không cản trở lối đi.
* **H2: Styling Surfaces: Trays, Table Lamps & Botanical Vessels**
  - Gợi ý cách trang trí bề mặt bàn hài hòa với đèn bàn, khay đựng chìa khóa và gương treo tường phía trên.

---

### 14. Handcrafted End Tables (`end-table`)
* **Vai trò**: Accent Furniture - Bàn phụ cạnh sofa hoặc đầu giường.
* **Số lượng sản phẩm hiện tại**: 1 sản phẩm.
* **Primary Keyword**: `handcrafted end table` (Search Intent: Accent side table).
* **Secondary Keywords**: `twisted wood side table`, `sculptural end table`, `wood nightstand`.
* **SEO Title**: `Handcrafted Wooden End Tables | Wrydeco`
* **Meta Description**: `Explore handcrafted wooden end tables with organic twisted silhouettes for living room sofas, lounge chairs and bedside styling.`

#### Cấu trúc Heading & Nội dung định hướng (350–400 words):
* **H2: Organic Accents: Twisted Silhouettes & Side Table Proportions**
  - Thiết kế bàn xoắn nguyên khối (Twisted Wood) vừa làm bàn để ly nước, vừa là đôn ngồi phụ đa năng.
* **H2: Height Harmony with Lounge Seating & Mattresses**
  - Chiều cao chuẩn 20"–24" ngang tầm tay với của tay vịn sofa và nệm giường ngủ.

---

### 15. Floating Wood Shelves (`floating-shelves`)
* **Vai trò**: Shelf Parent Category - Kệ thẳng, kệ rãnh sóng (fluted) treo tường.
* **Số lượng sản phẩm hiện tại**: 6 sản phẩm.
* **Primary Keyword**: `floating wood shelves` (Search Intent: Wall storage shelves).
* **Secondary Keywords**: `solid wood floating shelves`, `modern floating wood shelf`, `live edge floating shelf`.
* **SEO Title**: `Floating Wood Shelves | Modern & Rustic Designs | Wrydeco`
* **Meta Description**: `Explore floating wood shelves in modern, rustic, fluted and sculptural designs with multiple sizes and finishes for distinctive wall displays.`

#### Cấu trúc Heading & Nội dung định hướng (400–450 words):
* **H2: Clean Wall Storage: Fluted, Straight & Live Edge Profiles**
  - Phân loại các kiểu cạnh: Kệ phay rãnh hiện đại (fluted architectural lines) vs. Kệ bìa mộc mạc (live edge).
* **H2: Choosing Length, Depth & Bracket Configurations**
  - Các kích thước phổ biến từ 24", 36" đến 48"; độ sâu 8"–10" chứa vừa sách, đĩa nhạc và đồ trang trí.
* **H2: Secure Stud-Mount Installation for Heavy Display Loads**
  - Hướng dẫn tải trọng: Đạt 40–60 lbs khi bắt trúng xương gỗ tường thạch cao.

---

## Nhóm 4: Kệ Rượu & Trang Trí Chuyên Dụng

### 16. Wall-Mounted Wood Wine Racks (`wall-mounted-wine-rack`)
* **Vai trò**: Wine Specialty Category - Kệ rượu treo tường tích hợp khe treo ly.
* **Số lượng sản phẩm hiện tại**: 4 sản phẩm.
* **Primary Keyword**: `wall mounted wood wine rack` (Search Intent: Wall wine storage & stemware display).
* **Secondary Keywords**: `wall mounted wine rack with glass holder`, `wood wine rack wall shelf`.
* **SEO Title**: `Wall-Mounted Wood Wine Racks & Glass Holders | Wrydeco`
* **Meta Description**: `Shop wall-mounted wood wine racks with integrated bottle display and stemware storage for home bars, kitchens and dining spaces.`

#### Cấu trúc Heading & Nội dung định hướng (400–450 words):
* **H2: Elevated Home Bar: Wall Wine Storage with Integrated Stemware Racks**
  - Tối ưu hóa không gian phòng ăn hoặc quầy bar gia đình: Kết hợp lưu trữ chai rượu nằm ngang và hàng rãnh treo ly chân dài bên dưới.
* **H2: Bottle Neck Angle & Cork Moisture Preservation**
  - Độ nghiêng khoa học giữ nút bần luôn ẩm, bảo quản hương vị rượu vang hảo hạng.
* **H2: Wall Anchoring for Full-Bottle Weight Security**
  - Tính toán tải trọng: 1 chai rượu vang đầy nặng khoảng 3 lbs; hướng dẫn gia cố vững chãi cho kệ chứa 6–12 chai.

---

### 17. Handcrafted Wood Wine Racks (`wine-racks`)
* **Vai trò**: Wine Parent Category - Danh mục tổng các mẫu kệ rượu (để bàn và treo tường).
* **Số lượng sản phẩm hiện tại**: 1 sản phẩm.
* **Primary Keyword**: `wood wine rack` (Search Intent: Wine rack collection).
* **Secondary Keywords**: `wooden wine rack`, `countertop wine rack`, `handmade wine holder`.
* **SEO Title**: `Wood Wine Racks | Wall & Countertop Designs | Wrydeco`
* **Meta Description**: `Explore handcrafted wood wine racks in wall-mounted and countertop designs with bottle display and integrated stemware storage options.`

#### Cấu trúc Heading & Nội dung định hướng (350–400 words):
* **H2: The Art of Wine Display: Countertop & Wall Storage Solutions**
  - Hướng dẫn chọn kệ rượu phù hợp với nhu cầu tiếp khách và quy mô bộ sưu tập rượu gia đình.
* **H2: Natural Timber Grains Complementing Fine Vintages**
  - Sự kết hợp ấm áp giữa chất gỗ sồi, óc chó với màu đỏ ngọc bích của chai vang cao cấp.

---

## Nhóm 5: Trang Điều Hướng & Danh Mục Mua Sắm Tổng Hợp

### 18. New Arrivals (`new-arrivals`)
* **Vai trò**: Merchandising Hub - Giới thiệu các mẫu thiết kế mới ra mắt định kỳ.
* **Số lượng sản phẩm hiện tại**: 8 sản phẩm.
* **Primary Keyword**: `Wrydeco new arrivals` (Search Intent: Returning visitors / Brand discovery).
* **SEO Title**: `New Handcrafted Wood Furniture | Wrydeco`
* **Meta Description**: `Explore the latest Wrydeco furniture and decor, including newly released sculptural bookshelves, tables and handcrafted wood designs.`

#### Cấu trúc Heading & Nội dung định hướng (300–350 words):
* **H2: Fresh Silhouettes from the Wrydeco Workshop**
  - Giới thiệu những thử nghiệm sáng tạo mới nhất của xưởng mộc: Đường cong mới, vân gỗ mới, tỉ lệ mới.
* **H2: Exploring by Furniture Category**
  - Các khối nút liên kết nhanh đưa khách hàng khám phá sâu vào các dòng sản phẩm trụ cột.

---

### 19. Explore All Pieces (`all`)
* **Vai trò**: Shop-All Utility Catalog - Duyệt toàn bộ danh mục sản phẩm (157 sản phẩm).
* **Primary Keyword**: `Wrydeco furniture` (Search Intent: Branded catalog browsing).
* **SEO Title**: `Shop All Handcrafted Furniture & Decor | Wrydeco`
* **Meta Description**: `Browse all Wrydeco handcrafted furniture and decor, from sculptural bookshelves and wood tables to beds, wine racks and statement pieces.`

#### Cấu trúc Heading & Nội dung định hướng (350–400 words):
* **H2: A Complete Catalogue of Organic Woodcraft**
  - Tổng quan về toàn bộ hệ sinh thái sản phẩm Wrydeco: Từ các cây sách vĩ đại đến những chiếc bàn trà uốn lượn và phụ kiện trang trí tường.
* **H2: Navigating by Material, Function & Room Space**
  - Hướng dẫn sử dụng bộ lọc thông minh (Filters) theo chủng loại sản phẩm, mức giá, kiểu dáng và chất liệu gỗ.

---

# TỔNG KẾT & BƯỚC TIẾP THEO

File đề xuất này là **kim chỉ nam nội dung và kỹ thuật** để chuẩn bị triển khai mục `[COLLECTION BUYING GUIDE / SEO CONTENT]` cho Wrydeco.

Khi bạn duyệt cấu trúc này, chúng ta sẽ bắt tay vào:
1. **Lập trình section Liquid**: `sections/collection-buying-guide.liquid` với HTML ngữ nghĩa & responsive CSS.
2. **Kích hoạt Metafield**: `custom.buying_guide` để nhập nội dung độc bản cho từng collection.
3. **Triển khai mẫu cho collection đầu tiên**: `tree-bookshelves` và kiểm thử tự động với Playwright.
