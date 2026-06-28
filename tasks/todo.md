Hãy xây dựng khu vực lựa chọn biến thể sản phẩm trên trang chi tiết sản phẩm dựa theo ảnh tham chiếu đã cung cấp.

## Mục tiêu

Tạo một component lựa chọn biến thể gồm:

1. Thông tin màu đang được chọn.
2. Danh sách swatch màu hoặc chất liệu.
3. Danh sách kích thước.
4. Trạng thái kích thước hết hàng hoặc không khả dụng.

Component phải tích hợp đúng với product form và hệ thống variant hiện có. Không hard-code dữ liệu nếu thông tin tương ứng đã tồn tại trong Shopify product options và variants.

## 1. Bố cục tổng thể

Các thành phần được sắp xếp theo chiều dọc theo thứ tự:

```text
Thông tin màu hiện tại
Tên nhóm swatch
Danh sách swatch
Tiêu đề SIZES
Lưới nút kích thước
```

Toàn bộ component nằm trong khu vực thông tin sản phẩm, phía trên nút thêm vào giỏ hàng hoặc thay thế đúng vị trí của variant picker hiện tại.

Các nhóm nội dung cần có khoảng cách rõ ràng và được căn trái thống nhất.

Riêng phần styling, tham chiếu đến system design đã đọc được từ coding rules trước đó.

## 2. Dòng thông tin màu đang chọn

Ở đầu component hiển thị một dòng có cấu trúc:

```text
COLOR  Warm White
```

Trong đó:

- `COLOR` là nhãn cố định.
- `Warm White` là giá trị màu hoặc chất liệu đang được chọn.
- Hai phần nằm trên cùng một hàng.
- Giá trị đang chọn nằm ngay sau nhãn.
- Khi khách chọn swatch khác, tên màu phải được cập nhật ngay.

Không hiển thị edition, subtitle hoặc nội dung bổ sung sau tên màu.

## 3. Nhãn nhóm swatch

Ngay dưới dòng thông tin màu, hiển thị tên option tương ứng, ví dụ:

```text
Canvas
```

Tên nhóm phải lấy từ product option của Shopify, không hard-code nếu option name đã có sẵn.

Nhãn nằm trên một dòng riêng, phía trên danh sách swatch.

## 4. Danh sách swatch

Bên dưới tên option, hiển thị các lựa chọn màu hoặc chất liệu dưới dạng swatch hình tròn.

Theo ảnh tham chiếu:

- Các swatch nằm trên cùng một hàng.
- Các swatch được căn về bên trái.
- Swatch đang được chọn có vòng trạng thái active bao quanh.
- Một swatch có thể dùng một màu, nhiều vùng màu hoặc hình ảnh đại diện tùy dữ liệu sản phẩm.

Mỗi swatch phải là một button tương tác thực sự và có:

- `type="button"`.
- `aria-label` mô tả option.
- `aria-pressed="true"` khi đang được chọn.
- Trạng thái focus rõ ràng khi điều hướng bằng bàn phím.

Khi chọn swatch:

- Cập nhật option hiện tại.
- Tìm variant tương ứng.
- Cập nhật variant ID trong product form.
- Cập nhật tên màu đang hiển thị.
- Cập nhật trạng thái khả dụng của các size.
- Cập nhật giá, ảnh sản phẩm và trạng thái Add to cart nếu hệ thống hiện tại đã hỗ trợ.

Không xây swatch chỉ mang tính trang trí mà không liên kết với variant thực tế.

Nếu option có swatch image, color value, metafield hoặc metaobject tương ứng thì ưu tiên sử dụng dữ liệu đó.

## 5. Tiêu đề khu vực size

Sau danh sách swatch, hiển thị tiêu đề:

```text
SIZES
```

Tiêu đề:

- Nằm trên một dòng riêng.
- Căn trái.
- Không phải button.
- Nằm ngay phía trên lưới kích thước.

## 6. Lưới kích thước

Bên dưới tiêu đề `SIZES`, hiển thị các size dưới dạng lưới button.

Ví dụ thứ tự:

```text
5     5.5     6     6.5     7
7.5   8       8.5   9       9.5
10    10.5    11
```

Yêu cầu bố cục:

- Khi đủ chiều rộng, ưu tiên hiển thị 5 cột.
- Các button có cùng chiều rộng và chiều cao.
- Khoảng cách giữa các button đồng đều.
- Các size tự động xuống hàng.
- Dòng cuối căn trái.
- Không kéo giãn các button ở dòng cuối để lấp đầy container.
- Sử dụng CSS Grid hoặc cơ chế layout tương đương.
- Không chia thủ công dữ liệu thành từng hàng cố định.
- Thứ tự size phải dựa trên product option hoặc variants trong Shopify.

