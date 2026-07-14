Tôi đã kiểm tra **Wishlist by Square** trên Shopify App Store, tài liệu chính thức, chính sách quyền riêng tư và các đánh giá hiện tại.

## Kết luận nhanh

**Đây là một lựa chọn khá tốt để triển khai wishlist miễn phí cho WRYDECO**, đặc biệt nếu nhu cầu hiện tại chỉ là:

- Nút trái tim trên product page và product card.
- Trang danh sách yêu thích riêng.
- Guest không cần đăng nhập vẫn dùng được.
- Khi đăng nhập, wishlist guest được gắn vào Customer ID.
- Chia sẻ wishlist.
- Xem thống kê sản phẩm được yêu thích.

Tuy nhiên, có một điểm quan trọng: **tài liệu chưa khẳng định rõ bằng câu chữ rằng customer đăng nhập trên thiết bị mới chắc chắn thấy lại wishlist**. Cơ chế của app cho thấy khả năng này có tồn tại, nhưng nên kiểm tra thực tế trước khi dùng production.

## Giá

Hiện tại app được niêm yết là:

```text
Free
```

Không có gói trả phí hoặc giới hạn usage nào được công bố trên Shopify App Store tại thời điểm kiểm tra. Phí có thể được nhà phát triển thay đổi trong tương lai, nhưng hiện tại không thấy khoản phí hàng tháng. ([Shopify App Store][1])

## App hoạt động như thế nào?

Theo tài liệu chính thức:

- Wishlist được lưu **trên cloud của Square Apps**.
- Đồng thời sử dụng cookie trên trình duyệt.
- Guest không cần tạo tài khoản.
- Mỗi guest được theo dõi bằng một `Anonymous ID`.
- Khi guest đăng nhập trong cùng session, các sản phẩm đã lưu được chuyển sang `customer ID` của tài khoản Shopify. ([Square Apps][2])

Luồng có thể hiểu như sau:

```text
Guest
→ Cloud wishlist + cookie + Anonymous ID

Guest đăng nhập
→ Merge wishlist vào Shopify Customer ID

Customer đăng nhập
→ App tải wishlist theo Customer ID
```

Dựa trên cách này, dữ liệu **không có vẻ được lưu bằng Customer Metafield của Shopify**. Khả năng cao Square Apps lưu trong database riêng của họ và dùng Customer ID làm khóa liên kết. Đây là suy luận dựa trên tài liệu lưu cloud và danh sách quyền của app; Shopify App Store không hiển thị quyền đọc/ghi Customer resource cho app này. ([Square Apps][2])

## Đồng bộ khi đổi thiết bị

Đây chính là yêu cầu quan trọng nhất của bạn.

### Guest chưa đăng nhập

Không nên kỳ vọng đồng bộ sang thiết bị khác.

Guest được nhận diện thông qua cookie và Anonymous ID. Khi sang điện thoại hoặc trình duyệt khác, app không có cách chắc chắn để biết đó là cùng một người, trừ khi họ sử dụng link wishlist đã chia sẻ.

### Customer đã đăng nhập

Tài liệu nói wishlist guest sẽ được chuyển sang `customer ID` sau khi đăng nhập. Điều này cho thấy app có nền tảng kỹ thuật để tải wishlist theo tài khoản trên thiết bị khác. ([Square Apps][2])

Tuy nhiên, tài liệu chính thức hiện chỉ nói:

- Lưu trên cloud.
- Theo dõi customer account khi đăng nhập.
- Chuyển Anonymous ID sang Customer ID trong cùng session.

Tài liệu **không ghi thẳng**:

> Wishlist automatically synchronizes across all devices after login.

Vì vậy, trước khi quyết định, cần thực hiện test này:

```text
1. Thêm sản phẩm vào wishlist trên máy tính.
2. Đăng nhập Shopify Customer Account.
3. Mở website trên điện thoại.
4. Đăng nhập cùng customer account.
5. Kiểm tra wishlist có xuất hiện hay không.
```

Tôi đánh giá khả năng hỗ trợ là cao, nhưng không nên xem là đã được xác nhận 100% cho đến khi test.

## Các tính năng đáng chú ý

App hiện hỗ trợ:

- Wishlist button trên product page.
- Icon trái tim trên homepage và collection product cards.
- Dedicated wishlist page:

```text
/a/page/wishlist
```

- Xóa sản phẩm khỏi wishlist.
- Add to cart trực tiếp.
- Add toàn bộ wishlist vào cart.
- Cảnh báo tồn kho thấp.
- Chia sẻ wishlist bằng link hoặc email.
- Điều chỉnh màu sắc, icon, text và vị trí.
- Advanced display rules để chỉ hiện trên một số sản phẩm.
- Analytics trong 30 ngày.
- Top 10 sản phẩm được wishlist nhiều nhất.
- Theo dõi hoạt động guest và customer đã đăng nhập. ([Square Apps][2])

