Để icon **User/Account** ở góc trên bên phải chuyển khách hàng đến hệ thống **Customer accounts mới của Shopify**, bạn cần làm cả phần cài đặt Shopify và kiểm tra lại đường dẫn trong theme.

> Lưu ý: Shopify hiện không dùng cố định miền `account.shopify.com`. URL mặc định thường có dạng `shopify.com/{store-ID}/account`. Bạn cũng có thể đổi thành miền thương hiệu như `account.wrydeco.com`. ([Shopify Help Center][1])

## 1. Bật Customer accounts mới

Trong Shopify Admin:

1. Vào **Settings → Customer accounts**.
2. Nếu đang dùng **Legacy customer accounts**, nhấn **Upgrade**.
3. Bật **Show sign-in links**.
4. Lưu lại.

Customer accounts mới sử dụng đăng nhập không mật khẩu: khách nhập email và nhận mã xác minh 6 chữ số. ([Shopify Help Center][2])

## 2. Sửa đường dẫn icon User trong theme

Vào:

**Online Store → Themes → dấu ba chấm → Edit code**

Mở một trong các file thường chứa icon tài khoản:

* `sections/header.liquid`
* `snippets/header-icons.liquid`
* `snippets/header-drawer.liquid`

Tìm các từ:

```liquid
header__icon--account
```

hoặc:

```liquid
routes.account
```

hoặc:

```liquid
/account/login
```

Phần thẻ `<a>` của icon User nên sử dụng:

```liquid
<a
  href="{% if customer %}{{ routes.account_url }}{% else %}{{ routes.account_login_url }}{% endif %}"
  class="header__icon header__icon--account link focus-inset"
  rel="nofollow"
>
  {% render 'icon-account' %}
</a>
```

Trong đó:

* Khách chưa đăng nhập → `routes.account_login_url`
* Khách đã đăng nhập → `routes.account_url`

Shopify khuyến nghị dùng `routes.account_login_url` và `routes.account_url` thay vì tự nhập cứng URL, vì Shopify sẽ tự tạo đúng URL cho phiên bản Customer accounts mà cửa hàng đang sử dụng. ([Shopify][3])

## 3. Không nên nhập cứng URL này

Không nên dùng:

```liquid
<a href="https://account.shopify.com">
```

hoặc:

```liquid
<a href="https://shopify.com">
```

Vì đường dẫn tài khoản cần có ID cửa hàng, thông tin xác thực và tham số chuyển hướng. Chỉ cần dùng:

```liquid
{{ routes.account_login_url }}
```

Shopify sẽ tự sinh URL dạng phù hợp, ví dụ:

```text
https://shopify.com/authentication/1234567890/login
```

Sau khi đăng nhập, khách được chuyển đến trang đơn hàng tài khoản. ([Shopify Help Center][1])

## 4. Phương án đẹp hơn cho WRYDECO

Thay vì để khách nhìn thấy miền `shopify.com`, bạn nên tạo:

```text
account.wrydeco.com
```

Thực hiện tại:

1. **Settings → Customer accounts**
2. Tại mục **URL**, nhấn **Change domain**
3. Nhập:

```text
account
```

4. Nếu tên miền được quản lý bên ngoài Shopify, tạo DNS:

```text
Type: CNAME
Name/Host: account
Target: shops.myshopify.com
```

5. Sau khi kết nối, vào **Settings → Domains**
6. Chọn `account.wrydeco.com`
7. Đặt thành **Primary domain** cho Customer Account

Sau đó icon User vẫn giữ nguyên code `routes.account_url`, nhưng Shopify sẽ tự chuyển khách đến `account.wrydeco.com` thay vì hiển thị miền `shopify.com`. ([Shopify Help Center][1])

[1]: https://help.shopify.com/en/manual/customers/customer-accounts/customize-customer-accounts/connect-domain-customer-account "Shopify Help Center | Connecting a custom subdomain for your customer account pages"
[2]: https://help.shopify.com/en/manual/customers/customer-accounts "Shopify Help Center | Customer accounts"
[3]: https://shopify.dev/docs/storefronts/themes/sign-in "Customer sign-in links and redirects"
