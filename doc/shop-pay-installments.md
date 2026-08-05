Đúng, phần trong ảnh [Shop Pay Installments](../temp/shop-pay-installments.png) là **banner Shop Pay Installments gốc của Shopify**. Bạn không cần tự viết chữ “From $185.94/mo…”; Shopify sẽ tự tính số tiền, chèn logo Shop Pay và mở popup **View sample plans** bằng filter `payment_terms`. Nội dung hiển thị thay đổi theo giá sản phẩm và điều kiện trả góp. ([Shopify][1])

## Code Liquid mẫu cho local theme

Với theme kiểu Dawn, mở:

```text
sections/main-product.liquid
```

Tìm block hiển thị giá, thường có dạng:

```liquid
{%- when 'price' -%}
```

Sau phần render giá, chèn:

```liquid
{%- assign installment_form_id = 'product-form-installment-' | append: section.id -%}

<div class="product__shop-pay-installments">
  {%- form 'product',
    product,
    id: installment_form_id,
    class: 'installment caption-large'
  -%}
    <input
      type="hidden"
      name="id"
      value="{{ product.selected_or_first_available_variant.id }}"
    >

    {{ form | payment_terms }}
  {%- endform -%}
</div>
```

Ví dụ đầy đủ:

```liquid
{%- when 'price' -%}
  <div
    id="price-{{ section.id }}"
    role="status"
    {{ block.shopify_attributes }}
  >
    {%- render 'price',
      product: product,
      use_variant: true,
      show_badges: true,
      price_class: 'price--large'
    -%}
  </div>

  {%- assign installment_form_id = 'product-form-installment-' | append: section.id -%}

  <div class="product__shop-pay-installments">
    {%- form 'product',
      product,
      id: installment_form_id,
      class: 'installment caption-large'
    -%}
      <input
        type="hidden"
        name="id"
        value="{{ product.selected_or_first_available_variant.id }}"
      >

      {{ form | payment_terms }}
    {%- endform -%}
  </div>
```

Đây cũng là cách theme Dawn chính thức của Shopify triển khai banner ngay dưới giá sản phẩm. ([GitHub][2])

## CSS mẫu

Thêm vào `assets/base.css`, `theme.css` hoặc file CSS sản phẩm:

```css
.product__shop-pay-installments {
  margin-top: 10px;
  margin-bottom: 12px;
}

.product__shop-pay-installments .installment {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
}

.product__shop-pay-installments shopify-payment-terms {
  display: block;
}
```

## Nếu đã có sẵn product form

Khi giá nằm bên trong `{% form 'product', product %}`, chỉ cần đặt dòng này bên trong form:

```liquid
<div class="product__shop-pay-installments">
  {{ form | payment_terms }}
</div>
```

Ví dụ:

```liquid
{% form 'product', product, id: product_form_id %}
  <input
    type="hidden"
    name="id"
    value="{{ product.selected_or_first_available_variant.id }}"
  >

  <!-- Product price -->

  <div class="product__shop-pay-installments">
    {{ form | payment_terms }}
  </div>

  <!-- Add to cart button -->
{% endform %}
```

`payment_terms` bắt buộc phải nhận `form` object từ product form hoặc cart form. Input `name="id"` giúp Shopify xác định variant đang được chọn và cập nhật số tiền trả góp tương ứng. ([Shopify][3])

## Kiểm tra trước khi thêm

Trong thư mục local theme, tìm xem code đã tồn tại chưa:

```bash
grep -R "payment_terms" sections snippets
```

Nếu đã có:

```liquid
{{ form | payment_terms }}
```

thì không thêm lần nữa, nếu không banner có thể xuất hiện hai lần.

Lưu ý: code Liquid chỉ tạo vị trí hiển thị. Banner sẽ không hiện nếu store mới chỉ bật **Shopify Payments** nhưng chưa được kích hoạt và đủ điều kiện sử dụng **Shop Pay Installments**. ([Shopify][3])

[1]: https://shopify.dev/docs/api/liquid/filters/payment_terms "Liquid filters: payment_terms"
[2]: https://github.com/Shopify/dawn/blob/main/sections/main-product.liquid?utm_source=chatgpt.com "dawn/sections/main-product.liquid at main · Shopify/dawn"
[3]: https://shopify.dev/docs/storefronts/themes/pricing-payments/installments "Shop Pay Installments"
