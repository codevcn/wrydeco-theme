# Task cập nhật sản phẩm đang có sẵn trong store

> Dùng access token được mô tả trong file `./access-token.md` để truy cập vào store, sau đó bạn hãy cập nhật sản phẩm có ID là `10344740683833` theo các yêu cầu bên dưới.
> Lưu ý: Bạn phải tự làm công việc cập nhật sản phẩm chứ ko phải để cho tôi làm. Trong suốt quá trình cập nhật tuyệt đối ko được chạy script lấy access token mới, nếu access token hết hạn thì dừng toàn bộ quá trình cập nhật và báo lỗi cho tôi biết để tôi cấp lại access token mới.
> QUAN TRỌNG: Trong quá trình cập nhật, nếu có bất kỳ lỗi nào xảy ra thì dừng toàn bộ quá trình cập nhật và báo lỗi cho tôi biết.

### 1. Viết lại Product Title chuẩn SEO

Product Title gốc:

```text
Handmade Solid Wood Nightstand, Rustic Modern Bedside Table with 3 Storage Shelves, Wooden Bedroom Accent Furniture (Option 1)
```

- Viết lại product title gốc trên thành product title mới.
- Product title mới phải tự nhiên, rõ nghĩa, mô tả đúng sản phẩm và không chứa thông tin không có trong dữ liệu nguồn.
- Định dạng: Viết theo dạng **Title Case** (viết hoa chữ cái đầu mỗi từ chính).
- Cấu trúc câu chữ tối ưu: `[Tính từ phong cách/chế tác] + [Chất liệu] + [Kiểu dáng/hình tượng] + [Loại sản phẩm] + [Không gian/Mục đích]`.
- Độ dài bắt buộc: **từ 50 đến 70 ký tự**, tính cả khoảng trắng.
- Ưu tiên đặt từ khóa chính gần đầu title.
- Không nhồi nhét từ khóa, không lặp từ vô nghĩa, không dùng câu quảng cáo quá mức và không tự tạo thông số kỹ thuật.

### 2. Viết lại Product Description thành HTML

Mô tả sản phẩm gốc:

```text
🪵 Handmade Solid Wood Nightstand – Add warmth and natural character to your bedroom with a sculptural wooden bedside table designed with thick rounded shelves, visible wood grain, and an organic rustic-modern look.

🛏️ Practical 3-Tier Storage Design – The open shelf layout gives you space for bedtime essentials, books, candles, baskets, small plants, décor, remotes, or daily accessories while keeping your bedside area organized and easy to reach.

🎨 Choose Your Wood Finish – Available in Option 1 - Warm Wood, Option 2 - Dark Warm Wood, Option 3 - Cool Dark Wood, and Natural Finish, making it easy to match cozy, farmhouse, boho, cabin, organic modern, or minimalist bedroom décor.

📏 Two Size Options Available – Choose from 20"W x 22"H x 14"D or 24"W x 28"H x 14"D depending on your room size, bed height, and storage needs. The compact design works well beside beds, sofas, reading chairs, or lounge areas.

🏡 More Than a Bedside Table – Use it as a nightstand, end table, side table, small storage shelf, plant stand, entryway accent, or living room organizer. Its warm wood look makes it easy to style in multiple spaces.

🎁 Thoughtful Gift for Home Lovers – A beautiful housewarming, wedding, new apartment, anniversary, holiday, or birthday gift for anyone who loves natural wooden furniture, handmade-style home accents, and cozy interior styling.
```

Tham khảo cấu trúc HTML mẫu được cung cấp bên dưới để viết lại mô tả sản phẩm gốc trên.

- Cấu trúc HTML mẫu tham khảo (lưu lý là chỉ tham khảo cấu trúc, không copy nội dung, nội dung phải viết lại dựa trên mô tả sản phẩm gốc):

```html
<div class="wrydeco-product-description"> <p>The Layered Corner Tree Bookshelf for Nursery is a natural wood corner tree bookshelf defined by its layered corner canopy with closely spaced display shelves. It is intended for corner display and storage where wall span, shelf depth, and room clearance need to be checked together. Use the dimensions, finish options, and gallery to compare fit before selecting a configuration.</p> <h2>Product Details</h2> <ul> <li>
<strong>Design focus:</strong> layered corner canopy with closely spaced display shelves</li> <li>
<strong>Material and finish:</strong> The design is presented with natural wood character; review the gallery and finish options for variation in grain and tone.</li> <li>
<strong>Available sizes:</strong> 49"W x 55"H x 8"D; 60"W x 60"H x 10"D; 75"W x 69"H x 12"D; 90"W x 82"H x 12"D</li> <li>
<strong>Available finishes:</strong> Natural; Light Oak; Walnut; Dark Walnut; Custom</li> <li>
<strong>Product category:</strong> corner-bookshelf</li> <li>
<strong>Available configurations:</strong> Multiple selectable configurations are listed for this product. Confirm the final option combination before ordering.</li> </ul> <h2>Planning Your Space</h2> <p>Measure both walls of the corner, nearby trim, outlets, and walking clearance before choosing a size. Confirm whether the final placement requires wall support, anchoring, or professional installation.</p> <h2>Before You Order</h2>
<p>For final purchase decisions, confirm product-specific details such as wood species, load/weight capacity, mounting method and included hardware, production and delivery lead time, care instructions through the latest Wrydeco product information or customer support. These details should not be assumed from imagery alone.</p> </div>
```

