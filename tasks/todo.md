# TASK — Build trang chi tiết sản phẩm Shopify

## 1. Mục tiêu

Xây dựng hoặc cập nhật trang chi tiết sản phẩm Shopify dựa trên các ảnh chụp màn hình đã được cung cấp, bảo đảm:

- Bố cục và thứ tự nội dung bám sát trang tham chiếu trên mobile.
- Dữ liệu sản phẩm được lấy động từ Shopify, không nhập cứng theo một sản phẩm mẫu.
- Variant, giá, SKU, tồn kho, hình ảnh và trạng thái nút mua được đồng bộ khi khách thay đổi lựa chọn.
- Hiển thị đúng thông tin của chương trình giảm giá đang active được mô tả trong `sale-off-event-template.md`.
- Không hiển thị sai giá giảm hoặc khiến khách hiểu nhầm discount đã được áp dụng trước khi Shopify xác nhận tại cart/checkout.
- Giữ khả năng quản lý nội dung từ Shopify Admin, theme editor, metafield hoặc metaobject khi phù hợp.

## 2. Nguồn tham chiếu bắt buộc

### 2.1. Ảnh chụp trang sản phẩm

Sử dụng ba ảnh chụp màn hình trang chi tiết sản phẩm đã được cung cấp trước đó làm nguồn tham chiếu chính cho:

- Thứ tự các khối nội dung.
- Cách nhóm thông tin.
- Vị trí tương đối giữa thông tin sản phẩm, gallery, variant, các quyền lợi mua hàng và CTA.
- Hành vi mong đợi của các thành phần tương tác trên mobile.

Ảnh chụp chỉ là nguồn tham chiếu bố cục và trải nghiệm. Không được nhập cứng tên sản phẩm, SKU, giá, kích thước, review, tên nghệ nhân hoặc hình ảnh từ sản phẩm trong ảnh.

### 2.2. Chương trình giảm giá

Đọc `sale-off-event-template.md` và dùng các thông tin trong file này để xây dựng phần hiển thị chương trình giảm giá trên product page.

### 2.3. Styling

**Tham chiếu đến design system từ coding rules đã đọc trước đó.**

Không tạo một hệ styling độc lập, không tự đặt thêm design token và không mô tả lại quy tắc styling trong task này.

---

## 3. Phạm vi công việc

Task bao gồm:

1. Xây dựng bố cục product page theo thứ tự được mô tả trong tài liệu này.
2. Kết nối các khối với dữ liệu Shopify thực tế.
3. Xử lý thay đổi variant và trạng thái product form.
4. Hiển thị thông tin discount active đúng đối tượng, đúng thời gian và đúng điều kiện.
5. Bổ sung các trạng thái thiếu dữ liệu, hết hàng, không khả dụng và lỗi thêm vào giỏ.
6. Bảo đảm accessibility cơ bản cho form, gallery, accordion và các nút tương tác.
7. Giữ tương thích với Shopify theme editor và cấu trúc theme hiện tại.

Task không bao gồm:

- Cài mới hoặc thay thế app review.
- Tự tạo discount mới trong Shopify Admin.
- Thay đổi điều kiện của discount đang active.
- Gọi Shopify Admin API trực tiếp từ trình duyệt.
- Nhúng Admin API access token hoặc secret vào Liquid, JavaScript hay asset public.
- Xây dựng một hệ thống subscription mới.

---

## 4. Bố cục trang chi tiết sản phẩm

Thứ tự khối nội dung trên mobile phải bám sát ảnh tham chiếu như sau.

## 4.1. Khối người chế tác

Hiển thị ở đầu phần thông tin sản phẩm:

- Ảnh đại diện hình tròn.
- Nhãn ngắn, ví dụ `CRAFTED BY`.
- Tên người chế tác.
- Có thể liên kết đến trang giới thiệu người chế tác nếu dữ liệu có URL hợp lệ.

Nguồn dữ liệu ưu tiên:

1. Product metafield tham chiếu đến metaobject người chế tác.
2. Product metafield riêng cho tên, ảnh và URL.
3. Nếu không có dữ liệu thì ẩn toàn bộ khối, không để khoảng trống và không hiển thị dữ liệu mẫu.

