# Xác nhận về việc hiển thị review chéo sản phẩm bằng Judge.me

## Mục đích

Tôi đang sử dụng Judge.me trên một Shopify Online Store 2.0 theme và muốn xác nhận liệu hai nhu cầu dưới đây có thực sự bắt buộc phải dùng gói Judge.me Awesome trả phí hay không.

Tôi ưu tiên giải pháp chính thức, ổn định và không vi phạm điều khoản của Judge.me hoặc chính sách về tính minh bạch của review. Tôi không muốn sao chép review, gán review sai sản phẩm hoặc dựa vào API/markup nội bộ không được hỗ trợ.

## Bối cảnh hiện tại

- Judge.me app embed đã được bật.
- PDP đang sử dụng Judge.me Review Widget mới thông qua Shopify app block.
- Rating badge dưới giá sản phẩm được render từ metafield `product.metafields.judgeme.badge`.
- Review Widget sử dụng dữ liệu từ Judge.me, bao gồm `judgeme.review_widget_data`.
- Review riêng của từng sản phẩm đang hiển thị bình thường.
- Tôi muốn giữ rõ nguồn gốc sản phẩm của từng review để khách hàng không hiểu nhầm.

## Nhu cầu 1: Chia sẻ review giữa một nhóm sản phẩm

Ví dụ có ba sản phẩm liên quan:

```text
Product A: 0 reviews
Product B: 25 reviews
Product C: 18 reviews
```

Tôi muốn Product A, B và C cùng hiển thị tập review hợp nhất của cả nhóm. Product A có thể hiển thị review của B và C dù bản thân A chưa có review.

Tính năng chính thức có vẻ phù hợp là **Judge.me Product Groups**. Theo tài liệu Judge.me hiện tại:

- Reviews của các sản phẩm trong cùng group được chia sẻ trên các PDP trong group.
- Mỗi sản phẩm chỉ có thể thuộc một Product Group.
- Group hoạt động hai chiều; không phải cơ chế chỉ chia sẻ review một chiều.
- Tính năng được ghi là **Available on the Awesome plan**.

Tài liệu tham khảo:

- [Sharing reviews across product groups](https://judge.me/help/en/articles/8375162-sharing-reviews-across-product-groups)
- [Moving reviews from one product to another](https://judge.me/help/en/articles/12050430-moving-reviews-from-one-product-to-another)

## Nhu cầu 2: Hiển thị review từ tất cả sản phẩm

Tôi muốn đặt trên PDP một section riêng, chẳng hạn:

```text
Reviews from across the store
```

Section này hiển thị product reviews từ toàn bộ catalog, không chỉ review của sản phẩm hiện tại. Review cần giữ attribution hoặc liên kết đến sản phẩm gốc.

Tính năng chính thức có vẻ phù hợp là **Happy Customers Widget**, trước đây được gọi là **All Reviews Widget**. Theo tài liệu Judge.me hiện tại:

- Widget hiển thị product reviews và store reviews trong hai tab riêng.
- Widget có thể được thêm vào product page.
- Product reviews có thể đến từ tất cả sản phẩm trong store.
- Tính năng được ghi là **Available on the Awesome plan**.

Tài liệu tham khảo:

- [Happy Customers Widget](https://judge.me/help/en/articles/8201189-happy-customers-widget)
- [Collecting and displaying store reviews](https://judge.me/help/en/articles/8384957-collecting-and-displaying-store-reviews)

## Điểm dễ nhầm lẫn

Setting **Show store reviews** trong Review Widget mới dường như chỉ thêm **store reviews**, tức đánh giá về dịch vụ, giao hàng hoặc trải nghiệm mua sắm. Nó không đồng nghĩa với việc lấy product reviews từ tất cả sản phẩm trong catalog.

Do đó, các lựa chọn dường như là:

| Nhu cầu | Tính năng Judge.me | Gói theo tài liệu hiện tại |
|---|---|---|
| Review riêng của sản phẩm hiện tại | Review Widget | Free hoặc Awesome |
| Thêm store reviews vào Review Widget | Show store reviews | Free |
| Product reviews từ toàn bộ catalog | Happy Customers Widget | Awesome |
| Chia sẻ review giữa các sản phẩm liên quan | Product Groups | Awesome |

## Kết luận tạm thời cần xác nhận

Theo tài liệu chính thức của Judge.me được kiểm tra ngày **01/08/2026**, cả hai nhu cầu sau đều cần gói Awesome hoặc trial Awesome:

1. Chia sẻ review giữa các sản phẩm bằng Product Groups.
2. Hiển thị product reviews từ tất cả sản phẩm bằng Happy Customers Widget.

Trial chỉ là quyền dùng thử có thời hạn; nếu muốn giữ tính năng sau trial thì có vẻ phải tiếp tục trả phí.

## Câu hỏi dành cho cộng đồng hoặc Judge.me Support

1. Kết luận trên có chính xác với phiên bản Judge.me hiện tại trên Shopify không?
2. Có cách chính thức nào trên gói Free để Review Widget của Product A hiển thị product reviews của Product B hoặc một nhóm sản phẩm khác không?
3. Có cách chính thức nào trên gói Free để hiển thị product reviews từ toàn bộ catalog trên PDP không?
4. Setting **Show store reviews** có bao gồm product reviews từ sản phẩm khác hay chỉ bao gồm store reviews?
5. Có widget miễn phí nào của Judge.me hiển thị tất cả product reviews, thay vì chỉ một số review được chọn hoặc store reviews không?
6. Product Groups và Happy Customers Widget có ngừng hoạt động hoặc quay về hành vi mặc định ngay khi trial Awesome kết thúc không?
7. Nếu dùng Product Groups, Judge.me có tự cập nhật rating badge, review count, histogram và review data metafields cho toàn bộ group không?
8. Có API hoặc theme integration chính thức nào cho phép chọn một `source product` khác cho Review Widget mà không cần Awesome không?
9. Nếu có giải pháp miễn phí, giải pháp đó có được Judge.me hỗ trợ chính thức và có ổn định khi widget được nâng cấp không?
10. Với review lấy từ sản phẩm khác, Judge.me có luôn hiển thị tên hoặc liên kết của sản phẩm gốc để bảo đảm tính minh bạch không?

## Những giải pháp tôi không muốn sử dụng

- Export rồi import review sang một sản phẩm khác chỉ để tăng review count.
- Sửa product ID hoặc HTML nội bộ của widget bằng JavaScript không được Judge.me hỗ trợ.
- Hiển thị review của sản phẩm khác như thể review được viết cho sản phẩm hiện tại.
- Dùng rating toàn shop làm `Product.aggregateRating` cho một sản phẩm cụ thể.
- Xây giải pháp phụ thuộc vào endpoint, token hoặc markup riêng tư của Judge.me.

Nếu có phương án khác, vui lòng cho biết tên tính năng, gói áp dụng, tài liệu chính thức và các giới hạn liên quan.
