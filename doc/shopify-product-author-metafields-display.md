# Hiển thị thông tin tác giả sản phẩm từ Shopify Product Metafields

## 1. Mục tiêu

Hiển thị hồ sơ tác giả/nghệ nhân trên trang chi tiết sản phẩm Shopify, bao gồm:

- Ảnh tác giả
- Tên tác giả
- Tiểu sử ngắn

Dữ liệu được đọc trực tiếp từ **Product Metafields**, vì vậy mỗi sản phẩm có thể hiển thị một tác giả khác nhau.

---

## 2. Product Metafields cần có

Tạo ba metafield definition tại:

```text
Shopify Admin
→ Settings
→ Custom data
→ Products
```

| Tên hiển thị     | Namespace and key         | Loại dữ liệu     |
| ---------------- | ------------------------- | ---------------- |
| Author name      | `custom.author_name`      | Single line text |
| Author bio       | `custom.author_bio`       | Multi-line text  |
| Author image URL | `custom.author_image_url` | URL              |

Trong Liquid, dữ liệu được truy cập như sau:

```liquid
product.metafields.custom.author_name
product.metafields.custom.author_bio
product.metafields.custom.author_image_url
```

---

## 3. Cách triển khai được khuyên dùng

Tách phần hiển thị tác giả thành một snippet riêng để:

- Dễ tái sử dụng
- Không làm file `main-product.liquid` quá dài
- Dễ sửa bố cục về sau
- Tự động ẩn toàn bộ khối khi sản phẩm không có dữ liệu tác giả

Tạo file:

```text
snippets/product-author.liquid
```

Sau đó thêm nội dung dưới đây.

```liquid
{% comment %}
  Hiển thị thông tin tác giả của sản phẩm hiện tại.

  Product metafields:
  - custom.author_name
  - custom.author_bio
  - custom.author_image_url
{% endcomment %}

{% liquid
  assign author_name = product.metafields.custom.author_name.value
  assign author_bio = product.metafields.custom.author_bio
  assign author_image_url = product.metafields.custom.author_image_url.value
%}

{% if author_name != blank or author_bio.value != blank or author_image_url != blank %}
  <section
    class="product-author"
    aria-labelledby="product-author-title-{{ product.id }}"
  >
    {% if author_image_url != blank %}
      <div class="product-author__media">
        <img
          class="product-author__image"
          src="{{ author_image_url | escape }}"
          alt="{% if author_name != blank %}{{ author_name | escape }}{% else %}Product author{% endif %}"
          width="600"
          height="600"
          loading="lazy"
        >
      </div>
    {% endif %}

    <div class="product-author__content">
      <p class="product-author__eyebrow">
        The artisan behind this piece
      </p>

      {% if author_name != blank %}
        <h2
          id="product-author-title-{{ product.id }}"
          class="product-author__name"
        >
          {{ author_name | escape }}
        </h2>
      {% endif %}

      {% if author_bio.value != blank %}
        <div class="product-author__bio">
          {{ author_bio | metafield_tag }}
        </div>
      {% endif %}
    </div>
  </section>
{% endif %}
```

---

## 4. Gọi snippet trong trang sản phẩm

Mở section đang chịu trách nhiệm hiển thị trang chi tiết sản phẩm. Tùy theme, file thường là một trong các file sau:

```text
sections/main-product.liquid
sections/product-main.liquid
sections/product-information.liquid
```

Đặt lệnh render tại vị trí muốn hiển thị hồ sơ tác giả:

```liquid
{% render 'product-author', product: product %}
```

Ví dụ, đặt sau phần mô tả sản phẩm:

```liquid
<div class="product__description">
  {{ product.description }}
</div>

{% render 'product-author', product: product %}
```

Hoặc đặt sau toàn bộ khu vực thông tin mua hàng:

```liquid
</product-info>

{% render 'product-author', product: product %}
```

Vị trí chính xác phụ thuộc vào cấu trúc theme. Không nên đặt snippet bên trong vòng lặp variant, gallery hoặc product card.

---

## 5. Giải thích code

