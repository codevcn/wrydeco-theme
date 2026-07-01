Dưới đây là code mẫu Liquid cho tính năng **hover filter by wood type**, với 3 cách lấy data thật tùy theo nơi bạn lưu trữ:

---

## Cách 1: Từ Metafield (phù hợp nhất với setup của bạn)

Giả sử metafield namespace là `custom`, key là `wood_type` (single_line_text hoặc list):

```liquid
{% comment %} Thu thập unique wood types từ collection hiện tại {% endcomment %}
{% assign wood_types = "" %}

{% for product in collection.products limit: 250 %}
  {% assign wt = product.metafields.custom.wood_type.value %}
  {% if wt != blank %}
    {% unless wood_types contains wt %}
      {% assign wood_types = wood_types | append: wt | append: "|" %}
    {% endunless %}
  {% endif %}
{% endfor %}

{% assign wood_type_list = wood_types | split: "|" | uniq %}

{% comment %} Render nút filter với hover dropdown {% endcomment %}
<div class="wood-filter-wrapper">
  <button class="wood-filter-btn">
    Wood Type
    <span class="wood-filter-arrow">▾</span>
  </button>
  <div class="wood-filter-dropdown">
    <a href="{{ collection.url }}" class="wood-filter-option {% if current_tags == blank %}active{% endif %}">
      All
    </a>
    {% for wt in wood_type_list %}
      {% if wt != blank %}
        <a href="{{ collection.url }}?filter.p.m.custom.wood_type={{ wt | url_encode }}"
           class="wood-filter-option {% if current_tags contains wt %}active{% endif %}">
          {{ wt }}
        </a>
      {% endif %}
    {% endfor %}
  </div>
</div>
```
