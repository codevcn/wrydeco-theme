# Task cập nhật sản phẩm đang có sẵn trong store

> Dùng `../admin/access-token.md` để truy cập vào store, sau đó cập nhật sản phẩm có ID là `8346217185337` theo các yêu cầu bên dưới.

### 1. Viết lại Product Title chuẩn SEO

Product Title gốc:

```text
Handcrafted Wooden Floor Sculpture with Twisted Open Cutout Design, Tall Rustic Wood Art Decor for Living Room, Entryway & Boho Home (Option 3)
```

- Viết lại product title gốc trên thành product title mới.
- Product title mới phải tự nhiên, rõ nghĩa, mô tả đúng sản phẩm và không chứa thông tin không có trong dữ liệu nguồn.
- Độ dài bắt buộc: **từ 50 đến 70 ký tự**, tính cả khoảng trắng.
- Ưu tiên đặt từ khóa chính gần đầu title.
- Không nhồi nhét từ khóa, không lặp từ vô nghĩa, không dùng câu quảng cáo quá mức và không tự tạo thông số kỹ thuật.

### 2. Viết lại Product Description thành HTML

Mô tả sản phẩm gốc:

```text
🪵 Handcrafted wooden floor sculpture – A tall sculptural wood decor piece featuring a flowing twisted silhouette and organic open cutouts, designed to bring warmth, movement, and artistic character to your home.

🌿 Natural wood grain statement piece – The rich wood tone, visible grain pattern, smooth curves, and polished finish create an earthy handmade look that feels elegant, rustic, and unique in any room.

🏡 Perfect for living room & entryway styling – Use it as a floor sculpture, corner accent, entryway decor, hallway statement piece, bedroom accent, office decor, or artistic display for nature-inspired interiors.

✨ Sculptural open cutout design – The curved vertical form and carved openings create visual depth and shadow, making this piece stand out as functional-style art without needing added lighting.

🎁 Beautiful home upgrade or gift – A thoughtful choice for housewarming gifts, weddings, new homes, apartment makeovers, living room refreshes, or anyone who loves handcrafted-style wooden decor.

🧡 Warm rustic, boho & organic modern style – Pairs beautifully with farmhouse, bohemian, rustic modern, Mediterranean, vintage, lodge, cabin, natural, and organic modern home decor.

📦 Carefully packed for delivery – Each wooden sculpture is prepared with protective packing to help safeguard the curved body, smooth finish, base, and carved cutout details during shipping.
```

Tham khảo cấu trúc HTML mẫu được cung cấp bên dưới để viết lại mô tả sản phẩm gốc trên.

- Cấu trúc HTML mẫu tham khảo (lưu lý là chỉ tham khảo cấu trúc, không copy nội dung, nội dung phải viết lại dựa trên mô tả sản phẩm gốc):

```html
<div
  class="dm-tabs__rte"
  style="margin:0; padding:0; background:transparent; color:#2a211b; font-family:inherit;"
>
  <div style="display:grid; gap:16px; margin:0; padding:0; background:transparent;">
    <div
      style="padding:16px 18px; border-radius:16px; background:rgba(91,50,24,0.055); border:1px solid rgba(92,58,35,0.10);"
    >
      <div
        style="margin:0 0 6px; color:#5a3218; font-size:11px; line-height:1; font-weight:600; letter-spacing:0.16em; text-transform:uppercase;"
      >
        Sculptural Tree-Inspired Storage
      </div>
      <p
        style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
      >
        Bring natural warmth and artistic character into your home with a tree branch floor shelf
        featuring flowing trunk lines, organic supports, and sculptural multi-level storage.
      </p>
    </div>
    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        01
      </span>
      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Tree Branch Statement Design
        </h3>
        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Flowing trunk lines, organic branch supports, and sculptural shelf placement create a
          nature-inspired focal point that adds rustic warmth and visual movement to the room.
        </p>
      </div>
    </div>
    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        02
      </span>
      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Rich Wood Grain Appearance
        </h3>
        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          A rich wood grain appearance, smooth rounded shelf edges, and handcrafted-style curves
          give the bookcase a warm vintage character suited to cozy and nature-inspired interiors.
        </p>
      </div>
    </div>
    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        03
      </span>
      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Multi-Level Display Storage
        </h3>
        <p
          style="margin:0 0 10px; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Multiple shelf levels provide decorative display space for arranging books, plants,
          keepsakes, and personal décor in a warm and visually balanced way.
        </p>
        <div style="display:flex; flex-wrap:wrap; gap:7px; margin:0; padding:0;">
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Books</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Plants</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Pottery</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Lanterns</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Framed Photos</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Candles</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Baskets</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.09); border:1px solid rgba(92,58,35,0.13); color:#5a3218; font-size:12px; line-height:1;"
            >Collectibles</span
          >
        </div>
      </div>
    </div>

    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        04
      </span>

      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Functional Storage With Artistic Style
        </h3>

        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Combining practical organization with decorative character, this tree bookshelf can serve
          as a bookcase, plant display shelf, rustic storage piece, or sculptural statement feature.
        </p>
      </div>
    </div>

    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        05
      </span>

      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Choose Your Finish Color
        </h3>

        <p
          style="margin:0 0 10px; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Choose from four finish colors to coordinate the bookshelf with rustic, farmhouse, boho,
          vintage, cottage, cabin, woodland, or organic-modern décor.
        </p>

        <div style="display:flex; flex-wrap:wrap; gap:7px; margin:0; padding:0;">
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Warm Wood</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Dark Warm Wood</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Cool Dark Wood</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.09); border:1px solid rgba(92,58,35,0.13); color:#5a3218; font-size:12px; line-height:1;"
            >Natural Finish</span
          >
        </div>
      </div>
    </div>

    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        06
      </span>

      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Designed for Cozy Interiors
        </h3>

        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          A warm decorative addition to living rooms, bedrooms, reading nooks, offices, cabins,
          cottages, and other welcoming spaces with rustic or nature-inspired styling.
        </p>
      </div>
    </div>

    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        07
      </span>

      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Naturally Unique Character
        </h3>

        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Each piece may vary slightly in branch curve, shelf edge, decorative leaf placement, wood
          grain, color tone, and finish appearance, giving every bookshelf its own distinctive look.
        </p>
      </div>
    </div>

    <div
      style="margin:2px 0 0; padding:13px 15px; border-radius:14px; background:rgba(91,50,24,0.06); color:rgba(42,33,27,0.72); font-size:13px; line-height:1.6; border:1px solid rgba(92,58,35,0.08);"
    >
      Books, plants, pottery, lanterns, framed photos, baskets, and other decorative objects shown
      in product photos are for presentation only unless explicitly included.
    </div>
  </div>
</div>
```

