Liquid **không thể đọc trực tiếp** cấu hình discount code. Nhưng với discount code (khách nhập tay), có thêm một số điểm khác so với automatic discount:

---

**Những gì Liquid CÓ THỂ làm với discount code:**

**1. Hiển thị discount đã áp dụng trong Cart** (sau khi khách nhập code)

```liquid
{% for discount in cart.discount_applications %}
  <p>🎉 Mã <strong>{{ discount.title }}</strong> đang áp dụng
    {% if discount.value_type == 'percentage' %}
      — giảm {{ discount.value }}%
    {% elsif discount.value_type == 'fixed_amount' %}
      — giảm {{ discount.value | money }}
    {% endif %}
  </p>
{% endfor %}
```

**2. Hiển thị số tiền được giảm trên từng line item**

```liquid
{% for line in cart.line_items %}
  {% for allocation in line.discount_allocations %}
    <span>Tiết kiệm: -{{ allocation.amount | money }}</span>
  {% endfor %}
{% endfor %}
```

---

**Những gì Liquid KHÔNG làm được:**

- Kiểm tra xem mã `HELLO50` có hợp lệ không trước khi khách nhập
- Tự động hiển thị % giảm giá trên PDP/collection page (vì chưa biết khách có nhập code không)

---

**Để hiển thị banner "Nhập HELLO50 giảm 50%" trên storefront**, bạn làm thủ công trong theme:

```liquid
<div class="promo-banner">
  Nhập mã <strong>HELLO50</strong> để giảm 50% toàn bộ đơn hàng 🎉
</div>
```
