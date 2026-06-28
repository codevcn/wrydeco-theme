# Hướng dẫn dùng Product Author Metaobject Reference trong Shopify Liquid

## 1. Quy tắc bắt buộc

Thông tin tác giả của sản phẩm chỉ được lấy từ metafield tham chiếu mới:

```liquid
product.metafields.custom.author_info
```

Metafield này có kiểu:

```text
list.metaobject_reference
```

và tham chiếu đến entry thuộc metaobject `Product Author`.

> **BẮT BUỘC:** Tuyệt đối không đọc, fallback, khôi phục hoặc tái sử dụng ba product metafield tác giả cũ:
>
> - `custom.author_name`
> - `custom.author_bio`
> - `custom.author_image_url`

Kể cả khi `custom.author_info` không tồn tại, đang trống, tham chiếu lỗi hoặc metaobject không thể truy cập từ storefront, code **không được** quay lại lấy dữ liệu từ ba metafield cũ.

Trong mọi trường hợp không lấy được tác giả từ metaobject reference mới, storefront phải hiển thị:

```text
Chưa có thông tin tác giả cho sản phẩm này
```

---

## 2. Cấu trúc dữ liệu mới

```text
Product
└── product.metafields.custom.author_info
    └── Product Author metaobject entry
        ├── author_name
        ├── author_bio
        └── author_image_url
```

Cấu hình hiện tại:

```text
Product metafield
- Name: Author Info
- Namespace and key: custom.author_info
- Type: List of Product Author references

Metaobject definition
- Type: product_author
- Fields:
  - author_name
  - author_bio
  - author_image_url
```

Mỗi sản phẩm hiện chỉ có một tác giả, nhưng `custom.author_info` là một danh sách tham chiếu. Vì vậy, Liquid phải resolve danh sách bằng `.value` và lấy entry đầu tiên bằng `.first`.

---

## 3. Cách lấy metaobject entry đúng chuẩn

```liquid
{% assign author = product.metafields.custom.author_info.value | first %}
```

Ý nghĩa:

```text
product.metafields.custom.author_info
```

Lấy metafield `Author Info` của sản phẩm.

```text
.value
```

Resolve metafield reference thành danh sách metaobject entry.

```text
.first
```

Lấy entry đầu tiên vì mỗi sản phẩm chỉ sử dụng một tác giả.

```liquid
{% assign author_name = author.author_name.value %}
{% assign author_bio = author.author_bio.value %}
{% assign author_image_url = author.author_image_url.value %}
```

Không cần và không nên truy vấn lại metaobject bằng handle:

```liquid
metaobjects.product_author[handle]
```

Product metafield đã tham chiếu trực tiếp đến đúng entry.

---

## 4. Mẫu Liquid bắt buộc

Đoạn dưới đây:

- Chỉ đọc `custom.author_info`.
- Không dùng bất kỳ fallback nào.
- Kiểm tra reference và dữ liệu trong entry.
- Hiển thị thông báo khi không lấy được thông tin tác giả.

```liquid
{% liquid
  assign author = blank
  assign author_name = blank
  assign author_bio = blank
  assign author_image_url = blank
  assign has_author_info = false

  if product != blank
    assign author = product.metafields.custom.author_info.value | first
  endif

  if author != blank
    assign author_name = author.author_name.value
    assign author_bio = author.author_bio.value
    assign author_image_url = author.author_image_url.value

    if author_name != blank or author_bio != blank or author_image_url != blank
      assign has_author_info = true
    endif
  endif
%}

{% if has_author_info %}
  <div class="product-author" data-product-author>
    {% if author_image_url != blank %}
      <div class="product-author__image-wrapper">
        <img
          class="product-author__image"
          src="{{ author_image_url | escape }}"
          alt="{{ author_name | default: 'Product author' | escape }}"
          width="600"
          height="600"
          loading="lazy"
        >
      </div>
    {% endif %}

    <div class="product-author__content">
      {% if author_name != blank %}
        <h3 class="product-author__name">
          {{ author_name | escape }}
        </h3>
      {% endif %}

      {% if author_bio != blank %}
        <div class="product-author__bio">
          {{ author_bio | escape | newline_to_br }}
        </div>
      {% endif %}
    </div>
  </div>
{% else %}
  <p class="product-author__empty" data-product-author-empty>
    Chưa có thông tin tác giả cho sản phẩm này
  </p>
{% endif %}
```