Không nhập cứng tên `Ngoc Vo`.

## 4.2. Tiêu đề sản phẩm

Hiển thị product title ngay sau khối người chế tác.

Yêu cầu:

- Dùng `product.title`.
- Chỉ có một heading chính `h1` cho tên sản phẩm.
- Không lặp lại product title ở một vị trí khác trong phần main product.
- Cho phép tiêu đề dài xuống nhiều dòng mà không làm vỡ layout.

## 4.3. Khối giá trị sử dụng theo năm

Ảnh tham chiếu có khối nội dung dạng:

`$45.05/year · 20+ year lifespan — An heirloom piece, not fast furniture`

Khối này phải dùng dữ liệu động.

Nguồn dữ liệu đề xuất:

- `product.metafields.custom.expected_lifespan_years`: số năm sử dụng kỳ vọng.
- `product.metafields.custom.lifespan_message`: nội dung mô tả bổ sung, nếu có.

Cách tính:

```text
annualized_cost = selected_variant.price / expected_lifespan_years
```

Yêu cầu:

- Giá theo năm phải cập nhật khi selected variant thay đổi giá.
- Dùng định dạng tiền tệ theo currency của shop.
- Nếu không có lifespan hợp lệ hoặc giá trị nhỏ hơn hay bằng 0 thì ẩn toàn bộ khối.
- Không mặc định mọi sản phẩm đều có tuổi thọ 20 năm.
- Không trình bày nội dung này như hình thức trả góp, thuê bao hoặc phí hằng năm.

## 4.4. SKU

Hiển thị SKU của variant hiện tại.

Yêu cầu:

- Dùng SKU của `selected_or_first_available_variant` khi trang vừa tải.
- Cập nhật ngay khi khách đổi variant.
- Nếu variant không có SKU thì ẩn dòng SKU thay vì hiển thị giá trị rỗng.

## 4.5. Rating, review và câu hỏi

Hiển thị ngay trước gallery:

- Số sao hoặc biểu diễn rating hiện có.
- Điểm trung bình.
- Tổng số review.
- Liên kết đến khu vực review.
- Liên kết đến khu vực câu hỏi nếu theme hoặc app hiện tại có hỗ trợ.

Yêu cầu:

- Tái sử dụng dữ liệu và snippet của app review hoặc standard review metafields đang có trong project.
- Không tạo review count giả.
- Không nhập cứng `4.9`, `390+ reviews` hoặc `30 Questions`.
- Liên kết phải cuộn hoặc điều hướng đúng đến nội dung tương ứng.
- Nếu không có dữ liệu rating thì ẩn khối rating theo quy tắc hiện có của theme.

## 4.6. Product media gallery

Gallery nằm sau rating và trước giá sản phẩm.

Cần hỗ trợ:

- Hiển thị toàn bộ media hợp lệ của sản phẩm.
- Ảnh chính lớn.
- Điều hướng giữa các media.
- Chỉ báo vị trí hiện tại tương tự pagination dots trong ảnh tham chiếu.
- Nút mở ảnh hoặc zoom khi theme hiện tại hỗ trợ.
- Đồng bộ media theo variant nếu variant có featured media.
- Hỗ trợ ảnh và các media type mà theme hiện tại đã hỗ trợ.
- Giữ alt text từ Shopify media.

Hành vi:

- Khi đổi variant, gallery chuyển đến featured media của variant nếu có.
- Pagination phản ánh đúng số lượng media.
- Không tạo dot thừa.
- Nút điều hướng phải có accessible label.

## 4.7. Giá sản phẩm

Hiển thị sau gallery và trước variant picker.

Yêu cầu:

- Hiển thị giá của selected variant.
- Hiển thị compare-at price và trạng thái giảm giá gốc nếu dữ liệu sản phẩm thực tế có compare-at price.
- Cập nhật giá khi variant thay đổi.
- Không thay main product price bằng giá ước tính của chương trình automatic discount.
- Không giả lập rằng automatic discount đã được áp dụng vào product price trước khi đủ điều kiện.