### 3. Cập nhật product media

- Xóa toàn bộ product media hiện tại đi và cập nhật product media của sản phẩm theo field product.product_images được liệt kê trong file `./config.json`.

### 4. Cập nhật product category

- Cập nhật product category cho sản phẩm là ``.

### 5. Cập nhật biến thể

- Cập nhật biến thể cho sản phẩm theo field product.variant_data được liệt kê trong file `./config.json`.
- **Lưu ý:**
  - field base_price trong file config.json sẽ được sử dụng làm giá cơ bản cho sản phẩm, field variant_data.additional_price sẽ được sử dụng để cộng thêm vào giá cơ bản để tạo ra giá cuối cùng cho biến thể.
- **Quan trọng:**
  - tắt track quantity cho tất cả các biến thể của sản phẩm này, tức là sản phẩm này có thể được đặt mua mãi mãi.
  - nếu sản phẩm đã có sẵn loại biến thể tên là "Wood Finish" thì giữ nguyên loại biến thể đó và chỉ cập nhật hoặc thêm các loại biến thể khác.
  - vì shopify chỉ cho phép tối đa 3 loại biến thể, nên **NẾU TỔNG SỐ LOẠI BIẾN THỂ TÍNH THÊM CẢ "WOOD FINISH" ĐANG CÓ SẴN VƯỢT QUÁ 3 LOẠI BIẾN THỂ THÌ HÃY DỪNG TOÀN BỘ QUÁ TRÌNH CẬP NHẬT, SAU ĐÓ BÁO CHO TÔI BIẾT**.

### 6. Cập nhật metafields

- rich_description:

```html
<div class="description-root"><img alt="1" src="https://via.placeholder.com/800" class="" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-001-ba1f62a37c9e.jpg?v=1790876649"> <img alt="" src="https://via.placeholder.com/800" class="" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-002-36ca3716fa87.jpg?v=1790876653"> <img alt="PREAUREUM Tree Bookshelf, Large Wood Tree-Shaped Bookcase with Rustic Branch Shelves, Decorative ..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-003-7c3ae91a7544.jpg?v=1790876656"> <img alt="PREAUREUM Tree Branch Bookshelf, Handcrafted Natural Wood Wall Bookcase, Sculptural Floating Shel..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-004-9a9573ab4e29.jpg?v=1790876660"> <img alt="PREAUREUM Tree Bookshelf for Kids Room, Handmade Wooden Tree Bookcase with Storage Shelves, Nurse..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-005-2912abe96aa3.jpg?v=1790876663"> <img alt="PREAUREUM Tree Bookshelf with Branch Shelves, Wooden Standing Bookcase for Living Room, Entryway,..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-006-8999b0373958.jpg?v=1790876667"> <img alt="" src="https://via.placeholder.com/800" class="" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-007-dbbd3e59ac5e.jpg?v=1790876671"> <img alt="PREAUREUM 4 Large Tier Corner Tree Branch Floor Shelf, Solid Wood Wall Mounted Bookcase for Vinta..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-008-b3ae814ec8c8.jpg?v=1790876674"> <img alt="PREAUREUM Custom Tier Corner Tree Branch Floor Shelf, Solid Wood Wall Mounted Bookcase for Vintag..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-009-fd3383ed99fa.jpg?v=1790876678"> <img alt="PREAUREUM Tree Branch Floor Shelf Solid Wood Bookcase, Wall Mounted Vintage Bookshelf for Rustic ..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-010-e5807b0f42ce.jpg?v=1790876681"> <img alt="PREAUREUM 6 Tier Tree Branch Floor Shelf Solid Wood Bookcase, Wall Mounted Vintage Bookshelf for ..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-011-5558ac804246.jpg?v=1790876685"> <img alt="PREAUREUM Mushroom Tree Bookshelf, Wooden Nature Inspired 50&amp;#34; W x 60&amp;#34; H Fantasy Bookcase with Tie..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-012-5ea59d86f5b0.jpg?v=1790876688"> <img alt="PREAUREUM Sculptural Wooden Bookcase, Modern Organic Display Shelf with Curved Open Storage for L..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-013-62bb383b6123.jpg?v=1790876692"> <img alt="PREAUREUM Contemporary Wooden Tree Bookcase, Wall Mounted Branch Display Shelf with 8&amp;#34; D Open Sto..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-014-7551f18a3139.jpg?v=1790876696"> <img alt="PREAUREUM Rustic Tree Bookshelf, Solid Wood 70&amp;#34; H x 60&amp;#34; W Nature Inspired Bookcase with Open Shel..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-015-db61e30b12a7.jpg?v=1790876699"> <img alt="PREAUREUM Tree Branch Bookshelf, Wall Mounted Driftwood Floating Shelves, Solid Wood Bookcase for..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-016-702d12841a35.jpg?v=1790876703"> <img alt="PREAUREUM Wall Mounted Tree Bookshelf, Driftwood Branch Floating Shelves, Solid Wood Plant Displa..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-017-4ea3e13675c7.jpg?v=1790876707"> <img alt="PREAUREUM Wall Mounted Tree Bookshelf, Solid Wood Branch Floating Shelf, Rustic Driftwood Style P..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-018-5b5b42f2d2e9.jpg?v=1790876710"> <img alt="PREAUREUM Corner Tree Branch Shelf, Handcrafted Natural Wood 2 Tier Wall Shelf, Rustic Floating C..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-019-06750b2ab962.jpg?v=1790876714"> <img alt="Handcrafted Wooden Coffee Table with Sculptural Base, Rustic Modern Living Room Center Table for ..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-020-8773b4ae80a0.jpg?v=1790876717"> <img alt="Handcrafted Wooden Console Table with Branch-Inspired Base, Rustic Entryway Sofa Table for Farmho..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-021-a2e8ae12504f.jpg?v=1790876721"> <img alt="Sculptural Wooden Coffee Table with Organic Cutout Base, Rustic Modern Living Room Center Table f..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-022-f23ea00b9c62.jpg?v=1790876724"> <img alt="Natural Wood Coffee Table with Live Edge Look, Rustic Low Center Table for Living Room, Boho Farm..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-023-65151ba820e7.jpg?v=1790876728"> <img alt="PREAUREUM Wall Mounted Wine Rack, Mid Century Solid Wood Wine Holder with Glass Storage, Minimali..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-024-f40d3a30bfa6.jpg?v=1790876731"> <img alt="PREAUREUM Rustic Wine Rack for Kitchen Island, Sculptural Wooden Bottle Holder, 3-Tier Countertop..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-025-d22b1270eaf8.jpg?v=1790876735"> <img alt="PREAUREUM Handcrafted Record Player Stand, Solid Wood Turntable Cabinet with Vinyl Storage &amp;amp; Scul..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-026-376e0c7b8a9f.jpg?v=1790876739"> <img alt="PREAUREUM Organic Solid Walnut Jewelry Tree Organizer Stand, Branch Necklace Holder with Tray Bas..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-027-2171c2918438.jpg?v=1790876742"> <img alt="PREAUREUM Rustic Fireplace Mantel Shelf, Solid Wood Wall Mounted Mantel for Living Room and Famil..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-028-9c0fe49be736.jpg?v=1790876746"> <img alt="PREAUREUM Rustic Coat Rack with Shoe Shelf, 70” H x 60” W Entryway Hall Tree Organizer for Mudroo..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-029-a723cbfdf5d2.jpg?v=1790876749"> <img alt="PREAUREUM Handmade Entryway Shoe Bench Rack, Solid Wood Rustic Bench with Lower Shoe Storage Shel..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-030-398782e92466.jpg?v=1790876753"> <img alt="PREAUREUM Handcrafted Wooden Fruit Bowl with Natural Live Edge Look, Rustic Decorative Serving Bo..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-031-a036c56df92d.jpg?v=1790876756"> <img alt="PREAUREUM Handcrafted Wooden Lamp Base with Sculptural Cutout Design, Replacement Floor Lamp Stan..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-032-a87982751032.jpg?v=1790876760"> <img alt="PREAUREUM Black Wooden Lamp Base with Sculptural Crescent Design, Handcrafted Table Lamp Stand Ba..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-033-00d13f22c5c3.jpg?v=1790876764"> <img alt="PREAUREUM Wood Floor Lamp Base Only, Sculptural Driftwood Standing Light Base, Rustic Boho Coasta..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-034-b817b0fa40f6.jpg?v=1790876767"> <img alt="PREAUREUM Driftwood Wall Decorative Sculptural Wood Light Cover, Rustic Coastal Boho Wall Decor f..." src="https://via.placeholder.com/800" class="apm-brand-story-image-img" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handmade-Solid-Wood-Nightstand-Rustic-Modern-Bedside-Table-with-3-Storage-Shelves-Wooden-Bedroom-Accent-Furniture-Option-1-rich-035-75845d6b2b61.jpg?v=1790876770"></div>
```

