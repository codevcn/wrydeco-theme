> Nếu có mâu thuẫn dữ liệu trong quá trình tạo review, hãy dừng toàn bộ quá trình tạo review và báo cho tôi biết.

1. Đọc toàn bộ file `./human-reviews.md` để biết cách hành văn viết các review sản phẩm cho giống người bản xứ.
   > QUAN TRỌNG: Các review phải mang tính "cá nhân hóa sâu sắc 100%". Tức là ở bước đọc thông tin chi tiết của sản phẩm bên dưới, sẽ phải dùng trí tuệ nhân tạo đọc kỹ tiêu đề và mô tả sản phẩm để tự tay viết hoàn toàn từng dòng review một (sẽ mất nhiều thời gian hơn để viết nhưng đổi lại sẽ có được các review mang tính chân thực cao).
2. Đọc file `./template.csv` để biết cấu trúc viết review trong file CSV.
3. Với mỗi sản phẩm được khai báo trong file `./config.images.json`, bạn hãy thực hiện lần lượt các bước sau:

- Bước 1 **(QUAN TRỌNG)**: Truy cập vào store Wrydeco bằng `./access-token.md` để đọc thông tin chi tiết của sản phẩm để viết review bám sát sản phẩm hơn, thay vì viết review chung chung.
- Bước 2 **(QUAN TRỌNG)**: **Đọc và xem trực tiếp từng file ảnh local** trong thư mục khai báo tại field `products.images_folder_path_to_add_into_csv` (ví dụ: `media/images/8355804676153`) **trước khi upload lên Shopify** để AI nắm rõ chi tiết nội dung, màu sắc, kiểu dáng, chất liệu và bối cảnh thực tế của sản phẩm trong ảnh.
- Bước 3 **(QUAN TRỌNG)**: Chạy file `./upload.images.cmd {folder_path}` (ví dụ: `.\upload.images.cmd "media/images/8355804676153"`) để tự động upload toàn bộ ảnh local trong thư mục của sản phẩm đang xử lý lên Shopify store và nhận về danh sách URL ảnh public (CDN) được tự động lưu vào mảng `products.images_file_paths_to_add_into_csv`.
- Bước 4: Chạy file `./write_ratings_by_star.images.cmd` để lấy chỉ tiêu số lượng sao từ 1 đến 5 sao cho các review.
- Bước 5: Đọc file `./reviews-rule.txt` để xác định chỉ tiêu tạo ra các review.
- Bước 6:
  - Dựa vào:
    - Cách hành văn viết review như người bản xứ.
    - Thông tin sản phẩm đã đọc được.
    - **Thông tin và nội dung hình ảnh thực tế đã đọc/xem ở Bước 2.**
  - Hãy đóng vai 1 người thường xuyên đặt hàng online để viết reviews (cho sản phẩm đã đọc được thông tin) vào file `./output/{product_id}-reviews.images.csv`. Gán các URL ảnh (CDN URL đã upload xong ở Bước 3) trong field `products.images_file_paths_to_add_into_csv` vào ngẫu nhiên 1 review (gán vào cột phù hợp trong file CSV), đảm bảo bất cứ review nào bạn tạo cũng đều có ảnh. **Quan trọng: 1 review chỉ được phép có 1 ảnh và ko gán 1 ảnh vào nhiều review khác nhau, 1 ảnh chỉ được phép thuộc 1 review thôi**.
  - Hãy viết cả những review phản hồi (reply) cho một số review đã viết, ưu tiên viết phản hồi cho các review có số sao thấp (3-4 sao) để tạo sự tương tác và tăng tính chân thực cho các review.
  - Chỉ tạo reviews trong file CSV trong folder "output", ko tạo reviews trong file bên ngoài folder "output".
- Bước 7: Sau khi viết reviews trong file CSV xong, lặp lại các bước trên cho các sản phẩm còn lại.

4. Sau khi viết xong reviews thì thêm thông tin sản phẩm và thông tin tạo review vào cuối file `./handled.images.json` (ko xóa nội dung hiện có).
5. Chạy file `./clean.cmd` để xóa các file tạm thời và các file không cần thiết.
6. Chạy file `./merge_csv.cmd` để gộp tất cả các file CSV reviews của các sản phẩm vào 1 file CSV duy nhất.
7. Viết báo cáo kết quả tạo reviews cho các sản phẩm vào file `./report.md`.
8. Khi xong việc, hãy chạy lệnh CLI `mod toast {message muốn thông báo}` để thông báo cho tôi biết.