Ngay gần khối giá phải có khu vực thông báo chương trình giảm giá active được mô tả tại mục 6.

## 4.8. Variant picker

Hiển thị sau giá và promotion notice.

Bố cục theo ảnh tham chiếu:

- Tên option ở bên trái.
- Giá trị đang chọn ở bên phải.
- Các giá trị option hiển thị thành button hoặc swatch bên dưới.
- Giá trị hiện tại có trạng thái selected rõ ràng.

Yêu cầu chức năng:

- Hỗ trợ một hoặc nhiều product option.
- Không giả định option luôn có tên `Size`.
- Khi thay đổi option, resolve đúng variant.
- Cập nhật URL bằng `?variant=<variant_id>` mà không reload toàn trang nếu kiến trúc hiện tại hỗ trợ.
- Cập nhật hidden input `name="id"` trong product form.
- Cập nhật giá, compare-at price, SKU, media, availability, annualized cost và CTA.
- Option không tạo thành variant hợp lệ phải có trạng thái unavailable.
- Variant hết hàng phải được phân biệt với variant không tồn tại.

## 4.9. Private design consultation

Hiển thị một card tùy chọn sau variant picker, tương tự ảnh tham chiếu:

- Checkbox.
- Tiêu đề dịch vụ.
- Badge ngắn nếu có.
- Mô tả dịch vụ.

Phương án triển khai mặc định:

- Dùng line item property khi dịch vụ miễn phí và chỉ cần lưu lựa chọn cùng line item.

Ví dụ dữ liệu gửi vào cart:

```text
properties[Private design consultation] = Requested
```

Yêu cầu:

- Toàn bộ nội dung phải lấy từ section setting, block setting, product metafield hoặc metaobject.
- Chỉ hiển thị khi tính năng được bật và có đủ nội dung tối thiểu.
- Checkbox phải được liên kết đúng với label.
- Khi không chọn, không gửi property rỗng không cần thiết.
- Nếu sản phẩm có subscription hoặc selling plan, lựa chọn consultation không được làm hỏng product form.
- Không tự thêm một sản phẩm dịch vụ riêng vào cart trừ khi project đã có yêu cầu rõ ràng cho cơ chế add-on product.

Nên có một dòng giải thích ngắn về bước tiếp theo, ví dụ khách sẽ được liên hệ sau khi đặt hàng để lên lịch.

## 4.10. Các quyền lợi và cam kết mua hàng

Hiển thị sau consultation và trước product form CTA.

Theo ảnh tham chiếu, gồm các mục dạng hàng có icon, tiêu đề và nút mở nội dung:

- Express Delivery & Easy Setup.
- 30-Day Returns.
- 1-Year Warranty.
- Shipping Insurance.

Yêu cầu:

- Triển khai dưới dạng accordion hoặc disclosure có thể mở/đóng.
- Tên, icon và nội dung chi tiết phải lấy từ section blocks, metaobject hoặc metafield.
- Không nhập cứng chính sách nếu cửa hàng đã có nguồn dữ liệu policy khác.
- Nội dung hiển thị phải khớp chính sách thực tế của store.
- Không tự suy diễn rằng shipping discount đồng nghĩa với miễn phí vận chuyển.
- Mỗi disclosure phải dùng button hoặc semantic `details/summary` phù hợp.
- Cập nhật `aria-expanded` nếu dùng custom accordion.

## 4.11. Quantity selector và Add to cart

Hiển thị cùng một khu vực theo ảnh tham chiếu:

- Quantity selector ở bên trái.
- Nút Add to cart ở bên phải.

Yêu cầu:

- Quantity có nút giảm, giá trị hiện tại và nút tăng.
- Giá trị tối thiểu là 1, trừ khi business rule hiện tại cho phép khác.
- Tôn trọng quantity rules của variant nếu store đang sử dụng chúng.
- Add to cart phải gửi đúng variant ID, quantity, selling plan và line item properties.
- Hỗ trợ trạng thái loading.
- Ngăn submit lặp lại trong lúc request đang xử lý.
- Hiển thị lỗi add-to-cart rõ ràng trong live region.
- Sau khi thêm thành công, dùng hành vi cart hiện có của theme: mở cart drawer, hiển thị thông báo hoặc chuyển trang.

