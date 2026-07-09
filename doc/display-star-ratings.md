Được. Nếu muốn chỉnh **trực tiếp trong local theme**, cách chuẩn là thêm block Judge.me vào file PDP của theme.

Judge.me có hỗ trợ chèn bằng Liquid code, nhưng họ khuyến nghị cách này cho người biết code; đoạn star badge chính thức là `jdgm-preview-badge` dùng `product.metafields.judgeme.badge`. ([Judge.me][1])

## Cách làm trong local theme

Vào folder theme local của bạn, ví dụ:

```bash
cd D:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-theme
```

## Bước 1: Tìm file PDP chính

Thường nằm ở một trong các file này:

```text
sections/main-product.liquid
sections/product-template.liquid
templates/product.json
```

Với theme OS 2.0, khả năng cao là:

```text
sections/main-product.liquid
```

Mở file đó, tìm đoạn dạng:

```liquid
{%- for block in section.blocks -%}
```

và các case như:

```liquid
{%- case block.type -%}
  {%- when 'title' -%}
  {%- when 'price' -%}
  {%- when 'variant_picker' -%}
```

## Bước 2: Thêm case cho Judge.me rating

Thêm đoạn này trong `case block.type`:

```liquid
{%- when 'judgeme_rating' -%}
  <div class="product__judgeme-rating" {{ block.shopify_attributes }}>
    <div class="jdgm-widget jdgm-preview-badge" data-id="{{ product.id }}">
      {{ product.metafields.judgeme.badge }}
    </div>
  </div>
```

Nên đặt case này gần khu vực `title` hoặc `price`.

Ví dụ thứ tự hợp lý:

```liquid
{%- when 'title' -%}
  <div class="product__title" {{ block.shopify_attributes }}>
    <h1>{{ product.title | escape }}</h1>
  </div>

{%- when 'judgeme_rating' -%}
  <div class="product__judgeme-rating" {{ block.shopify_attributes }}>
    <div class="jdgm-widget jdgm-preview-badge" data-id="{{ product.id }}">
      {{ product.metafields.judgeme.badge }}
    </div>
  </div>

{%- when 'price' -%}
  ...
```

## Bước 3: Thêm block vào schema

Cuối file `sections/main-product.liquid`, tìm:

```liquid
{% schema %}
```

Bên trong `"blocks": [...]`, thêm block này:

```json
{
  "type": "judgeme_rating",
  "name": "Judge.me star rating",
  "limit": 1
}
```

Ví dụ:

```json
"blocks": [
  {
    "type": "title",
    "name": "Title",
    "limit": 1
  },
  {
    "type": "judgeme_rating",
    "name": "Judge.me star rating",
    "limit": 1
  },
  {
    "type": "price",
    "name": "Price",
    "limit": 1
  }
]
```

Lưu ý: JSON trong schema phải đúng dấu phẩy. Nếu block trước đó chưa có dấu phẩy thì thêm vào.

## Bước 4: Thêm block vào template product JSON

Mở file:

```text
templates/product.json
```

hoặc nếu theme dùng template khác:

```text
templates/product.default.json
templates/product.rug.json
```

Tìm section `main-product`, thường giống vầy:

```json
"main": {
  "type": "main-product",
  "blocks": {
    "title": {
      "type": "title",
      "settings": {}
    },
    "price": {
      "type": "price",
      "settings": {}
    }
  },
  "block_order": [
    "title",
    "price"
  ]
}
```

Thêm block:

```json
"judgeme_rating": {
  "type": "judgeme_rating",
  "settings": {}
}
```

Rồi đưa nó vào `block_order` ngay sau title:

```json
"block_order": [
  "title",
  "judgeme_rating",
  "price"
]
```

Vị trí này sẽ hiển thị:

```text
Product title
Judge.me stars
Price
```

Đây là vị trí mình khuyên dùng cho PDP.

## Bước 5: Thêm CSS

Thêm vào file CSS chính, thường là:

```text
assets/base.css
```

hoặc:

```text
assets/theme.css
assets/component-product.css
```

Code:

```css
.product__judgeme-rating {
  margin-top: 6px;
  margin-bottom: 12px;
  line-height: 1;
}

.product__judgeme-rating .jdgm-preview-badge {
  display: inline-flex;
  align-items: center;
}

@media screen and (max-width: 749px) {
  .product__judgeme-rating {
    margin-top: 4px;
    margin-bottom: 10px;
  }
}
```

## Bước 6: Chạy local để kiểm tra

```bash
shopify theme dev
```

Mở PDP sản phẩm và kiểm tra sao có hiện không.

Nếu không hiện, kiểm tra thêm 2 điểm:

1. **Judge.me app embed phải được bật trong Shopify admin**. Judge.me yêu cầu bật app embed khi dùng widget/app block trên theme. ([Judge.me][2])
2. Product phải có dữ liệu review/metafield Judge.me. Nếu chưa có review, badge có thể không hiện hoặc chỉ hiện rỗng tùy setting.

## Cách nhanh hơn nếu không muốn tạo block

Bạn có thể chèn thẳng dưới title trong `main-product.liquid`:

```liquid
<div class="product__judgeme-rating">
  <div class="jdgm-widget jdgm-preview-badge" data-id="{{ product.id }}">
    {{ product.metafields.judgeme.badge }}
  </div>
</div>
```

Nhưng mình **không khuyên** cách này, vì sau này muốn đổi vị trí phải sửa code lại. Cách chuẩn hơn là tạo block `judgeme_rating`, rồi sắp xếp bằng `templates/product.json` hoặc Theme Editor.
