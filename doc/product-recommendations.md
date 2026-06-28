# Hướng dẫn gọi Shopify Product Recommendations API từ Liquid

## Tổng quan

Shopify Product Recommendations hoạt động theo 2 cách:

1. **Liquid object `recommendations`** — render server-side trong section file
2. **AJAX endpoint `/recommendations/products.json`** — fetch client-side bằng JavaScript

Recommendations được Shopify tự sinh dựa trên lịch sử mua hàng, mô tả sản phẩm, và collection liên quan. Cần có đủ traffic/data để hệ thống học.

---

## Cách 1: Liquid Object `recommendations`

Object `recommendations` chỉ khả dụng bên trong file section có tên **`product-recommendations.liquid`**.

### Tạo file section

Tạo file: `sections/product-recommendations.liquid`

```liquid
{% if recommendations.performed and recommendations.products_count > 0 %}
  <div class="product-recommendations">
    <h2>Sản phẩm liên quan</h2>
    <ul>
      {% for product in recommendations.products %}
        <li>
          <a href="{{ product.url }}">
            <img src="{{ product.featured_image | image_url: width: 300 }}" alt="{{ product.title }}">
            <p>{{ product.title }}</p>
            <p>{{ product.price | money }}</p>
          </a>
        </li>
      {% endfor %}
    </ul>
  </div>
{% endif %}

{% schema %}
{
  "name": "Product Recommendations",
  "limit": 1,
  "templates": ["product"]
}
{% endschema %}
```

### Các properties của `recommendations`

| Property                         | Mô tả                              |
| -------------------------------- | ---------------------------------- |
| `recommendations.performed`      | `true` nếu API đã trả về kết quả   |
| `recommendations.products`       | Mảng sản phẩm được gợi ý           |
| `recommendations.products_count` | Số lượng sản phẩm trả về           |
| `recommendations.intent`         | `"related"` hoặc `"complementary"` |

---

## Cách 2: AJAX Endpoint (JavaScript Fetch)

### Endpoint

```
GET /recommendations/products.json
```

### Parameters

| Param        | Bắt buộc | Mô tả                                         |
| ------------ | -------- | --------------------------------------------- |
| `product_id` | ✅       | ID sản phẩm hiện tại                          |
| `limit`      | ❌       | Số sản phẩm trả về (mặc định: 10, tối đa: 10) |
| `intent`     | ❌       | `related` (mặc định) hoặc `complementary`     |
| `section_id` | ❌       | ID section để trả về HTML đã render sẵn       |

### Ví dụ fetch JSON thuần

```javascript
const productId = {{ product.id }};

fetch(`/recommendations/products.json?product_id=${productId}&limit=4&intent=related`)
  .then(response => response.json())
  .then(data => {
    const products = data.products;
    products.forEach(product => {
      console.log(product.title, product.price);
    });
  });
```

### Ví dụ fetch kèm `section_id` (trả về HTML render sẵn) ✅ Khuyến nghị

Đây là cách chuẩn nhất — Shopify render section Liquid phía server rồi trả về HTML:

```javascript
// Trong product template hoặc JS file
const productId = {{ product.id }};
const sectionId = 'product-recommendations'; // tên file section (không có .liquid)

fetch(`/recommendations/products?section_id=${sectionId}&product_id=${productId}&limit=4`)
  .then(response => response.text())
  .then(html => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const inner = doc.querySelector('.product-recommendations');
    if (inner) {
      document.querySelector('#recommendations-container').innerHTML = inner.innerHTML;
    }
  });
```

> **Lưu ý:** Khi dùng `section_id`, endpoint là `/recommendations/products` (không có `.json`).

---

## Tích hợp vào Product Template

Trong file `templates/product.json` hoặc `sections/main-product.liquid`, thêm placeholder để JS inject vào:

```liquid
<div id="recommendations-container" data-product-id="{{ product.id }}">
  {{- 'product-recommendations' | section_url -}}
</div>

<script>
  document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('recommendations-container');
    const productId = container.dataset.productId;

    fetch(`/recommendations/products?section_id=product-recommendations&product_id=${productId}&limit=4`)
      .then(r => r.text())
      .then(html => {
        container.innerHTML = new DOMParser()
          .parseFromString(html, 'text/html')
          .querySelector('.product-recommendations')?.innerHTML || '';
      });
  });
</script>
```

---

## Lưu ý quan trọng

- Recommendations **chỉ hoạt động trên storefront thật** — không hoạt động trong Shopify Theme Editor preview hoặc localhost.
- Cần sản phẩm có đủ **sales data hoặc metadata** (tags, collection, description) để Shopify sinh gợi ý.
- `intent=complementary` yêu cầu bạn đã cấu hình **Complementary products** trong app Search & Discovery.
- Giới hạn tối đa **10 sản phẩm** mỗi request.
- Section file **bắt buộc phải tên là `product-recommendations.liquid`** để `recommendations` object hoạt động.