Trạng thái CTA tối thiểu:

- `Add to cart` khi variant có thể mua.
- `Sold out` khi variant tồn tại nhưng hết hàng và không cho backorder.
- `Unavailable` khi tổ hợp option không tồn tại.
- Trạng thái pre-order chỉ dùng khi project đã có logic pre-order thực tế.

## 4.12. Dynamic checkout

Hiển thị sau Add to cart:

- Shopify dynamic checkout button, bao gồm Shop Pay khi Shopify xác định phù hợp.
- Liên kết hoặc cơ chế `More payment options` theo hành vi native của Shopify.

Yêu cầu:

- Ưu tiên dùng cơ chế native của Shopify, ví dụ `{{ form | payment_button }}` trong đúng product form.
- Không tự dựng nút Shop Pay giả.
- Dynamic checkout phải nhận đúng selected variant, quantity, selling plan và line item properties trong giới hạn Shopify hỗ trợ.
- Nếu consultation là thông tin bắt buộc phải được giữ khi đi qua dynamic checkout, cần kiểm thử thực tế; không giả định chỉ dựa trên giao diện.

---

## 5. Thứ tự nội dung bắt buộc

Trên mobile, phần main product phải theo thứ tự:

1. Người chế tác.
2. Product title.
3. Giá trị sử dụng theo năm.
4. SKU.
5. Rating, review và questions.
6. Product media gallery.
7. Product price.
8. Thông báo chương trình giảm giá active.
9. Variant picker.
10. Private design consultation.
11. Purchase benefits / policy disclosures.
12. Quantity selector và Add to cart.
13. Dynamic checkout button.
14. More payment options.

Không thay đổi thứ tự này nếu không có xung đột kỹ thuật rõ ràng với cấu trúc theme hiện tại. Nếu phải thay đổi, cần ghi lại lý do trong phần bàn giao.

Ảnh tham chiếu là bố cục mobile. Với tablet và desktop, giữ nguyên thứ tự nội dung logic và áp dụng cấu trúc responsive theo coding rules cùng design system hiện có.

---

## 6. Chương trình giảm giá đang active

## 6.1. Thông tin nguồn

Sử dụng đúng các thông tin sau từ `sale-off-event-template.md`:

| Trường | Giá trị |
|---|---|
| Tên chương trình | Khai trương cửa hàng Sale Off |
| Trạng thái | ACTIVE |
| Loại discount | Automatic |
| Kiểu discount | `DiscountAutomaticBasic` |
| Khách hàng áp dụng | Tất cả khách hàng |
| Mức giảm | 50% |
| Phạm vi | Collection cụ thể |
| Minimum subtotal | $100.00 USD |
| One-time purchase | Có |
| Subscription | Không |
| Bắt đầu UTC | `2026-06-27T14:02:06Z` |
| Kết thúc UTC | `2026-07-09T03:59:59Z` |
| Kết thúc EDT | 23:59:59 ngày 08/07/2026, UTC-4 |
| Target collection | A Home Shared with Life |
| Target collection GID | `gid://shopify/Collection/475413217337` |
| Target collection numeric ID | `475413217337` |
| Kết hợp order discount | Không |
| Kết hợp product discount | Không |
| Kết hợp shipping discount | Có |

Thông tin kỹ thuật nội bộ:

```text
DiscountNode GID: gid://shopify/DiscountAutomaticNode/1258939416633
```

Không hiển thị GID, numeric ID, usage count hoặc recurring cycle limit cho khách hàng.

## 6.2. Điều kiện hiển thị promotion notice

Chỉ hiển thị promotion notice trên product page khi đồng thời thỏa mãn:

1. Thời gian hiện tại nằm trong khoảng bắt đầu và kết thúc của chương trình.
2. Product hiện tại thuộc collection `A Home Shared with Life`.
3. Chương trình được đánh dấu enabled/active trong nguồn cấu hình storefront.
4. Ngữ cảnh mua là one-time purchase hoặc chưa chọn subscription.

Không hiển thị promotion notice khi:

- Product không thuộc target collection.
- Chương trình chưa bắt đầu hoặc đã kết thúc.
- Khách đang chọn subscription/selling plan không được chương trình hỗ trợ.
- Dữ liệu cấu hình discount không đầy đủ hoặc không xác định được eligibility an toàn.

## 6.3. Nội dung hướng tới khách hàng

Promotion notice phải truyền đạt tối thiểu:

- Giảm 50%.
- Tự động áp dụng.
- Không cần mã giảm giá.
- Áp dụng cho đơn đủ điều kiện từ $100 USD.
- Chỉ áp dụng cho sản phẩm thuộc collection được chỉ định.
- Áp dụng cho one-time purchase, không áp dụng cho subscription.
- Thời điểm kết thúc chương trình.

Nội dung gợi ý:

```text
Khai trương cửa hàng: Giảm 50% tự động cho sản phẩm đủ điều kiện khi đơn hàng đạt từ $100 USD. Không cần mã. Áp dụng cho mua một lần và kết thúc lúc 23:59:59 EDT ngày 08/07/2026.
```

Có thể điều chỉnh câu chữ theo ngôn ngữ storefront, nhưng không được thay đổi ý nghĩa hoặc điều kiện.

## 6.4. Quy tắc hiển thị giá trong chương trình sale

Đây là automatic discount có minimum subtotal. Vì vậy:

- Main product price vẫn phải là giá thực của selected variant.
- Không ghi đè `variant.price` bằng giá giảm 50%.
- Không dùng giá giảm ước tính làm giá bán chính.
- Không hiển thị sale badge theo cách khiến khách tin rằng discount chắc chắn đã được áp dụng khi cart chưa đủ $100.
- Shopify cart/checkout là nguồn xác nhận cuối cùng về discount thực nhận.

Nếu có hiển thị giá tham khảo sau giảm, phải đáp ứng toàn bộ điều kiện sau:

1. Gắn nhãn rõ là `Giá ước tính sau ưu đãi` hoặc nội dung tương đương.
2. Hiển thị kèm điều kiện đơn tối thiểu $100.
3. Cập nhật theo selected variant.
4. Không thay thế main price.
5. Không hiển thị khi subscription được chọn.
6. Không cam kết kết quả nếu cart còn có discount khác không thể kết hợp.

Công thức tham khảo:

```text
estimated_discounted_price = selected_variant.price × 0.5
```

Việc hiển thị giá ước tính là tùy chọn. Promotion notice mô tả điều kiện là bắt buộc.

## 6.5. Quy tắc kết hợp discount

Thông tin cần thể hiện trong phần điều khoản mở rộng hoặc tooltip, không cần đưa toàn bộ vào dòng chính:

- Không kết hợp với order discount khác.
- Không kết hợp với product discount khác.
- Có thể kết hợp với shipping discount nếu Shopify xác nhận cả hai discount đều đủ điều kiện.

Không diễn giải `shipping discounts: true` thành miễn phí vận chuyển.

## 6.6. Kiểm tra thời gian

Nhúng timestamp dạng ISO UTC vào HTML data attributes hoặc cấu hình JavaScript:

```html
<div
  data-sale-start="2026-06-27T14:02:06Z"
  data-sale-end="2026-07-09T03:59:59Z"
></div>
```

So sánh bằng timestamp tuyệt đối:

```text
Date.now() >= startTimestamp && Date.now() <= endTimestamp
```

Không parse chuỗi ngày theo định dạng phụ thuộc locale.

Nếu có countdown:

- Countdown chỉ là thông tin bổ sung.
- Khi hết thời gian, ẩn promotion notice hoặc chuyển về trạng thái kết thúc mà không cần reload trang.
- Không dùng countdown làm nguồn duy nhất để quyết định Shopify có áp dụng discount hay không.

## 6.7. Xác định product thuộc target collection

Ưu tiên kiểm tra bằng collection ID hoặc handle ổn định từ dữ liệu Shopify.

Target collection:

```text
Name: A Home Shared with Life
GID: gid://shopify/Collection/475413217337
Numeric ID: 475413217337
```

Không chỉ so sánh bằng collection title vì title có thể thay đổi.