Mỗi button size phải:

- Hiển thị giá trị size ở giữa.
- Có `type="button"`.
- Không tự submit product form.
- Có trạng thái active khi được chọn.
- Có trạng thái focus rõ ràng.
- Có thuộc tính accessibility phù hợp.
- Cập nhật variant tương ứng khi được nhấn.

## 7. Trạng thái size đang chọn

Khi khách chọn một size:

- Xóa trạng thái active khỏi size trước đó.
- Đặt trạng thái active cho size mới.
- Cập nhật option đang chọn.
- Cập nhật variant ID trong product form.
- Cập nhật trạng thái còn hàng.
- Cập nhật Add to cart.
- Không reload toàn bộ trang.

Nếu tổ hợp giữa màu và size không tương ứng với một variant hợp lệ, size đó phải được xem là không khả dụng.

## 8. Trạng thái size không khả dụng

Theo ảnh tham chiếu, một size không khả dụng vẫn xuất hiện trong grid nhưng có đường chéo đi qua button.

Button không khả dụng cần:

- Giữ nguyên vị trí trong lưới.
- Không làm thay đổi bố cục khi trạng thái variant thay đổi.
- Có thuộc tính `disabled`.
- Có `aria-disabled="true"` khi phù hợp.
- Không thể chọn bằng chuột hoặc bàn phím.
- Hiển thị đường chéo thể hiện unavailable hoặc sold out.
- Vẫn hiển thị giá trị size để người dùng nhận biết.
- Có trạng thái giảm nhấn mạnh so với size khả dụng.

Trạng thái phải được xác định theo tổ hợp option hiện tại.

Ví dụ:

```text
Màu hiện tại + Size 8
```

Nếu tổ hợp này không có variant hoặc variant đã hết hàng thì size 8 phải được disabled.

## 9. Nguồn dữ liệu

Ưu tiên sử dụng dữ liệu Shopify hiện có:

```text
product.options_with_values
product.variants
product.selected_or_first_available_variant
variant.available
variant.options
```

Nếu theme đã có variant picker hoặc JavaScript quản lý variant thì phải tái sử dụng hoặc mở rộng logic hiện tại.

Không xây một hệ thống chọn variant thứ hai hoạt động song song.

Không được:

- Hard-code danh sách size.
- Hard-code tên màu.
- Hard-code variant ID.
- Dùng text hiển thị để suy đoán variant theo cách không ổn định.
- Làm mất khả năng mở sản phẩm bằng URL có variant ID.
- Làm hỏng product form hoặc Add to cart hiện tại.

## 10. Responsive

Trên màn hình nhỏ:

- Component giữ bố cục dọc.
- Swatch nằm trên một hàng và có thể xuống hàng nếu có nhiều lựa chọn.
- Lưới size tự điều chỉnh số cột phù hợp.
- Button không tràn container.
- Vùng nhấn đủ lớn cho thao tác cảm ứng.

Trên màn hình rộng:

- Component không bị kéo giãn quá mức.
- Các button size giữ kích thước cân đối.
- Nội dung tiếp tục căn trái giống ảnh tham chiếu.

Riêng phần styling, tham chiếu đến system design đã đọc được từ coding rules trước đó.

## 11. Yêu cầu code

- Phân tích cấu trúc theme hiện tại trước khi chỉnh sửa.
- Tách component thành snippet hoặc block phù hợp.
- Giữ semantic HTML.
- Không viết JavaScript inline nếu project đã có module hoặc file quản lý variant.
- Không đăng ký trùng event listener khi Shopify section được reload.
- Hỗ trợ Shopify Theme Editor và section rendering.
- Không phá vỡ variant picker hiện tại.
- Không thay đổi những phần không liên quan.
- Không thêm thư viện bên ngoài.
- Không tự tạo style khác với system design hiện có.

## 12. Kết quả cần bàn giao

Sau khi hoàn thành, hãy cung cấp:

1. Danh sách file đã tạo hoặc chỉnh sửa.
2. Toàn bộ code thay đổi của từng file.
3. Giải thích cách option và variant được ánh xạ vào UI.
4. Giải thích cách xác định size không khả dụng.
5. Vị trí gọi snippet hoặc block trên product page.
6. Các bước kiểm tra:
   - Chọn swatch.
   - Chọn size.
   - Size hết hàng.
   - Tổ hợp variant không tồn tại.
   - Add to cart đúng variant.
   - Reload trang bằng URL có variant ID.
   - Shopify Theme Editor.
   - Mobile và desktop.
