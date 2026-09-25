# Task cập nhật sản phẩm đang có sẵn trong store

> Dùng access token được mô tả trong file `./access-token.md` để truy cập vào store, sau đó bạn hãy cập nhật sản phẩm có ID là `10324646690873` theo các yêu cầu bên dưới.
> Lưu ý: Bạn phải tự làm công việc cập nhật sản phẩm chứ ko phải để cho tôi làm. Trong suốt quá trình cập nhật tuyệt đối ko được chạy script lấy access token mới, nếu access token hết hạn thì dừng toàn bộ quá trình cập nhật và báo lỗi cho tôi biết để tôi cấp lại access token mới.
> QUAN TRỌNG: Trong quá trình cập nhật, nếu có bất kỳ lỗi nào xảy ra thì dừng toàn bộ quá trình cập nhật và báo lỗi cho tôi biết.

### 1. Viết lại Product Title chuẩn SEO

Product Title gốc:

```text
Handcrafted Wooden Wall Shelf with Organic Bowl Design, Rustic Floating Display Shelf for Entryway, Living Room & Boho Home Decor (Option 2)
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
🌿 Organic bowl-shaped wall shelf – A sculptural wooden wall shelf with a softly curved tray-style surface and flowing support form, designed to add natural warmth, texture, and artistic character to your wall decor.

🪵 Natural wood grain statement piece – The rich wood tone, visible grain movement, rounded edges, and carved organic shape create a handcrafted look that feels rustic, warm, and beautifully unique.

🏡 Perfect for small-space display – Use it as an entryway shelf, living room accent shelf, bedroom wall shelf, hallway display shelf, plant shelf, candle shelf, or decorative floating shelf for cozy home styling.

✨ Functional decor with artisan appeal – The shallow bowl-style surface is ideal for displaying small vases, mini planters, candles, crystals, decorative bowls, keepsakes, keys, or seasonal accents while keeping your wall space stylish.

🧡 Great for boho, rustic & organic modern homes – Pairs beautifully with farmhouse, bohemian, Mediterranean, vintage, woodland, natural, cottage, cabin, and organic modern interiors.

🎁 Thoughtful home gift idea – A meaningful choice for housewarming gifts, weddings, new homes, apartment makeovers, entryway refreshes, or anyone who loves natural wood decor with sculptural handmade-style charm.

📦 Carefully packed for delivery – Each shelf is prepared with protective packing to help safeguard the wood surface, curved tray edge, support base, and carved details during shipping.
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
<div class="description-root"><img alt="B0H44RKD1X" src="https://via.placeholder.com/800" class="" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handcrafted-Wooden-Wall-Shelf-with-Organic-Bowl-Design-Rustic-Floating-Display-Shelf-for-Entryway-Living-Room-Boho-Home-Decor-Option-2-rich-001-270bfd11a576_e2432cf2-626b-4e23-9fad-c1.jpg?v=1790277077"> <img alt="B0H44RKD1X" src="https://via.placeholder.com/800" class="" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handcrafted-Wooden-Wall-Shelf-with-Organic-Bowl-Design-Rustic-Floating-Display-Shelf-for-Entryway-Living-Room-Boho-Home-Decor-Option-2-rich-002-eef709b4fd1b_79646392-7327-4db3-9804-af.jpg?v=1790277082"> <img alt="B0H44RKD1X" src="https://via.placeholder.com/800" class="" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handcrafted-Wooden-Wall-Shelf-with-Organic-Bowl-Design-Rustic-Floating-Display-Shelf-for-Entryway-Living-Room-Boho-Home-Decor-Option-2-rich-003-4c3598992be5_579a1070-0328-40ee-876d-a1.jpg?v=1790277086"> <img alt="B0H44RKD1X" src="https://via.placeholder.com/800" class="" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handcrafted-Wooden-Wall-Shelf-with-Organic-Bowl-Design-Rustic-Floating-Display-Shelf-for-Entryway-Living-Room-Boho-Home-Decor-Option-2-rich-004-28b8896afc39_453159c7-cec9-4f95-b0d1-01.jpg?v=1790277090"> <img alt="B0H44RKD1X" src="https://via.placeholder.com/800" class="" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handcrafted-Wooden-Wall-Shelf-with-Organic-Bowl-Design-Rustic-Floating-Display-Shelf-for-Entryway-Living-Room-Boho-Home-Decor-Option-2-rich-005-317bb3a75ae1_b3d07186-8681-4da7-b06e-da.jpg?v=1790277094"> <img alt="B0H44RKD1X" src="https://via.placeholder.com/800" class="" data-src="https://cdn.shopify.com/s/files/1/0829/7968/4580/files/Handcrafted-Wooden-Wall-Shelf-with-Organic-Bowl-Design-Rustic-Floating-Display-Shelf-for-Entryway-Living-Room-Boho-Home-Decor-Option-2-rich-006-7d4ec2eeff71_9f1b2ba7-0623-4032-8eaf-76.jpg?v=1790277098"></div>
```

- amazon_link: "https://www.amazon.com/dp/B0H82ZCNSG"
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

- Cập nhật product type cho sản phẩm là `floating-shelves`.

### 11. Cập nhật vendor

- Cập nhật vendor cho sản phẩm là `Wrydeco`.

### 12. Cập nhật tags

- Cập nhật tags cho sản phẩm là `source_amazon`.

### 13. Cập nhật handle của sản phẩm

- Handle của sản phẩm sẽ được suy ra từ `Handcrafted Wooden Wall Shelf with Organic Bowl Design, Rustic Floating Display Shelf for Entryway, Living Room & Boho Home Decor (Option 2)`, handle của sản phẩm phải được viết dưới dạng kebab-case.