### 5.1. Đọc giá trị metafield

```liquid
{% liquid
  assign author_name = product.metafields.custom.author_name.value
  assign author_bio = product.metafields.custom.author_bio
  assign author_image_url = product.metafields.custom.author_image_url.value
%}
```

- `author_name` lấy giá trị chuỗi từ metafield tên tác giả.
- `author_bio` giữ nguyên đối tượng metafield để có thể dùng filter `metafield_tag`.
- `author_image_url` lấy URL ảnh tác giả dưới dạng chuỗi.

Với metafield, `.value` dùng để lấy giá trị thực:

```liquid
product.metafields.custom.author_name.value
```

Không nên chỉ in trực tiếp toàn bộ đối tượng metafield trong các phép xử lý chuỗi.

---

### 5.2. Chỉ hiển thị khi có dữ liệu

```liquid
{% if author_name != blank or author_bio.value != blank or author_image_url != blank %}
```

Điều kiện này giúp:

- Sản phẩm có author info sẽ hiển thị khối tác giả.
- Sản phẩm chưa có author info sẽ không tạo khoảng trống.
- Chỉ cần ít nhất một trong ba trường có dữ liệu là khối có thể hiển thị.

Nếu yêu cầu bắt buộc phải có tên tác giả mới hiển thị, thay điều kiện bằng:

```liquid
{% if author_name != blank %}
```

---

### 5.3. Hiển thị ảnh tác giả

```liquid
<img
  src="{{ author_image_url | escape }}"
  alt="{{ author_name | escape }}"
  width="600"
  height="600"
  loading="lazy"
>
```

Vì `custom.author_image_url` có loại dữ liệu là **URL**, giá trị của nó là một đường dẫn ảnh bên ngoài hoặc đường dẫn Shopify CDN.

Không sử dụng:

```liquid
{{ author_image_url | image_url }}
```

Filter `image_url` chỉ phù hợp với Shopify image object hoặc file reference, không dành cho một URL chuỗi thông thường.

Các thuộc tính quan trọng:

- `alt`: hỗ trợ khả năng truy cập và SEO hình ảnh.
- `width` và `height`: giúp trình duyệt giữ trước không gian, hạn chế layout shift.
- `loading="lazy"`: trì hoãn tải ảnh khi khu vực tác giả chưa xuất hiện trong viewport.

---

### 5.4. Hiển thị tên tác giả an toàn

```liquid
{{ author_name | escape }}
```

Filter `escape` chuyển các ký tự HTML đặc biệt thành dạng an toàn, tránh việc dữ liệu văn bản phá vỡ cấu trúc HTML.

---

### 5.5. Hiển thị bio

```liquid
{{ author_bio | metafield_tag }}
```

`metafield_tag` là cách được khuyên dùng để Shopify tự render metafield theo đúng loại dữ liệu.

Với `Multi-line text`, Shopify sẽ xử lý nội dung nhiều dòng phù hợp hơn so với việc in chuỗi thô.

Phương án thay thế:

```liquid
{{ author_bio.value | escape | newline_to_br }}
```

Dùng phương án này khi cần kiểm soát HTML đầu ra đơn giản hơn.

Không nên in trực tiếp nội dung không escape bằng:

```liquid
{{ author_bio.value }}
```

---

## 6. Trường hợp chỉ cần code ngắn gọn

Có thể đặt trực tiếp code dưới đây trong `main-product.liquid`:

```liquid
{% assign author_name = product.metafields.custom.author_name.value %}
{% assign author_bio = product.metafields.custom.author_bio %}
{% assign author_image_url = product.metafields.custom.author_image_url.value %}

{% if author_name != blank %}
  <div class="product-author">
    {% if author_image_url != blank %}
      <img
        src="{{ author_image_url | escape }}"
        alt="{{ author_name | escape }}"
        width="600"
        height="600"
        loading="lazy"
      >
    {% endif %}

    <div class="product-author__content">
      <h2>{{ author_name | escape }}</h2>

      {% if author_bio.value != blank %}
        {{ author_bio | metafield_tag }}
      {% endif %}
    </div>
  </div>
{% endif %}
```

