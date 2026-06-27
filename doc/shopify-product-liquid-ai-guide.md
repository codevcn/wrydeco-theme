# Shopify Product Rendering Rules for AI Coding Agent

> Mục tiêu: hướng dẫn AI hiển thị dữ liệu sản phẩm Shopify đúng cách bằng Liquid trong theme Online Store 2.0.  
> Ưu tiên: đúng variant, đúng giá, đúng form, dễ tái sử dụng, không dùng API/filter lỗi thời.

---

## 1. Quy tắc cốt lõi

### Phân biệt `product` và `variant`

Dùng `product` cho thông tin chung:

```liquid
product.title
product.vendor
product.type
product.description
product.media
product.metafields
product.url
```

Dùng variant hiện tại cho thông tin thay đổi theo lựa chọn:

```liquid
current_variant.id
current_variant.price
current_variant.compare_at_price
current_variant.available
current_variant.sku
current_variant.barcode
current_variant.featured_media
current_variant.unit_price
current_variant.weight
```

Trên product page, luôn xác định variant trước:

```liquid
{% liquid
  assign current_variant = product.selected_or_first_available_variant

  if current_variant == blank
    assign current_variant = product.first_available_variant
  endif

  if current_variant == blank
    assign current_variant = product.variants.first
  endif
%}
```

Không dùng `product.price` hoặc `product.available` để đại diện cho variant đang chọn.

---

## 2. Cấu trúc theme đề xuất

```text
templates/product.json
sections/main-product.liquid
snippets/product-price.liquid
snippets/product-media.liquid
snippets/product-card.liquid
assets/product.js
```

Luồng:

```text
product.json
  → main-product.liquid
    → snippets
      → product.js cập nhật khi đổi variant
```

Snippet phải nhận biến rõ ràng:

```liquid
{% render 'product-card', card_product: product %}
```

Không phụ thuộc ngầm vào biến bên ngoài snippet.

---

## 3. Hiển thị dữ liệu cơ bản

```liquid
<h1>{{ product.title | escape }}</h1>

{% if product.vendor != blank %}
  <p>{{ product.vendor | escape }}</p>
{% endif %}

{% if product.description != blank %}
  <div class="rte">
    {{ product.description }}
  </div>
{% endif %}
```

Quy tắc:

- Text thuần dùng `escape`.
- `product.description` là HTML, không dùng `escape`.
- Không bọc description trong `<p>`.
- Dùng `product.url`, không tự ghép URL từ handle.

```liquid
<a href="{{ product.url }}">
  {{ product.title | escape }}
</a>
```

---

## 4. Hiển thị giá

Luôn dùng filter `money`:

```liquid
{{ current_variant.price | money }}
```

Hiển thị sale đúng điều kiện:

```liquid
{% assign is_on_sale = false %}

{% if current_variant.compare_at_price > current_variant.price %}
  {% assign is_on_sale = true %}
{% endif %}

<div class="price">
  {% if is_on_sale %}
    <s>{{ current_variant.compare_at_price | money }}</s>
  {% endif %}

  <span>{{ current_variant.price | money }}</span>
</div>
```

Không dùng:

```liquid
{% if current_variant.compare_at_price %}
```

Trên product card:

```liquid
{% if card_product.price_varies %}
  From {{ card_product.price_min | money }}
{% else %}
  {{ card_product.price | money }}
{% endif %}
```

Không tự format tiền bằng JavaScript như:

```javascript
"$" + (price / 100).toFixed(2);
```

Với Shopify Markets hoặc nhiều currency, ưu tiên HTML giá do Shopify render từ server.

---

## 5. Availability và nút mua

Trên product page:

```liquid
{% if current_variant.available %}
  In stock
{% else %}
  Sold out
{% endif %}
```

Nút:

```liquid
<button
  type="submit"
  name="add"
  {% unless current_variant.available %}disabled{% endunless %}
>
  {% if current_variant.available %}
    Add to cart
  {% else %}
    Sold out
  {% endif %}
</button>
```

Trên product card có thể dùng:

```liquid
{% unless card_product.available %}
  <span>Sold out</span>
{% endunless %}
```

Không chỉ ẩn nút bằng CSS. Phải dùng `disabled`.

---

## 6. Product form