## Khả năng tương thích giao diện WRYDECO

App sử dụng Shopify App Embed:

```text
Online Store
→ Themes
→ Customize
→ App embeds
→ Enable Wishlist by Square
```

Nó hỗ trợ thay đổi:

- Text.
- Màu sắc.
- Icon.
- Vị trí.
- Hiện/ẩn button.
- Hiện icon trên product image.
- Vị trí icon trong header.

Tài liệu cũng nói app đã cải thiện hỗ trợ các theme có product-card structure tùy biến. Tuy nhiên, một review gần đây cho biết họ vẫn cần đội hỗ trợ viết custom integration cho một store cụ thể. Điều đó có nghĩa theme WRYDECO đã custom mạnh có thể cần Square Apps can thiệp. ([Square Apps][2])

Điểm tích cực là nhiều review tập trung khen tốc độ hỗ trợ và khả năng sửa integration theo từng store.

## Ngôn ngữ

App Store liệt kê 15 ngôn ngữ, nhưng **không có tiếng Việt**. Có tiếng Anh, Đức, Pháp, Tây Ban Nha, Nhật, Trung Quốc và một số ngôn ngữ châu Âu. ([Shopify App Store][1])

Tài liệu cho phép chỉnh text và translation theo từng ngôn ngữ, nhưng cần kiểm tra xem có thể tự nhập đầy đủ bản dịch tiếng Việt cho mọi trạng thái hay không.

Với WRYDECO chủ yếu dùng tiếng Anh, điều này không phải vấn đề lớn.

## Uy tín hiện tại

Tại thời điểm kiểm tra:

- `Built for Shopify`.
- Đánh giá `5.0/5`.
- `87` reviews.
- 100% review hiện tại là 5 sao.
- Ra mắt ngày `24/06/2025`.
- Nhà phát triển: Square Apps.
- Square Apps hiện có 5 app trên Shopify App Store, tất cả đều được niêm yết 5 sao và phần lớn có huy hiệu Built for Shopify. ([Shopify App Store][1])

Điểm cần nhìn nhận thẳng:

- App còn khá mới, mới hoạt động khoảng một năm.
- 87 review là tín hiệu tốt nhưng chưa phải lịch sử vận hành dài.
- Phần lớn review công khai tập trung vào support hơn là độ ổn định dài hạn hoặc đồng bộ đa thiết bị.

## Dữ liệu và quyền riêng tư

Shopify App Store cho biết app có thể xem:

- Thông tin chủ store.
- Products, collections và product listings.
- Theme.
- Metaobjects.
- Inventory.
- Tags.
- Locales và translations.
- Selling plans. ([Shopify App Store][1])

Chính sách chung của Square Apps/Appsolve nói họ có thể xử lý dữ liệu customer như ID, tên, email, số điện thoại, địa chỉ thanh toán và giao hàng. Tuy nhiên, đây là chính sách chung cho toàn bộ sản phẩm của công ty, rộng hơn quyền cụ thể hiển thị cho app Wishlist. Chính sách cũng nói dữ liệu có thể được giữ trong thời gian cần thiết và trong một số trường hợp tối thiểu ba năm sau lần liên hệ hoặc kết thúc quan hệ. ([Square Apps][3])

Bạn nên thêm Square Apps vào danh sách service provider trong Privacy Policy của WRYDECO sau khi cài app.

**Nên cài thử app này**, vì hiện tại miễn phí, có analytics, wishlist guest, chia sẻ và khả năng merge vào customer ID. Nhưng chưa nên xem nó là giải pháp chính thức cho yêu cầu đồng bộ đa thiết bị trước khi hoàn thành bài test đăng nhập trên hai thiết bị.

Các điều cần xác nhận trực tiếp với support trước khi launch:

```text
1. Logged-in customers có được đồng bộ wishlist giữa nhiều thiết bị không?
2. Wishlist được lưu bao lâu sau khi customer không hoạt động?
3. Dữ liệu có còn tồn tại sau khi uninstall và reinstall không?
4. Có cách export toàn bộ wishlist data không?
5. App lưu product hay chính xác product variant?
6. Có giới hạn wishlist items hoặc wishlist actions không?
7. Có hỗ trợ hoàn chỉnh Shopify New Customer Accounts không?
```

Với trạng thái hiện tại, đây là lựa chọn hợp lý hơn việc tự build backend wishlist ngay từ đầu.
