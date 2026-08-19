Đúng. Với nút tím **“Follow on Shop”** như trong ảnh, Shopify đã có sẵn Liquid filter để render nút này; không cần tự dựng link hay tự code logic follow. Shopify hiện hỗ trợ cú pháp: ([Shopify][1])

```liquid
{{ shop | login_button: action: 'follow' }}
```

Shopify sẽ tự generate HTML/button và xử lý việc đăng nhập Shop nếu cần rồi follow store trong Shop app. ([Shopify][1])

Tuy nhiên, không phải cứ paste Liquid là mọi store đều hiện được. Store cần đáp ứng điều kiện của Shopify, hiện tại gồm **Shop sales channel đã cài** và **Shop Pay đã bật**. ([Shopify Help Center][2])

Nếu theme của Wrydeco đã hỗ trợ sẵn thì còn đơn giản hơn: vào **Online Store → Themes → Customize → Footer → bật “Follow on Shop”**. Shopify xác nhận đây là option chính thức trong Footer. ([Shopify Help Center][2])

Nếu bạn muốn **đặt nút ở vị trí tùy ý trong footer**, giống SpryInterior, thì có thể chèn Liquid vào `footer.liquid`/section footer tương ứng:

```liquid
<div class="footer__follow-on-shop">
  {{ shop | login_button: action: 'follow' }}
</div>
```

Sau đó CSS chỉ nên dùng để chỉnh **layout/spacing xung quanh**. Lưu ý Shopify yêu cầu **không sửa màu thương hiệu của nút Follow on Shop** đối với theme theo Theme Store requirements. ([Shopify][3])

Nên nếu mục tiêu của bạn là thêm chính xác nút đó vào footer Wrydeco thì **đúng, về cơ bản một dòng Liquid là phần quan trọng nhất**.

[1]: https://shopify.dev/docs/api/liquid/filters/login_button "Liquid filters: login_button"
[2]: https://help.shopify.com/en/manual/online-store/themes/customizing-themes/common-customizations/add-shop-buttons "Shopify Help Center | Add Shop sign-in buttons to your store"
[3]: https://shopify.dev/docs/storefronts/themes/store/requirements?utm_source=chatgpt.com "Theme store requirements"