Nếu theme chỉ có dữ liệu Liquid:

- Duyệt `product.collections` và so sánh collection ID hoặc handle đã cấu hình.
- Không gọi Admin GraphQL từ client-side.

Nếu project có backend hoặc quy trình đồng bộ:

- Có thể dùng Admin GraphQL để đọc `discountAutomaticNodes` và đồng bộ dữ liệu sale sang metaobject, shop metafield hoặc cấu hình storefront an toàn.
- Không đưa Admin API token ra frontend.

## 6.8. Nguồn dữ liệu storefront cho sale event

Shopify Liquid storefront không nên phụ thuộc trực tiếp vào Admin DiscountNode. Chọn một trong các phương án phù hợp với kiến trúc hiện có:

### Phương án ưu tiên

Lưu sale event trong shop metaobject hoặc shop metafield được đồng bộ từ dữ liệu Admin:

```text
sale_event.enabled
sale_event.title
sale_event.discount_percentage
sale_event.minimum_subtotal
sale_event.starts_at
sale_event.ends_at
sale_event.target_collection_id
sale_event.one_time_purchase_enabled
sale_event.subscription_enabled
sale_event.combines_with_shipping_discount
```

### Phương án thay thế

Dùng section/theme settings nếu project chưa có metaobject hoặc quy trình đồng bộ.

Yêu cầu chung:

- Có một nguồn dữ liệu storefront rõ ràng.
- Không rải các constant của event tại nhiều file.
- Không hardcode cùng một timestamp ở nhiều component.
- Tách logic eligibility khỏi phần render UI.

---

## 7. Dữ liệu Shopify và nguồn dữ liệu đề xuất

| Nội dung | Nguồn ưu tiên |
|---|---|
| Product title | `product.title` |
| Product media | `product.media` |
| Variant | `product.variants` và selected variant |
| Price | `variant.price` |
| Compare-at price | `variant.compare_at_price` |
| SKU | `variant.sku` |
| Availability | `variant.available` |
| Option values | `product.options_with_values` |
| Crafted by | Product metafield → metaobject reference |
| Lifespan | Product metafield dạng integer |
| Lifespan message | Product metafield |
| Consultation | Product metafield, metaobject hoặc section block |
| Purchase benefits | List metaobject references hoặc section blocks |
| Rating/reviews | App review hiện có hoặc standard review metafields |
| Sale event | Shop metaobject, shop metafield hoặc một config storefront tập trung |
| Target sale collection | Collection ID/handle từ sale event config |

Mọi khối optional phải tự ẩn khi dữ liệu không tồn tại.

---

## 8. Yêu cầu kỹ thuật

## 8.1. Liquid

- Tái sử dụng section và snippet hiện có trước khi tạo file mới.
- Không đặt business logic lớn trực tiếp trong markup nếu có thể tách thành snippet hoặc JavaScript module rõ ràng.
- Product form phải dùng Shopify product form hợp lệ.
- Không tạo nested form.
- Không render trùng hidden variant ID input.
- Không làm mất block attributes cần cho theme editor.
- Mọi setting mới phải có schema hợp lệ.
- Nội dung optional phải kiểm tra blank trước khi render.

## 8.2. JavaScript

JavaScript của product page chịu trách nhiệm tối thiểu cho:

- Resolve selected variant.
- Cập nhật URL variant.
- Cập nhật price, compare-at price và SKU.
- Cập nhật availability và CTA.
- Cập nhật annualized cost.
- Đồng bộ gallery với featured media của variant.
- Cập nhật selected value của option.
- Cập nhật trạng thái sale notice theo thời gian.
- Ẩn promotion notice nếu subscription được chọn.
- Xử lý add-to-cart theo kiến trúc cart hiện có.

Yêu cầu:

- Không gắn event listener trùng khi section được load lại trong theme editor.
- Hỗ trợ section load/unload nếu theme hiện tại dùng Shopify theme editor events.
- Không phụ thuộc vào text hiển thị để tìm variant.
- Dùng variant ID và option values làm dữ liệu nguồn.
- Có guard khi element không tồn tại.
- Không gây lỗi toàn trang khi một block optional bị ẩn.

