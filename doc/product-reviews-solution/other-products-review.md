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
