Hãy đọc source code hiện tại và triển khai logic cho popup tìm kiếm dựa trên ảnh tham chiếu tôi cung cấp.

Không cần tự đặt thêm quy tắc coding hoặc styling. Hãy tuân theo file CSS tham chiếu và file rule đã có trong project.

## Logic mở và đóng popup

- Popup tìm kiếm chỉ xuất hiện khi người dùng nhấn vào icon tìm kiếm trên Header.
- Sử dụng event `onPointerDown` để mở popup.
- Khi popup mở, hiển thị backdrop phía sau.
- Nhấn vào backdrop để đóng popup.
- Nhấn phím `Escape` để đóng popup.
- Nhấn bên trong popup không được làm popup đóng.
- Khi popup mở, tự động focus vào ô nhập tìm kiếm.

## Recently Searches

Thay mục `Trending Searches` trong ảnh thành:

`Recently Searches`

Khu vực này hiển thị những sản phẩm mà người dùng đã:

1. Tìm thấy trong kết quả tìm kiếm.
2. Nhấn vào card để truy cập trang chi tiết sản phẩm.

Không lưu từ khóa người dùng đã nhập. Chỉ lưu sản phẩm mà người dùng thực sự đã nhấn vào.

Mỗi sản phẩm gần đây cần lưu các thông tin cần thiết như:

- ID hoặc handle sản phẩm.
- Title sản phẩm.
- URL sản phẩm.
- Ảnh sản phẩm.

Yêu cầu:

- Lưu danh sách vào `localStorage`.
- Sau khi reload trang, danh sách vẫn còn.
- Sản phẩm mới nhấn được đưa lên đầu danh sách.
- Không tạo sản phẩm trùng lặp.
- Nếu sản phẩm đã tồn tại, đưa sản phẩm đó lên đầu danh sách.
- Giới hạn tối đa 8 sản phẩm.
- Nhấn vào một sản phẩm trong `Recently Searches` sẽ truy cập trang chi tiết của sản phẩm đó.
- Nếu chưa có sản phẩm nào thì không hiển thị danh sách sản phẩm gần đây.
- Nếu dữ liệu trong `localStorage` bị lỗi hoặc không hợp lệ thì bỏ qua dữ liệu lỗi và không làm crash giao diện.

## Logic tìm kiếm

- Theo dõi nội dung người dùng nhập vào ô tìm kiếm.
- Dùng giá trị sau khi đã `trim()`.
- Khi người dùng nhập ít hơn 2 ký tự:
  - Không gọi API tìm kiếm.
  - Không hiển thị danh sách kết quả sản phẩm.

- Khi người dùng nhập từ 2 ký tự trở lên:
  - Thực hiện tìm kiếm sản phẩm.
  - Sử dụng nguồn dữ liệu hoặc API tìm kiếm sản phẩm đang có trong project.
  - Không sử dụng mock data nếu project đã có dữ liệu sản phẩm thật.

- Debounce thao tác tìm kiếm khoảng 250–300 ms để tránh gửi request liên tục.
- Nếu người dùng thay đổi từ khóa nhanh, kết quả của request cũ không được ghi đè kết quả của request mới.

## Danh sách kết quả tìm kiếm

Khi từ khóa có ít nhất 2 ký tự, hiển thị danh sách các card sản phẩm bên trong popup.

Mỗi card sản phẩm bao gồm:

- Ảnh sản phẩm.
- Title sản phẩm.

Toàn bộ card có thể nhấn để truy cập trang chi tiết sản phẩm.

Khi người dùng nhấn vào một card kết quả:

1. Lưu sản phẩm đó vào `Recently Searches`.
2. Loại bỏ dữ liệu trùng nếu sản phẩm đã tồn tại.
3. Đưa sản phẩm vừa nhấn lên đầu danh sách.
4. Điều hướng đến trang chi tiết sản phẩm.

Nếu sản phẩm không có ảnh, xử lý bằng ảnh fallback hoặc cơ chế fallback hiện có trong project.

## Cuộn danh sách kết quả

- Khu vực danh sách kết quả tìm kiếm phải có thể cuộn độc lập khi có nhiều sản phẩm.
- Khi người dùng cuộn danh sách kết quả, trang phía sau không được cuộn theo ngoài ý muốn.
- Khi popup mở, ngăn trang phía sau cuộn.
- Khi popup đóng, khôi phục khả năng cuộn của trang.

## Các trạng thái cần xử lý

Popup tìm kiếm cần xử lý đầy đủ các trạng thái:

- Chưa nhập đủ 2 ký tự.
- Đang tìm kiếm.
- Có kết quả tìm kiếm.
- Không tìm thấy sản phẩm.
- Request tìm kiếm bị lỗi.
- Sản phẩm không có ảnh.
- Dữ liệu `localStorage` không hợp lệ.

Lỗi tìm kiếm không được làm crash popup hoặc toàn bộ trang.

## Luồng hoạt động mong muốn

1. Người dùng nhấn icon tìm kiếm bằng `onPointerDown`.
2. Popup và backdrop xuất hiện.
3. Ô tìm kiếm tự động được focus.
4. Nếu chưa nhập từ khóa, hiển thị `Recently Searches` nếu có dữ liệu.
5. Khi nhập ít nhất 2 ký tự, bắt đầu tìm kiếm sản phẩm.
6. Trong lúc tìm kiếm, hiển thị trạng thái loading.
7. Khi có kết quả, hiển thị danh sách card sản phẩm.
8. Danh sách kết quả có thể cuộn.
9. Khi nhấn vào card, lưu sản phẩm vào `Recently Searches`.
10. Sau đó điều hướng đến trang chi tiết sản phẩm.
11. Người dùng có thể đóng popup bằng backdrop, nút đóng hoặc phím `Escape`.

Sau khi hoàn thành, hãy cho tôi biết:

- Những file đã chỉnh sửa hoặc tạo mới.
- Logic tìm kiếm đang sử dụng API hoặc nguồn dữ liệu nào.
- Logic lưu và đọc `Recently Searches`.
- Luồng xử lý khi người dùng nhấn vào một sản phẩm.
- Cách kiểm tra thủ công toàn bộ tính năng.
