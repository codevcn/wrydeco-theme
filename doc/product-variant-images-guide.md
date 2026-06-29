# Lấy metafield `variant_images` của product variant

Để lấy metafield `variant_images` của variant, bạn cần biết namespace và key của metafield đó. Để tôi kiểm tra thông tin metafield của variant này trước.

Đây là thông tin metafield:

- **Namespace:** `custom`
- **Key:** `variant_images`
- **Type:** `multi_line_text_field`
- **Value hiện tại:** `natural_eye-level\nnatural_high-angle`

---

Dưới đây là code Liquid mẫu để lấy giá trị metafield này:

```liquid
{% comment %} Lấy metafield variant_images từ variant hiện tại {% endcomment %}
{% assign variant_images_raw = product.selected_or_first_available_variant.metafields.custom.variant_images %}

{% if variant_images_raw != blank %}
  {% comment %} Tách thành mảng theo dòng (multi_line_text_field) {% endcomment %}
  {% assign variant_images_list = variant_images_raw | newline_to_br | split: '<br />' %}

  {% for image_key in variant_images_list %}
    {% assign image_key = image_key | strip %}
    {% if image_key != blank %}
      <p>{{ image_key }}</p>
      {{- comment -}} Hoặc dùng image_key để map sang ảnh thực tế -}}
    {% endif %}
  {% endfor %}
{% endif %}
```

---

**Lưu ý:**

- Vì type là `multi_line_text_field`, các giá trị được phân tách bằng ký tự xuống dòng (`\n`), nên dùng `newline_to_br` + `split` để tách thành mảng.
- Nếu bạn dùng metafield này để map sang ảnh sản phẩm, bạn cần thêm logic tìm ảnh theo `alt` text hoặc filename tương ứng với các key như `natural_eye-level`, `natural_high-angle`.

---

# Lấy danh sách ảnh của product và alt text của từng ảnh

```liquid
{% comment %} Lấy danh sách ảnh của product {% endcomment %}
{% for image in product.images %}
  <img
    src="{{ image | image_url: width: 800 }}"
    alt="{{ image.alt }}"
    width="{{ image.width }}"
    height="{{ image.height }}"
  >

  {% comment %} Lấy field alt của từng ảnh {% endcomment %}
  <p>Alt text: {{ image.alt }}</p>
{% endfor %}
```

---

Nếu bạn muốn **tìm ảnh theo alt text cụ thể** (ví dụ map với `variant_images` metafield ở trên):

```liquid
{% assign target_alt = "natural_eye-level" %}

{% for image in product.images %}
  {% if image.alt == target_alt %}
    <img src="{{ image | image_url: width: 800 }}" alt="{{ image.alt }}">
    {% break %}
  {% endif %}
{% endfor %}
```

---

Kết hợp cả hai — **lấy ảnh từ metafield variant rồi map sang ảnh product:**

```liquid
{% assign variant = product.selected_or_first_available_variant %}
{% assign variant_images_raw = variant.metafields.custom.variant_images %}

{% if variant_images_raw != blank %}
  {% assign image_keys = variant_images_raw | newline_to_br | split: '<br />' %}

  {% for key in image_keys %}
    {% assign key = key | strip %}
    {% for image in product.images %}
      {% if image.alt == key %}
        <img src="{{ image | image_url: width: 800 }}" alt="{{ image.alt }}">
        {% break %}
      {% endif %}
    {% endfor %}
  {% endfor %}
{% endif %}
```

**Tóm tắt các property của `image`:**

- `image.alt` — alt text
- `image.src` — URL gốc
- `image.width` / `image.height` — kích thước
- `image | image_url: width: 800` — URL đã resize
