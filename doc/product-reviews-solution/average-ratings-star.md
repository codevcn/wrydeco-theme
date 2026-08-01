# Có thể hiện ratings trung bình và tổng số ratings của toàn catalog ở PDP được ko?

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
