# Task cập nhật sản phẩm đang có sẵn trong store

> Dùng `../admin/access-token.md` để truy cập vào store, sau đó cập nhật sản phẩm có ID là `8337728700473` theo các yêu cầu bên dưới.

### 1. Viết lại Product Title chuẩn SEO

Product Title gốc:

```text
Handmade Fluted Wood Floating Shelf, Solid Wood Wall Mounted Shelf with Layered Scalloped Trim, Custom Size Decorative Shelf for Plants Books Home Decor
```

- Viết lại product title gốc trên thành product title mới.
- Product title mới phải tự nhiên, rõ nghĩa, mô tả đúng sản phẩm và không chứa thông tin không có trong dữ liệu nguồn.
- Độ dài bắt buộc: **từ 50 đến 70 ký tự**, tính cả khoảng trắng.
- Ưu tiên đặt từ khóa chính gần đầu title.
- Không nhồi nhét từ khóa, không lặp từ vô nghĩa, không dùng câu quảng cáo quá mức và không tự tạo thông số kỹ thuật.

### 2. Viết lại Product Description thành HTML

Mô tả sản phẩm gốc:

```text
🪵 Handmade fluted wood design – This floating shelf features a beautiful layered scalloped trim with vertical fluted detail, giving your wall a warm, textured, and high-end decorative look.

🏡 Custom size for your space – Available in custom sizing so you can choose the right length for your wall, whether you need a small accent shelf, medium display ledge, or long statement shelf.

🌿 Perfect for plants and decor – Great for displaying potted plants, books, framed art, candles, vases, bowls, collectibles, or everyday decorative accents in a clean floating style.

✨ Solid wood wall shelf – Made with a rich natural wood appearance and visible grain detail, this shelf adds organic warmth to modern, rustic, farmhouse, boho, wabi sabi, and minimalist interiors.

🎨 Multiple finish options – Choose from Warm Wood, Dark Warm Wood, Cool Dark Wood, or Natural Finish to match your wall color, furniture, and home decor style.

🔧 Space-saving wall mounted display – Designed to mount directly on the wall, helping you decorate vertically while keeping tables, counters, and floors less cluttered.

🎁 Great gift for home decor lovers – A thoughtful choice for housewarming gifts, new apartment decor, birthdays, Mother’s Day, Christmas, or anyone who loves handmade wood shelves and cozy interior styling.
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

### 6. Cập nhật metafields

- rich_description:

```html
<div class="description-root">
  <img
    alt="g"
    src="https://images-na.ssl-images-amazon.com/images/G/01/x-locale/common/grey-pixel.gif"
    class="a-spacing-base a-lazy-loaded"
    data-src="https://m.media-amazon.com/images/S/aplus-media-library-service-media/0cc6adcb-8cd9-4302-b37c-02d4f07dbf42.__CR0,0,1594,986_PT0_SX970_V1___.png"
  />
  <img
    alt="h"
    src="https://images-na.ssl-images-amazon.com/images/G/01/x-locale/common/grey-pixel.gif"
    class="a-spacing-base a-lazy-loaded"
    data-src="https://m.media-amazon.com/images/S/aplus-media-library-service-media/292aad88-b728-42c3-b532-3410e7efaaff.__CR0,0,1594,986_PT0_SX970_V1___.png"
  />
  <img
    alt="f"
    src="https://images-na.ssl-images-amazon.com/images/G/01/x-locale/common/grey-pixel.gif"
    class="a-spacing-base a-lazy-loaded"
    data-src="https://m.media-amazon.com/images/S/aplus-media-library-service-media/26f3d2ff-f8e2-41eb-ac72-93588dcfd5c0.__CR0,0,1594,986_PT0_SX970_V1___.png"
  />
  <img
    alt="b"
    src="https://images-na.ssl-images-amazon.com/images/G/01/x-locale/common/grey-pixel.gif"
    class="a-spacing-base a-lazy-loaded"
    data-src="https://m.media-amazon.com/images/S/aplus-media-library-service-media/c80caa7b-522d-498b-bde6-f02a0e2d2e56.__CR0,0,1594,986_PT0_SX970_V1___.png"
  />
  <img
    alt="x"
    src="https://images-na.ssl-images-amazon.com/images/G/01/x-locale/common/grey-pixel.gif"
    class="a-spacing-base a-lazy-loaded"
    data-src="https://m.media-amazon.com/images/S/aplus-media-library-service-media/af46e73a-9c8b-4974-bf83-1a8541bfbe0f.__CR0,0,1594,986_PT0_SX970_V1___.png"
  />
  <img
    alt="d"
    src="https://images-na.ssl-images-amazon.com/images/G/01/x-locale/common/grey-pixel.gif"
    class="a-spacing-base a-lazy-loaded"
    data-src="https://m.media-amazon.com/images/S/aplus-media-library-service-media/929a3029-8f62-42bd-9f85-44112fcdc022.__CR0,0,1594,986_PT0_SX970_V1___.png"
  />
  <img
    alt="x"
    src="https://images-na.ssl-images-amazon.com/images/G/01/x-locale/common/grey-pixel.gif"
    class="a-spacing-base a-lazy-loaded"
    data-src="https://m.media-amazon.com/images/S/aplus-media-library-service-media/b73d21f7-2260-4c81-84c9-057834992c9a.__CR0,0,1594,986_PT0_SX970_V1___.png"
  />
</div>
```

- amazon_link: "https://www.amazon.com/dp/B0H82J4GXR?th=1"
- author_info: "gid://shopify/Metaobject/195646947385"
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

- Cập nhật product type cho sản phẩm là `floating-shelf-modern`.

### 11. Cập nhật vendor

- Cập nhật vendor cho sản phẩm là `Wrydeco`.

### 12. Cập nhật tags

- Cập nhật tags cho sản phẩm là `source_amazon`.