Cách này phù hợp để thử nhanh. Với theme chính thức, nên dùng snippet riêng.

---

## 7. Styling

Phần styling cần tham chiếu đến **design system từ coding rules đã đọc trước đó**.

Các class đã chuẩn bị sẵn để styling:

```text
.product-author
.product-author__media
.product-author__image
.product-author__content
.product-author__eyebrow
.product-author__name
.product-author__bio
```

Không viết style inline trong Liquid:

```liquid
<div style="display: flex;">
```

Nên đặt CSS trong stylesheet phù hợp của theme.

---

## 8. Kiểm tra dữ liệu trước khi code

Mở một sản phẩm trong Shopify Admin:

```text
Products
→ Chọn sản phẩm
→ Metafields
```

Xác nhận ba trường đã có dữ liệu:

```text
Author name
Author bio
Author image URL
```

Ví dụ:

```text
Author name:
Ngoc Vo

Author bio:
Với Ngoc Vo, gỗ không chỉ là vật liệu mà còn là nơi lưu giữ
những dấu vết và ký ức của thiên nhiên...

Author image URL:
https://ashdeco.com/cdn/shop/files/Ngoc_Vo.png?v=1778150092&width=600
```

Nếu metafield không có dữ liệu, Liquid không thể hiển thị nội dung.

---

## 9. Debug metafield trong Liquid

Trong quá trình phát triển, có thể tạm thời in dữ liệu để kiểm tra:

```liquid
<pre>
  Author name: {{ product.metafields.custom.author_name.value | json }}
  Author bio: {{ product.metafields.custom.author_bio.value | json }}
  Author image: {{ product.metafields.custom.author_image_url.value | json }}
</pre>
```

Sau khi kiểm tra xong phải xóa đoạn debug này khỏi theme.

Filter `json` giúp nhìn rõ:

- Giá trị có tồn tại hay không
- Có ký tự đặc biệt hay không
- Namespace và key có được đọc đúng hay không

---

## 10. Các lỗi thường gặp

### Sai namespace hoặc key

Sai:

```liquid
product.metafields.author.author_name
```

Đúng:

```liquid
product.metafields.custom.author_name
```

Namespace và key trong Liquid phải khớp tuyệt đối với definition trong Shopify Admin.

---

### Dùng sai loại metafield ảnh

CSV đang lưu một URL ảnh, vì vậy metafield phải có loại:

```text
URL
```

Nếu metafield được tạo với loại `File`, dữ liệu và cách render sẽ khác.

---

### Không dùng `.value`

Không nên xử lý chuỗi bằng toàn bộ metafield object:

```liquid
{% assign author_name = product.metafields.custom.author_name %}
```

Nên lấy giá trị:

```liquid
{% assign author_name = product.metafields.custom.author_name.value %}
```

Riêng khi dùng `metafield_tag`, giữ nguyên object metafield:

```liquid
{% assign author_bio = product.metafields.custom.author_bio %}
{{ author_bio | metafield_tag }}
```

---

### Ảnh không hiển thị

Kiểm tra:

1. URL bắt đầu bằng `https://`.
2. URL có thể mở công khai trên trình duyệt.
3. CSV không chứa khoảng trắng thừa ở đầu hoặc cuối URL.
4. Metafield `custom.author_image_url` được tạo với loại `URL`.
5. Tên cột CSV khớp:

```text
Author image URL (product.metafields.custom.author_image_url)
```

---

## 11. Kết quả mong đợi

Khi sản phẩm có đủ dữ liệu, trang sản phẩm hiển thị:

```text
[Ảnh tác giả]

THE ARTISAN BEHIND THIS PIECE

Ngoc Vo

Với Ngoc Vo, gỗ không chỉ là vật liệu mà còn là nơi lưu giữ
những dấu vết và ký ức của thiên nhiên...
```

Mỗi sản phẩm sẽ tự động lấy đúng author info đã được lưu trong Product Metafields của chính sản phẩm đó.
