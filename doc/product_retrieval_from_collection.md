# Hướng dẫn truy xuất dữ liệu Sản phẩm từ Collection

Dựa trên mã nguồn của section `For you, today` (`for-you-masonry.liquid`), dưới đây là phương pháp chuẩn (best practice) để truy xuất dữ liệu sản phẩm từ một collection trong theme Wrydeco.

## Các bước thực hiện

### 1. Khai báo biến `collection`
Đầu tiên, gán biến `collection` bằng dữ liệu từ cài đặt của section (schema). Nếu người dùng chưa chọn collection nào trong Theme Editor, ta có thể cung cấp một fallback mặc định bằng cách truy xuất trực tiếp qua handle của collection (ví dụ: `collections['for-you-today']`).

```liquid
{%- assign collection = section.settings.collection -%}
{%- if collection == blank -%}
  {%- assign collection = collections['for-you-today'] -%}
{%- endif -%}
```

### 2. Xác định số lượng sản phẩm cần hiển thị
Lấy giới hạn số lượng sản phẩm từ cài đặt, sử dụng filter `default` để đảm bảo luôn có một giá trị fallback nếu cài đặt trống.

```liquid
{%- assign products_to_show = section.settings.products_to_show | default: 10 -%}
```

### 3. Vòng lặp lấy sản phẩm (For Loop)
Sử dụng vòng lặp `for` lặp qua thuộc tính `collection.products` kết hợp với tham số `limit` để giới hạn số lượng trả về.

```liquid
{%- for product in collection.products limit: products_to_show -%}
  <!-- Gọi giao diện hiển thị cho từng product ở đây -->
  <!-- Ví dụ: {{ product.title }}, {{ product.price | money }}, v.v. -->
```

### 4. Xử lý trạng thái rỗng (Empty State / Placeholder)
Sử dụng thẻ `{%- else -%}` bên trong vòng lặp `for` để render ra giao diện mẫu (placeholder) trong trường hợp collection không tồn tại, hoặc không có sản phẩm nào bên trong. Điều này giúp giao diện không bị vỡ hoặc trống trơn khi cài đặt bị lỗi.

```liquid
{%- for product in collection.products limit: products_to_show -%}
  <!-- Giao diện sản phẩm thật -->
{%- else -%}
  <!-- Giao diện Placeholder mẫu -->
  {%- for i in (1..5) -%}
    <div class="pin-card">
      <div class="pin-card__image-wrapper">
        {{ 'product-' | append: i | placeholder_svg_tag: 'placeholder-svg' }}
      </div>
      <div class="pin-card__info">
        <h3>Example Product Title</h3>
        <div>$1,087.00</div>
      </div>
    </div>
  {%- endfor -%}
{%- endfor -%}
```

---

## Cấu trúc đoạn mã hoàn chỉnh

Kết hợp tất cả các bước trên, cấu trúc chuẩn sẽ trông như sau:

```liquid
{%- assign collection = section.settings.collection -%}
{%- if collection == blank -%}
  {%- assign collection = collections['for-you-today'] -%}
{%- endif -%}
{%- assign products_to_show = section.settings.products_to_show | default: 10 -%}

<div class="product-grid">
  {%- for product in collection.products limit: products_to_show -%}
    <!-- Gọi snippet hoặc tự viết HTML hiển thị sản phẩm -->
    <div class="product-item">
      <a href="{{ product.url }}">{{ product.title | escape }}</a>
      <p>{{ product.price | money }}</p>
    </div>
  {%- else -%}
    <!-- Placeholder data -->
    {%- for i in (1..products_to_show) -%}
      <div class="product-item placeholder">
        {{ 'product-' | append: i | placeholder_svg_tag: 'placeholder-svg' }}
        <p>Example Product</p>
      </div>
    {%- endfor -%}
  {%- endfor -%}
</div>
```