Form phải gửi variant ID, không phải product ID.

Đúng:

```liquid
{% form 'product', product %}
  <input
    type="hidden"
    name="id"
    value="{{ current_variant.id }}"
  >

  <input
    type="number"
    name="quantity"
    min="1"
    step="1"
    value="1"
  >

  <button
    type="submit"
    name="add"
    {% unless current_variant.available %}disabled{% endunless %}
  >
    Add to cart
  </button>
{% endform %}
```

Sai:

```liquid
<input name="id" value="{{ product.id }}">
```

Có thể thêm line item property trong form:

```liquid
<input
  type="text"
  name="properties[Monogram]"
>
```

Dynamic checkout phải nằm trong product form:

```liquid
{{ form | payment_button }}
```

---

## 7. Variant selector

### Cách đơn giản: dropdown variant

```liquid
<select name="id" data-variant-select>
  {% for variant in product.variants %}
    <option
      value="{{ variant.id }}"
      {% if variant.id == current_variant.id %}selected{% endif %}
      {% unless variant.available %}disabled{% endunless %}
    >
      {{ variant.title | escape }}
      — {{ variant.price | money }}
    </option>
  {% endfor %}
</select>
```

### Với option picker riêng

Render bằng:

```liquid
{% for option in product.options_with_values %}
  ...
{% endfor %}
```

Sau khi khách đổi option, JavaScript phải cập nhật ít nhất:

1. Variant ID.
2. Price.
3. Compare-at price.
4. Availability.
5. Add-to-cart button.
6. SKU.
7. Featured media.
8. Unit price.
9. URL `?variant=...`.

Liquid chỉ render trạng thái ban đầu. Liquid không tự cập nhật sau khi trang đã tải.

---

## 8. Media

Dùng `product.media`, không chỉ dùng `product.images`.

```liquid
{% for media in product.media %}
  {% case media.media_type %}
    {% when 'image' %}
      {{ media
        | image_url: width: 1600
        | image_tag:
          widths: '400, 600, 800, 1200, 1600',
          sizes: '(min-width: 990px) 50vw, 100vw',
          loading: 'lazy'
      }}

    {% when 'video' %}
      {{ media | video_tag: controls: true }}

    {% when 'external_video' %}
      {{ media | external_video_tag }}

    {% when 'model' %}
      {{ media | model_viewer_tag }}

    {% else %}
      {{ media | media_tag }}
  {% endcase %}
{% endfor %}
```

Ảnh chính đầu tiên:

```liquid
loading: 'eager',
fetchpriority: 'high'
```

Các ảnh sau:

```liquid
loading: 'lazy'
```

Không dùng filter cũ:

```liquid
img_url
img_tag
```

Dùng:

```liquid
image_url
image_tag
```

Media theo variant:

```liquid
{% assign active_media = current_variant.featured_media
  | default: product.featured_media
%}
```

---

## 9. Metafield

Truy cập:

```liquid
product.metafields.namespace.key
```

Luôn kiểm tra `blank`.

Text:

```liquid
{% assign material = product.metafields.custom.material %}

{% if material != blank %}
  <p>{{ material.value | escape }}</p>
{% endif %}
```

Rich text:

```liquid
{% assign details = product.metafields.custom.details %}

{% if details != blank %}
  {{ details | metafield_tag }}
{% endif %}
```

Product reference:

```liquid
{% assign related_product =
  product.metafields.custom.related_product.value
%}

{% if related_product != blank %}
  {% render 'product-card',
    card_product: related_product
  %}
{% endif %}
```

Liquid chỉ đọc metafield. Liquid không tạo metafield.

---

## 10. SKU, unit price và weight

```liquid
{% if current_variant.sku != blank %}
  <p>SKU: {{ current_variant.sku | escape }}</p>
{% endif %}
```

```liquid
{% if current_variant.unit_price_measurement %}
  {{ current_variant | unit_price_with_measurement }}
{% endif %}
```

```liquid
{% if current_variant.weight > 0 %}
  {{ current_variant.weight | weight_with_unit }}
{% endif %}
```

Các giá trị này phải cập nhật khi đổi variant.

---

## 11. Product card

Mẫu tối thiểu:

