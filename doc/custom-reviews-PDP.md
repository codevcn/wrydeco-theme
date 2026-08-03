# Tôi muốn PDP của sản phẩm này có thể hiển thị reviews của sản phẩm khác thì có dùng trên gói Free được ko?

**Có, gói Free vẫn làm được**, nhưng tùy cách bạn muốn hiển thị:

### Cách phù hợp nhất: Reviews Grid Widget

Bạn có thể đặt một section review riêng trên PDP và cho nó lấy review từ **một hoặc nhiều sản phẩm khác**:

1. Vào **Shopify Admin → Online Store → Themes → Customize**.
2. Mở template sản phẩm cần chỉnh.
3. Chọn **Add section → Apps → Reviews Grid**.
4. Trong **Reviews selection**, chọn **Custom products**.
5. Chọn sản phẩm có review mà bạn muốn hiển thị, tối đa 10 sản phẩm.
6. Save.

Reviews Grid và lựa chọn `Custom products` hiện có trên gói **Free**. ([Judge.me][1])

### Nhưng cần hiểu giới hạn

Reviews Grid chỉ tạo **một khu vực review riêng** trên PDP. Nó không:

- Nhập review đó vào Review Widget chính của sản phẩm hiện tại.
- Cộng review count vào sản phẩm hiện tại.
- Thay đổi số sao ở rating badge dưới giá.
- Biến review của sản phẩm khác thành review của sản phẩm đang xem.

### Trường hợp sản phẩm chưa có review

Nếu sản phẩm hiện tại có **0 review**, Review Widget mới cũng có lựa chọn:

**If no reviews show → Reviews for other products**

Tính năng này dùng được trên Free, nhưng Judge.me tự lấy review từ sản phẩm khác; bạn không chọn chính xác sản phẩm nguồn. Khi sản phẩm hiện tại bắt đầu có review, phần fallback này không còn xuất hiện. ([Judge.me][2])

### Kết luận

- Chỉ cần PDP hiển thị thêm review của một sản phẩm khác: **Free làm được bằng Reviews Grid**.
- Muốn review được gộp trực tiếp vào Review Widget, dùng chung rating và review count: phải dùng **Product Groups trên gói Awesome**. ([Judge.me][3])

[1]: https://judge.me/help/en/articles/13904539-reviews-grid-widget "Reviews Grid Widget | Judge.me Help Center"
[2]: https://judge.me/help/en/articles/12460582-customizing-the-review-widget-new-version "Customizing the Review Widget (new version) | Judge.me Help Center"
[3]: https://judge.me/help/en/articles/8375162-sharing-reviews-across-product-groups "Sharing reviews across product groups | Judge.me Help Center"

# Có thể hiện ratings trung bình và tổng số ratings của toàn catalog ở PDP dc ko?

**Có, gói Free làm được** bằng widget **All Reviews Counter** của Judge.me. Widget này có thể đặt trực tiếp trên PDP và hiển thị:

- Điểm rating trung bình của toàn cửa hàng.
- Tổng số review đã được publish.
- Ví dụ: `Customers rate us 4.8/5 based on 250 reviews.` ([Judge.me][1])

### Cách thêm vào PDP

1. Vào **Shopify Admin → Online Store → Themes → Customize**.
2. Mở template **Products → Default product**.
3. Chọn **Add section** hoặc **Add block → Apps**.
4. Thêm block **Reviews Text** — tên mới của nó là **All Reviews Counter**.
5. Kéo đến vị trí mong muốn rồi **Save**. ([Judge.me][1])

### Điểm cần lưu ý

Số liệu của All Reviews Counter là **tất cả review đã publish**, có thể bao gồm cả:

- Product reviews của toàn bộ catalog.
- Store reviews về trải nghiệm mua hàng hoặc dịch vụ.

Judge.me không cung cấp biến Free riêng để chỉ tính **product reviews toàn catalog nhưng loại bỏ store reviews**. Reviews Grid cũng hiển thị header theo tất cả review đã publish, bao gồm product và store reviews. ([Judge.me][2])

Nếu cửa hàng của bạn hiện **không có Store Reviews**, số liệu này thực tế sẽ chính là:

> Rating trung bình và tổng số product reviews của toàn catalog.

Nên đặt tiêu đề rõ ràng như **“Customer Reviews Across Our Store”** hoặc **“Rated 4.8/5 Across All Products”**, không đặt ngay sát tên sản phẩm theo cách khiến khách hiểu đây là rating riêng của sản phẩm hiện tại. Badge Judge.me dưới giá vẫn nên giữ rating riêng của sản phẩm.

[1]: https://judge.me/help/en/articles/8420847-all-reviews-counter "All Reviews Counter | Judge.me Help Center"
[2]: https://judge.me/help/en/articles/13904539-reviews-grid-widget "Reviews Grid Widget | Judge.me Help Center"