- amazon_link: "https://www.amazon.com/dp/B0H5PWM7CB"
- author_info: "gid://shopify/Metaobject/195646947385"
- product_material: "wood"
- seo_product_title:
  - Viết từ product title gốc thành dạng cụm từ khóa mở rộng (**long-tail keyword**).
  - Định dạng: Viết theo dạng **Title Case** (viết hoa chữ cái đầu mỗi từ chính).
  - Độ dài tối ưu: **từ 50 đến 70 ký tự**.
  - Tuyệt đối **không chứa tên thương hiệu** (không thêm `| Wrydeco`), không dùng dấu gạch đứng `|` hay dấu gạch ngang `-` để ngắt từ.
  - Phải mô tả đúng loại sản phẩm, đặc điểm nổi bật, vật liệu hoặc phong cách thực tế nếu dữ liệu crawl có cung cấp (ví dụ: `Large Handcrafted Tree Branch Corner Bookshelf Natural Wood`).
  - Không nhồi nhét từ khóa và không thêm thông tin không có trong dữ liệu nguồn.
  - Không bắt buộc giống product title hoặc page title.
- wood_type: "wood"

### 7. Cập nhật phần hiển thị trên công cụ tìm kiếm

- tiêu đề trang:
  - Đây là tiêu đề hiển thị trên công cụ tìm kiếm (SEO Title).
  - Viết chuẩn SEO, tự nhiên và đặt từ khóa chính ngay đầu tiêu đề.
  - Cấu trúc bắt buộc: `[Tiêu đề chính cô đọng] | Wrydeco` (hậu tố ` | Wrydeco` chiếm 10 ký tự).
  - Độ dài bắt buộc: **từ 50 đến 60 ký tự**, tính cả khoảng trắng và hậu tố ` | Wrydeco` (chủ động viết tiêu đề chính khoảng 40 đến 50 ký tự để khi ghép thêm tên thương hiệu sẽ đạt đúng số ký tự quy định).
- mô tả meta:
  - Viết chuẩn SEO dựa trên nội dung thật của sản phẩm (SEO Description).
  - Cấu trúc mở đầu chuẩn mực: Luôn bắt đầu bằng cụm `Explore the [Product Title] by Wrydeco...` (hoặc `Shop the [Product Title] by Wrydeco...`).
  - Nội dung tiếp theo: Nêu ngắn gọn công năng/đặc điểm nổi bật, chất liệu gỗ, các tùy chọn kích thước và màu hoàn thiện (ví dụ: `, with branch-style storage, size options and wood finishes.` hoặc `. Compare available sizes, wood finishes, and product imagery.`).
  - Độ dài bắt buộc: **từ 150 đến 160 ký tự**, tính cả khoảng trắng.
  - Không nhồi nhét từ khóa, không dùng thông tin giả, câu văn hoàn chỉnh và luôn kết thúc bằng dấu chấm `.`, không kết thúc bằng câu bị cắt dở.
- tên định danh URL
  - Viết dưới dạng URL slug chuẩn SEO.
  - Độ dài bắt buộc: **từ 50 đến 60 ký tự**, tính cả dấu gạch nối.
  - Chỉ sử dụng chữ thường ASCII, chữ số và dấu gạch nối `-`.
  - Không dấu tiếng Việt, không khoảng trắng, không ký tự đặc biệt.
  - Không bắt đầu hoặc kết thúc bằng dấu gạch nối.
  - Không có hai dấu gạch nối liên tiếp.
  - Ưu tiên từ khóa mô tả đúng sản phẩm và tránh các từ không mang giá trị SEO.

### 8. Cập nhật trạng thái hiển thị sản phẩm

- Cập nhật trạng thái hiển thị sản phẩm là **active**.

### 9. Cập nhật đăng lên các channel bán hàng

- Cập nhật sản phẩm phải được đăng lên các channel bán hàng (bật các channel): Online Store, Point of Sale, Inbox.

### 10. Cập nhật product type

- Cập nhật product type cho sản phẩm là `bedside-table`.

### 11. Cập nhật vendor

- Cập nhật vendor cho sản phẩm là `Wrydeco`.

### 12. Cập nhật tags

- Cập nhật tags cho sản phẩm là `source_amazon`.

### 13. Cập nhật handle của sản phẩm

- Handle của sản phẩm sẽ được suy ra từ `Handmade Solid Wood Nightstand, Rustic Modern Bedside Table with 3 Storage Shelves, Wooden Bedroom Accent Furniture (Option 1)`, handle của sản phẩm phải được viết dưới dạng kebab-case.