```liquid
{% if card_product != blank %}
  <article class="product-card">
    <a href="{{ card_product.url }}">
      {% if card_product.featured_media != blank %}
        {{ card_product.featured_media.preview_image
          | image_url: width: 800
          | image_tag:
            widths: '240, 360, 480, 640, 800',
            sizes: '(min-width: 990px) 25vw, 50vw',
            loading: 'lazy'
        }}
      {% endif %}

      <h3>{{ card_product.title | escape }}</h3>
    </a>

    {% if card_product.price_varies %}
      <span>From {{ card_product.price_min | money }}</span>
    {% else %}
      <span>{{ card_product.price | money }}</span>
    {% endif %}

    {% unless card_product.available %}
      <span>Sold out</span>
    {% endunless %}
  </article>
{% endif %}
```

Product card dùng dữ liệu cấp product. Product page dùng dữ liệu variant hiện tại.

---

## 12. JavaScript khi đổi variant

Không chỉ cập nhật input `name="id"`.

Phải đồng bộ toàn bộ UI liên quan.

Ưu tiên Section Rendering API để lấy HTML mới từ Shopify:

```javascript
const url = new URL(window.location.href);

url.searchParams.set("variant", variantId);
url.searchParams.set("section_id", sectionId);

const response = await fetch(url.toString());
const htmlText = await response.text();
```

Sau đó thay các vùng:

```text
price
compare-at price
SKU
stock
button
media
unit price
pickup availability
selling plan
```

Dùng:

```javascript
window.history.replaceState({}, "", newUrl);
```

để cập nhật URL variant mà không reload trang.

Nếu cùng một dữ liệu xuất hiện nhiều nơi, dùng `querySelectorAll`, không dùng một `querySelector` duy nhất.

---

## 13. SEO và accessibility

Product page:

```liquid
<h1>{{ product.title | escape }}</h1>
```

Structured data:

```liquid
<script type="application/ld+json">
  {{ product | structured_data }}
</script>
```

Không tạo nhiều Product JSON-LD trùng nhau giữa theme và app.

Input phải có label:

```liquid
<label for="Variant-{{ section.id }}">
  Choose an option
</label>

<select
  id="Variant-{{ section.id }}"
  name="id"
>
```

Radio group nên dùng:

```html
<fieldset>
  <legend>Color</legend>
</fieldset>
```

Stock/status có thể dùng:

```liquid
<div role="status" aria-live="polite">
  ...
</div>
```

Product card không dùng `h1`.

---

## 14. Hiệu năng

Phải:

- Dùng responsive image.
- Không lazy-load ảnh hero chính.
- Không render hai gallery giống nhau cho desktop và mobile.
- Không nhúng toàn bộ `product | json` nếu không cần.
- Không serialize variant data nhiều lần.
- Không lặp toàn bộ variants nhiều lần không cần thiết.
- Không autoplay video tùy tiện.
- Chỉ tải dữ liệu cần cho section hiện tại.

Dữ liệu JSON tối thiểu:

```liquid
<script type="application/json" data-product-state>
  {
    "id": {{ product.id | json }},
    "url": {{ product.url | json }},
    "selectedVariantId": {{ current_variant.id | json }}
  }
</script>
```

---

## 15. Các lỗi AI tuyệt đối tránh

1. Dùng `product.id` làm input cart.
2. Dùng `product.price` trên product page.
3. Dùng `product.available` cho variant hiện tại.
4. Chỉ kiểm tra compare-at price có tồn tại.
5. Dùng `product.images` làm gallery duy nhất.
6. Dùng `img_url` hoặc `img_tag`.
7. Bọc `product.description` trong `<p>`.
8. Không hỗ trợ `?variant=...`.
9. Không kiểm tra metafield trống.
10. Tự format currency bằng JavaScript.
11. Chỉ cập nhật variant ID nhưng không cập nhật UI.
12. Dùng `querySelector` khi có nhiều vùng giá/preview.
13. Hard-code toàn bộ text nếu theme đa ngôn ngữ.
14. Tạo nhiều `h1` trên cùng trang.
15. Chỉ dùng CSS để vô hiệu hóa nút sold out.
16. Nhúng toàn bộ `product | json` nhiều lần.
17. Tạo Product JSON-LD trùng với app.
18. Phụ thuộc ngầm vào biến trong snippet.
19. Tự ghép URL `/products/{{ product.handle }}` khi đã có `product.url`.
20. Giả định mọi sản phẩm đều có media, SKU hoặc metafield.