## 8.3. Cart và discount

- Không tự trừ 50% trong cart bằng JavaScript.
- Không tạo line item price giả.
- Không gửi discount code vì đây là automatic discount.
- Sau khi add-to-cart, cart UI phải cho Shopify cập nhật discount allocation theo cơ chế hiện có.
- Nếu cart drawer hiển thị discount, dùng dữ liệu cart response thực tế thay vì tính tay.
- Minimum subtotal $100 phải được hiểu là điều kiện của discount Shopify, không phải validation chặn Add to cart.

## 8.4. Accessibility

Tối thiểu phải có:

- Một `h1` duy nhất cho product title.
- Label đúng cho quantity input và option controls.
- Variant buttons có trạng thái selected có thể đọc được.
- Checkbox consultation có label liên kết.
- Accordion hỗ trợ keyboard và trạng thái mở/đóng.
- Gallery controls có accessible name.
- Product form error dùng live region.
- Loading state không làm mất focus.
- Nút disabled dùng thuộc tính phù hợp, không chỉ thay đổi giao diện.

## 8.5. SEO và structured data

- Không tạo Product JSON-LD thứ hai nếu theme đã có structured data.
- Dữ liệu Product/Offer phải dùng giá thật của variant, không dùng giá automatic discount ước tính làm `price` nếu Shopify chưa áp dụng.
- Availability trong structured data phải khớp trạng thái sản phẩm thực.
- Review aggregate chỉ được render khi có dữ liệu review thật.
- Không đưa line item property consultation thành một product offer riêng nếu nó không phải sản phẩm có giá.

---

## 9. Cấu trúc component đề xuất

Tên file phải thích nghi với cấu trúc theme hiện tại. Không bắt buộc tạo đúng các tên dưới đây nếu project đã có component tương đương.

```text
sections/
└── main-product.liquid

snippets/
├── product-craftsperson.liquid
├── product-annualized-cost.liquid
├── product-rating-summary.liquid
├── product-media-gallery.liquid
├── product-price.liquid
├── product-sale-notice.liquid
├── product-variant-picker.liquid
├── product-consultation.liquid
├── product-benefits.liquid
├── quantity-input.liquid
└── product-buy-buttons.liquid

assets/
├── product-info.js
├── product-gallery.js
├── product-form.js
└── sale-event.js
```

Nguyên tắc:

- Không tạo file mới nếu theme đã có snippet/function tương ứng.
- Không sao chép hai implementation variant picker hoặc product form cùng tồn tại.
- Promotion logic nên tập trung tại một module hoặc snippet duy nhất.

---

## 10. Trạng thái và fallback bắt buộc

| Trường hợp | Kết quả mong đợi |
|---|---|
| Không có craftsperson | Ẩn khối crafted by |
| Không có lifespan | Ẩn annualized cost |
| Không có SKU | Ẩn dòng SKU |
| Không có review | Ẩn rating summary theo quy tắc theme |
| Không có consultation | Ẩn card consultation |
| Không có benefit blocks | Không render container rỗng |
| Product không thuộc sale collection | Không hiển thị sale notice |
| Sale chưa bắt đầu | Không hiển thị sale notice |
| Sale đã kết thúc | Tự ẩn sale notice |
| Subscription được chọn | Ẩn hoặc vô hiệu promotion notice và giải thích không áp dụng |
| Variant available | Enable Add to cart |
| Variant sold out | Disable CTA và hiển thị Sold out |
| Tổ hợp option không tồn tại | Disable CTA và hiển thị Unavailable |
| Add-to-cart lỗi | Hiển thị lỗi có thể đọc được |
| Media rỗng | Không render gallery controls rỗng |

---

## 11. Test cases bắt buộc

## 11.1. Product và variant

1. Product một variant.
2. Product nhiều variant có cùng giá.
3. Product nhiều variant có giá khác nhau.
4. Variant có compare-at price.
5. Variant không có SKU.
6. Variant có featured media riêng.
7. Variant sold out.
8. Tổ hợp option unavailable.
9. Product không có metafield optional.

## 11.2. Sale event