Phần styling phải tham chiếu đến design system và coding rules hiện có của project.

---

## 5. Snippet được khuyến nghị

Tạo file:

```text
snippets/product-author.liquid
```

Nội dung:

```liquid
{% comment %}
  Renders the product author from the new metaobject reference only.

  Required source:
  product.metafields.custom.author_info

  Expected metafield type:
  list.metaobject_reference

  Expected Product Author fields:
  - author_name
  - author_bio
  - author_image_url

  Important:
  - Do not use legacy product author metafields.
  - Do not implement a legacy fallback.
  - Show an empty-state message when the reference cannot be resolved.

  Usage:
  {% render 'product-author', product: product %}
{% endcomment %}

{% liquid
  assign author = blank
  assign author_name = blank
  assign author_bio = blank
  assign author_image_url = blank
  assign has_author_info = false

  if product != blank
    assign author = product.metafields.custom.author_info.value | first
  endif

  if author != blank
    assign author_name = author.author_name.value
    assign author_bio = author.author_bio.value
    assign author_image_url = author.author_image_url.value

    if author_name != blank or author_bio != blank or author_image_url != blank
      assign has_author_info = true
    endif
  endif
%}

{% if has_author_info %}
  <div class="product-author" data-product-author>
    {% if author_image_url != blank %}
      <div class="product-author__image-wrapper">
        <img
          class="product-author__image"
          src="{{ author_image_url | escape }}"
          alt="{{ author_name | default: 'Product author' | escape }}"
          width="600"
          height="600"
          loading="lazy"
        >
      </div>
    {% endif %}

    <div class="product-author__content">
      {% if author_name != blank %}
        <h3 class="product-author__name">
          {{ author_name | escape }}
        </h3>
      {% endif %}

      {% if author_bio != blank %}
        <div class="product-author__bio">
          {{ author_bio | escape | newline_to_br }}
        </div>
      {% endif %}
    </div>
  </div>
{% else %}
  <p class="product-author__empty" data-product-author-empty>
    Chưa có thông tin tác giả cho sản phẩm này
  </p>
{% endif %}
```

Gọi snippet:

```liquid
{% render 'product-author', product: product %}
```

Ví dụ đặt dưới mô tả sản phẩm:

```liquid
<div class="product__description">
  {{ product.description }}
</div>

{% render 'product-author', product: product %}
```

---

## 6. Dùng trong block của product section

Ví dụ schema:

```json
{
  "type": "product_author",
  "name": "Product author",
  "limit": 1,
  "settings": []
}
```

Trong vòng lặp block:

```liquid
{% case block.type %}
  {% when 'title' %}
    <!-- Product title -->

  {% when 'price' %}
    <!-- Product price -->

  {% when 'product_author' %}
    <div {{ block.shopify_attributes }}>
      {% render 'product-author', product: product %}
    </div>
{% endcase %}
```

Phải giữ `block.shopify_attributes` để block hoạt động đúng trong Shopify Theme Editor.

---

## 7. Trạng thái không có tác giả

Thông báo phải xuất hiện trong các trường hợp sau:

1. Biến `product` không tồn tại.
2. `product.metafields.custom.author_info` chưa được gán.
3. Danh sách reference đang trống.
4. Entry được tham chiếu đã bị xóa hoặc không còn hợp lệ.
5. Metaobject không được cấp quyền truy cập storefront.
6. Entry tồn tại nhưng cả ba field đều trống.
7. CSV import sai handle hoặc reference không resolve được.

Thông báo chuẩn:

```liquid
<p class="product-author__empty" data-product-author-empty>
  Chưa có thông tin tác giả cho sản phẩm này
</p>
```

Không được để vùng tác giả biến mất hoàn toàn và không được âm thầm đọc dữ liệu cũ.

---

## 8. Nhiều tác giả trong tương lai

Hiện tại chỉ dùng entry đầu tiên:

```liquid
{% assign author = product.metafields.custom.author_info.value | first %}
```

Nếu sau này một sản phẩm thực sự có nhiều tác giả, có thể lặp qua danh sách mới:

```liquid
{% assign authors = product.metafields.custom.author_info.value %}

{% if authors != blank and authors.count > 0 %}
  <div class="product-authors">
    {% for author in authors %}
      {% assign author_name = author.author_name.value %}
      {% assign author_bio = author.author_bio.value %}
      {% assign author_image_url = author.author_image_url.value %}

      <article class="product-author">
        {% if author_image_url != blank %}
          <img
            src="{{ author_image_url | escape }}"
            alt="{{ author_name | default: 'Product author' | escape }}"
            width="600"
            height="600"
            loading="lazy"
          >
        {% endif %}

        {% if author_name != blank %}
          <h3>{{ author_name | escape }}</h3>
        {% endif %}

        {% if author_bio != blank %}
          <div>{{ author_bio | escape | newline_to_br }}</div>
        {% endif %}
      </article>
    {% endfor %}
  </div>
{% else %}
  <p class="product-author__empty" data-product-author-empty>
    Chưa có thông tin tác giả cho sản phẩm này
  </p>
{% endif %}
```

Với yêu cầu hiện tại, chưa cần dùng phiên bản này.

---

## 9. Nếu đổi ảnh sang File reference

Hiện tại `author_image_url` là text chứa URL, do đó phải dùng thẻ `<img>`:

```liquid
<img src="{{ author.author_image_url.value | escape }}">
```

Không dùng `image_url` filter cho chuỗi URL:

```liquid
{{ author.author_image_url.value | image_url }}
```

Nếu sau này field được đổi thành:

```text
author_image
Type: File reference
Accepted file: Image
```

thì dùng:

```liquid
{% assign author_image = author.author_image.value %}

{% if author_image != blank %}
  {{
    author_image
    | image_url: width: 800
    | image_tag:
      class: 'product-author__image',
      widths: '200, 300, 400, 600, 800',
      sizes: '(min-width: 750px) 300px, 160px',
      loading: 'lazy',
      alt: author.author_name.value
  }}
{% endif %}
```

Việc đổi kiểu field ảnh không thay đổi quy tắc chính: tác giả vẫn phải được lấy từ `custom.author_info`.

---

## 10. Debug trong Theme Editor

Có thể tạm thời thêm:

```liquid
{% if request.design_mode %}
  {% assign debug_author = product.metafields.custom.author_info.value | first %}

  <pre>
    Metafield type: {{ product.metafields.custom.author_info.type }}
    Is list: {{ product.metafields.custom.author_info.list? }}
    Reference count: {{ product.metafields.custom.author_info.value.count }}
    Author exists: {% if debug_author != blank %}yes{% else %}no{% endif %}
  </pre>
{% endif %}
```

Kỳ vọng:

```text
Metafield type: list.metaobject_reference
Is list: true
Reference count: 1
Author exists: yes
```

Xóa code debug trước khi publish theme.

---

## 11. Những cách tuyệt đối không được dùng

### Không đọc ba product metafield cũ

Cấm dùng trong bất kỳ section, snippet hoặc block nào:

```text
product.metafields.custom.author_name
product.metafields.custom.author_bio
product.metafields.custom.author_image_url
```

Ba key trên chỉ là cấu trúc dữ liệu cũ và phải được loại bỏ khỏi code Liquid.

### Không tạo fallback về dữ liệu cũ

Không được áp dụng logic:

```text
Nếu custom.author_info trống
→ đọc author_name, author_bio hoặc author_image_url cũ
```

Cách xử lý duy nhất khi `custom.author_info` không resolve được là hiển thị:

```text
Chưa có thông tin tác giả cho sản phẩm này
```

### Không truy vấn lại bằng display name

Không dùng tên tác giả để tìm metaobject entry. Tên hiển thị có thể thay đổi và không phải khóa tham chiếu an toàn.

### Không bỏ `.value.first`

`custom.author_info` là một metafield dạng danh sách. Phải resolve đúng:

```liquid
{% assign author = product.metafields.custom.author_info.value | first %}
```

---

## 12. Các lỗi thường gặp

### In metafield trực tiếp

Không đúng:

```liquid
{{ product.metafields.custom.author_info }}
```

Đúng:

```liquid
{% assign author = product.metafields.custom.author_info.value | first %}
```

### Quên `.value`

Không đúng:

```liquid
{% assign author = product.metafields.custom.author_info.first %}
```

Đúng:

```liquid
{% assign author = product.metafields.custom.author_info.value | first %}
```