### 3. Cập nhật product media

- Xóa toàn bộ product media hiện tại đi và cập nhật product media của sản phẩm theo field product.product_images được liệt kê trong file `./config.json`.

### 4. Cập nhật product category

- Cập nhật product category cho sản phẩm là ``.

### 5. Cập nhật biến thể

- Cập nhật biến thể cho sản phẩm theo field product.variant_data được liệt kê trong file `./config.json`.
- **Lưu ý:**
  - field base_price trong file config.json sẽ được sử dụng làm giá cơ bản cho sản phẩm, field variant_data.additional_price sẽ được sử dụng để cộng thêm vào giá cơ bản để tạo ra giá cuối cùng cho biến thể.
  - tắt track quantity cho tất cả các biến thể của sản phẩm này, tức là sản phẩm này có thể được đặt mua mãi mãi.
- **Quan trọng:**
  - nếu sản phẩm đã có sẵn loại biến thể tên là "Wood Finish" thì giữ nguyên loại biến thể đó và chỉ cập nhật hoặc thêm các loại biến thể khác.
  - vì shopify chỉ cho phép tối đa 3 loại biến thể, nên **NẾU TỔNG SỐ LOẠI BIẾN THỂ TÍNH THÊM CẢ "WOOD FINISH" ĐANG CÓ SẴN VƯỢT QUÁ 3 LOẠI BIẾN THỂ THÌ HÃY DỪNG TOÀN BỘ QUÁ TRÌNH CẬP NHẬT, SAU ĐÓ BÁO CHO TÔI BIẾT**.

### 6. Cập nhật metafields

- rich_description:

```html
<div class="description-root"></div>
```

- amazon_link: "https://www.amazon.com/dp/B0H82SWT17?th=1"
- author_info: "gid://shopify/Metaobject/195647701049"
- product_material: "wood"
- seo_product_title:
  - Viết từ product title gốc thành dạng **long-tail keyword**.
  - Phải mô tả đúng loại sản phẩm, đặc điểm nổi bật, vật liệu hoặc phong cách thực tế nếu dữ liệu crawl có cung cấp.
  - Không nhồi nhét từ khóa và không thêm thông tin không có trong dữ liệu nguồn.
  - Không bắt buộc giống product title hoặc page title.
- wood_type: "wood"

### 7. Cập nhật phần hiển thị trên công cụ tìm kiếm

- tiêu đề trang:
  - Đây là tiêu đề hiển thị trên công cụ tìm kiếm.
  - Viết chuẩn SEO, tự nhiên và tập trung vào từ khóa chính.
  - Độ dài bắt buộc: **từ 50 đến 60 ký tự**, tính cả khoảng trắng.
  - Không tự động thêm tên thương hiệu nếu việc đó làm vượt giới hạn ký tự.
- mô tả meta:
  - Viết chuẩn SEO dựa trên nội dung thật của sản phẩm.
  - Độ dài bắt buộc: **từ 150 đến 160 ký tự**, tính cả khoảng trắng.
  - Mô tả rõ sản phẩm, điểm nổi bật và mục đích sử dụng chính.
  - Không nhồi nhét từ khóa, không dùng thông tin giả và không kết thúc bằng câu bị cắt dở.
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

- Cập nhật sản phẩm được đăng lên các channel bán hàng: Online Store, Point of Sale, Inbox.

### 10. Cập nhật product type

- Cập nhật product type cho sản phẩm là `wooden-floor-sculpture`.

### 11. Cập nhật vendor

- Cập nhật vendor cho sản phẩm là `Wrydeco`.

### 12. Cập nhật tags

- Cập nhật tags cho sản phẩm là `source_amazon`.
