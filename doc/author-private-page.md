# Tài liệu hướng dẫn tạo một trang tác giả riêng trong theme (dùng metaobject `product_author` bạn đang có), đây là các bước:

> Tài liệu này giả định chủ store đã tạo metaobject definition `product_author` trên shopify admin xong xuôi.

---

## Bước 1: Tạo URL template cho metaobject

Vào **Content → Metaobjects → product_author → Settings**, bật tùy chọn **"Has web presence"** và đặt URL handle, ví dụ: `/authors/{handle}`. Mỗi tác giả sẽ có URL riêng như `/authors/alex-nguyen`.

---

## Bước 2: Tạo template Liquid trong theme

Trong theme code (local hoặc qua **Online Store → Themes → Edit code**), tạo file:

```
templates/metaobject/product_author.json
```

---

## Bước 3: Tạo section hiển thị thông tin tác giả

Tạo file `sections/metaobject-product-author.liquid` với nội dung mẫu:

```liquid
{% assign author = metaobject %}

<div class="author-page">
  {% if author.fields.avatar.value %}
    <img src="{{ author.fields.avatar.value | image_url: width: 300 }}" alt="{{ author.fields.name.value }}">
  {% endif %}

  <h1>{{ author.fields.name.value }}</h1>
  <p>{{ author.fields.bio.value }}</p>
</div>

{% schema %}
{
  "name": "Author Profile",
  "settings": []
}
{% endschema %}
```

> Thay `avatar`, `name`, `bio` bằng đúng tên field bạn đã định nghĩa trong metaobject definition.

---

## Bước 4: Kết nối template với section

JSON template (`metaobject.product_author.json`):

```json
{
  "sections": {
    "main": {
      "type": "metaobject-product-author"
    }
  },
  "order": ["main"]
}
```

---

## Bước 5: Kiểm tra field names

Vào **Content → Metaobjects → product_author** (definition), xem danh sách các field và ghi lại đúng **key** của từng field để dùng trong Liquid (`author.fields.<key>.value`).

---

## Bước 6: Preview và publish

- Test URL: `your-store.myshopify.com/authors/alex-nguyen`
- Nếu dùng local theme development (`shopify theme dev`), preview trực tiếp trên localhost.

## Bước 7: Note

- Xem ảnh chụp màn hình thông tin product_author trong Shopify admin để biết field names chính xác:
  - [Ảnh 1](../temp/product-author-metaobject-screenshot-1.png)
  - [Ảnh 2](../temp/product-author-metaobject-screenshot-2.png)