### Quên `.first`

Không đúng:

```liquid
{% assign author = product.metafields.custom.author_info.value %}
{{ author.author_name.value }}
```

`author` ở trên là danh sách, không phải một metaobject entry.

Đúng:

```liquid
{% assign author = product.metafields.custom.author_info.value | first %}
```

### Metaobject không có quyền storefront

Kiểm tra:

```text
Settings
→ Custom data
→ Metaobjects
→ Product Author
→ Access
→ Storefronts
```

### Sản phẩm chưa được gắn entry

Kiểm tra:

```text
Products
→ mở sản phẩm
→ Metafields
→ Author Info
```

Field phải chứa đúng một `Product Author` entry.

---

## 13. Checklist migration bắt buộc

- [ ] Tìm toàn bộ chỗ đang đọc dữ liệu tác giả cũ.
- [ ] Xóa hoàn toàn logic dùng `custom.author_name`.
- [ ] Xóa hoàn toàn logic dùng `custom.author_bio`.
- [ ] Xóa hoàn toàn logic dùng `custom.author_image_url`.
- [ ] Không giữ fallback tạm thời.
- [ ] Cấm dùng `product.metafields.custom.author_info.value.first`.
- [ ] Chỉ dùng `product.metafields.custom.author_info.value | first`.
- [ ] Đọc field qua `author.<field_key>.value`.
- [ ] Kiểm tra `author != blank`.
- [ ] Kiểm tra entry có ít nhất một field không trống.
- [ ] Hiển thị thông báo khi không có dữ liệu.
- [ ] Tách phần render thành `snippets/product-author.liquid`.
- [ ] Kiểm tra sản phẩm của Ngoc Vo.
- [ ] Kiểm tra sản phẩm của Kiet Phac.
- [ ] Kiểm tra sản phẩm của Alex Nguyen.
- [ ] Kiểm tra một sản phẩm chưa có reference.
- [ ] Kiểm tra reference trỏ đến entry không hợp lệ.
- [ ] Kiểm tra quyền truy cập storefront của metaobject.
- [ ] Kiểm tra mobile, tablet và desktop.
- [ ] Xóa code debug trước khi publish.

---

## 14. Mẫu cuối cùng được khuyến nghị

```liquid
{% comment %}
  Product author from metaobject reference only.
  No legacy metafield fallback is allowed.
{% endcomment %}

{% liquid
  assign author = product.metafields.custom.author_info.value | first
  assign has_author_info = false

  if author != blank
    assign author_name = author.author_name.value
    assign author_bio = author.author_bio.value
    assign author_image_url = author.author_image_url.value

    if author_name != blank or author_bio != blank or author_image_url != blank
      assign has_author_info = true
    endif
  endif
%}

{% if has_author_info %}
  <div class="product-author" data-product-author>
    {% if author_image_url != blank %}
      <img
        class="product-author__image"
        src="{{ author_image_url | escape }}"
        alt="{{ author_name | default: 'Product author' | escape }}"
        width="600"
        height="600"
        loading="lazy"
      >
    {% endif %}

    <div class="product-author__content">
      {% if author_name != blank %}
        <h3 class="product-author__name">
          {{ author_name | escape }}
        </h3>
      {% endif %}

      {% if author_bio != blank %}
        <div class="product-author__bio">
          {{ author_bio | escape | newline_to_br }}
        </div>
      {% endif %}
    </div>
  </div>
{% else %}
  <p class="product-author__empty" data-product-author-empty>
    Chưa có thông tin tác giả cho sản phẩm này
  </p>
{% endif %}
```

Gọi snippet tại nơi cần hiển thị:

```liquid
{% render 'product-author', product: product %}
```

Đây là cấu trúc duy nhất được chấp nhận cho phần tác giả trong theme.

---

## Tài liệu Shopify chính thức

- Liquid `metafield` object: https://shopify.dev/docs/api/liquid/objects/metafield
- Liquid `metaobject` object: https://shopify.dev/docs/api/liquid/objects/metaobject
- Referencing metaobjects: https://help.shopify.com/en/manual/custom-data/metaobjects/referencing-metaobjects
- Connecting and displaying metaobjects: https://help.shopify.com/en/manual/custom-data/metaobjects/connecting-to-your-online-store/connecting-metaobjects
