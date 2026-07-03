Để truy xuất các policy này trong Liquid, bạn dùng object **`shop`** — Shopify expose tất cả policies qua các attribute sau:

```liquid
{{ shop.shipping_policy.body }}
{{ shop.refund_policy.body }}
{{ shop.privacy_policy.body }}
{{ shop.terms_of_service.body }}
{{ shop.subscription_policy.body }}
```

Mỗi policy object có 2 properties:

- `.body` — nội dung HTML đầy đủ
- `.url` — đường dẫn đến trang policy (ví dụ `/policies/shipping-policy`)

---

**Ví dụ dùng thực tế:**

```liquid
{{- shop.shipping_policy.body -}}
```

Hoặc nếu muốn link đến trang policy:

```liquid
<a href="{{ shop.shipping_policy.url }}">Shipping Policy</a>
```

---

**Lưu ý quan trọng:**

- `.body` trả về **raw HTML** nên không cần thêm `| escape`
- Nếu policy chưa được set, `.body` sẽ trả về empty string — nên wrap trong `{% if %}` để tránh render block trống:

```liquid
{% if shop.shipping_policy.body != blank %}
  <div class="policy-content">
    {{ shop.shipping_policy.body }}
  </div>
{% endif %}
```