1. Product thuộc collection `475413217337`, đang trong thời gian active.
2. Product không thuộc target collection.
3. Thời gian trước `2026-06-27T14:02:06Z`.
4. Thời gian sau `2026-07-09T03:59:59Z`.
5. One-time purchase được chọn.
6. Subscription được chọn.
7. Variant giá dưới $100.
8. Variant giá từ $100 trở lên.
9. Cart có sản phẩm đủ điều kiện nhưng subtotal chưa đạt $100.
10. Cart đạt minimum subtotal và Shopify tự áp dụng 50%.
11. Cart có order discount hoặc product discount khác không thể kết hợp.
12. Cart có shipping discount đủ điều kiện kết hợp.
13. Kiểm tra thời điểm kết thúc theo UTC và EDT.

## 11.3. Product form

1. Add một sản phẩm, quantity 1.
2. Add quantity lớn hơn 1.
3. Add kèm consultation property.
4. Add không chọn consultation.
5. Add variant sold out.
6. Request add-to-cart lỗi mạng.
7. Bấm submit liên tục.
8. Dynamic checkout với selected variant hiện tại.

## 11.4. Responsive và interaction

1. Mobile theo thứ tự khối bắt buộc.
2. Tablet không đổi thứ tự logic.
3. Desktop không lặp thông tin hoặc product form.
4. Gallery swipe/click hoạt động.
5. Pagination không thừa.
6. Accordion dùng được bằng keyboard.
7. Variant picker dùng được bằng keyboard.
8. Theme editor reload section không tạo event listener trùng.

---

## 12. Tiêu chí nghiệm thu

Task được xem là hoàn thành khi:

- Bố cục mobile đúng thứ tự của ảnh tham chiếu.
- Toàn bộ dữ liệu sản phẩm lấy động từ Shopify.
- Variant change cập nhật đầy đủ giá, SKU, availability, media, URL và form ID.
- Product form thêm đúng variant và quantity vào cart.
- Consultation được gửi đúng dưới dạng line item property khi được chọn.
- Sale notice chỉ hiển thị cho product thuộc target collection và trong thời gian active.
- Sale notice nêu đúng 50%, minimum subtotal $100, automatic/no code, one-time purchase và thời gian kết thúc.
- Main product price không bị ghi đè bằng giá discount ước tính.
- Không hiển thị discount cho subscription.
- Không gọi Admin API từ frontend và không lộ access token.
- Không có container rỗng khi thiếu optional data.
- Không có lỗi Liquid schema, JavaScript console hoặc lỗi theme check liên quan đến phần đã sửa.
- Không phá vỡ cart drawer, dynamic checkout, review app hoặc các section product hiện có.
- Accessibility cơ bản của form, accordion và gallery đạt yêu cầu trong mục 8.4.

---

## 13. Yêu cầu bàn giao

Khi hoàn thành, cung cấp:

1. Danh sách file đã tạo hoặc chỉnh sửa.
2. Tóm tắt trách nhiệm của từng file.
3. Danh sách metafield, metaobject hoặc theme setting mới cần tạo.
4. Hướng dẫn nhập dữ liệu craftsperson, lifespan, consultation và purchase benefits.
5. Vị trí cấu hình sale event storefront.
6. Giải thích cách xác định product thuộc target collection.
7. Kết quả kiểm thử các test case chính.
8. Những phần không thể xác minh trong môi trường local, đặc biệt automatic discount tại Shopify checkout.
9. Mọi khác biệt bắt buộc so với bố cục ảnh tham chiếu và lý do.

---

## 14. Ràng buộc quan trọng

- Không hardcode dữ liệu của sản phẩm trong ảnh tham chiếu.
- Không hardcode review giả.
- Không tạo nút Shop Pay giả.
- Không tự giảm line item price bằng JavaScript.
- Không hiển thị `50% off` cho product ngoài target collection.
- Không áp dụng thông điệp sale cho subscription.
- Không coi shipping discount là free shipping.
- Không đưa Admin API credential vào storefront.
- Không tạo design system hoặc styling rules mới.
- Không thay đổi business rule của discount đã được mô tả trong `sale-off-event-template.md`.