---

## 16. Checklist bắt buộc

Trước khi hoàn tất code, AI phải kiểm tra:

- [ ] Có `current_variant`.
- [ ] Product form gửi variant ID.
- [ ] Giá product page lấy từ variant.
- [ ] Compare-at price chỉ hiện khi lớn hơn price.
- [ ] Availability lấy từ variant.
- [ ] Nút sold out có `disabled`.
- [ ] Variant URL hoạt động.
- [ ] Đổi variant cập nhật price, stock, SKU, media và button.
- [ ] Gallery dùng `product.media`.
- [ ] Image dùng `image_url` và `image_tag`.
- [ ] Description không bị escape hoặc bọc sai.
- [ ] Metafield có kiểm tra blank.
- [ ] Product card xử lý `price_varies`.
- [ ] Input có label.
- [ ] Product page chỉ có một H1.
- [ ] Structured data không bị trùng.
- [ ] Ảnh chính không lazy load.
- [ ] JavaScript không tự format currency sai market.
- [ ] Không nhúng dữ liệu product/variant thừa.

---

## 17. Mẫu section tối thiểu

```liquid
{% liquid
  assign current_variant =
    product.selected_or_first_available_variant

  if current_variant == blank
    assign current_variant =
      product.first_available_variant
  endif

  assign product_form_id =
    'ProductForm-' | append: section.id
%}

<section
  id="MainProduct-{{ section.id }}"
  data-product-id="{{ product.id }}"
  data-product-url="{{ product.url }}"
>
  <h1>{{ product.title | escape }}</h1>

  <div data-price>
    {% if current_variant.compare_at_price
      > current_variant.price
    %}
      <s>
        {{ current_variant.compare_at_price | money }}
      </s>
    {% endif %}

    <span>
      {{ current_variant.price | money }}
    </span>
  </div>

  <div role="status" data-stock>
    {% if current_variant.available %}
      In stock
    {% else %}
      Sold out
    {% endif %}
  </div>

  {% form 'product',
    product,
    id: product_form_id,
    class: 'product-form'
  %}
    {% unless product.has_only_default_variant %}
      <label for="Variant-{{ section.id }}">
        Choose an option
      </label>

      <select
        id="Variant-{{ section.id }}"
        name="id"
        data-variant-select
      >
        {% for variant in product.variants %}
          <option
            value="{{ variant.id }}"
            {% if variant.id == current_variant.id %}
              selected
            {% endif %}
            {% unless variant.available %}
              disabled
            {% endunless %}
          >
            {{ variant.title | escape }}
            — {{ variant.price | money }}
          </option>
        {% endfor %}
      </select>
    {% else %}
      <input
        type="hidden"
        name="id"
        value="{{ current_variant.id }}"
      >
    {% endunless %}

    <button
      type="submit"
      name="add"
      data-add-to-cart
      {% unless current_variant.available %}
        disabled
      {% endunless %}
    >
      {% if current_variant.available %}
        Add to cart
      {% else %}
        Sold out
      {% endif %}
    </button>
  {% endform %}

  {% if product.description != blank %}
    <div class="rte">
      {{ product.description }}
    </div>
  {% endif %}
</section>

<script type="application/ld+json">
  {{ product | structured_data }}
</script>
```

---

## 18. Nguồn tham chiếu

Khi cần xác minh behavior, ưu tiên:

```text
https://shopify.dev/docs/api/liquid/objects/product
https://shopify.dev/docs/api/liquid/objects/variant
https://shopify.dev/docs/api/liquid/tags/form
https://shopify.dev/docs/storefronts/themes/product-merchandising/variants
https://shopify.dev/docs/storefronts/themes/product-merchandising/media
https://github.com/Shopify/dawn
```

---

## Kết luận bắt buộc cho AI

Khi code giao diện sản phẩm Shopify:

```text
Product = thông tin chung.
Variant = đơn vị thực sự được mua.
Cart form phải gửi variant ID.
UI phải cập nhật toàn bộ khi variant thay đổi.
```

Nếu một implementation vi phạm bốn quy tắc trên, không được coi là hoàn chỉnh.
