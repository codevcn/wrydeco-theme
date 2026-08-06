> QUAN TRỌNG: Nếu có mâu thuẫn dữ liệu trong quá trình tạo review, hãy dừng toàn bộ quá trình tạo review và báo cho tôi biết.

1. Đọc toàn bộ file `./human-reviews.md` để biết cách hành văn viết các review sản phẩm cho giống người bản xứ.

> QUAN TRỌNG: Các review phải mang tính "cá nhân hóa sâu sắc 100%". Tức là ở bước đọc thông tin chi tiết của sản phẩm bên dưới, sẽ phải dùng trí tuệ nhân tạo đọc kỹ tiêu đề và mô tả sản phẩm để tự tay viết hoàn toàn từng dòng review một (sẽ mất nhiều thời gian hơn để viết nhưng đổi lại sẽ có được các review mang tính chân thực cao).

2. Đọc file `./template.csv` để biết cấu trúc viết review trong file CSV.
3. Với mỗi sản phẩm được khai báo trong file `./config.json`, bạn hãy thực hiện các bước sau:

- Bước 1 **(QUAN TRỌNG)**: Truy cập vào store Wrydeco bằng `./access-token.md` để đọc thông tin chi tiết của sản phẩm để viết review bám sát sản phẩm hơn, thay vì viết review chung chug.
- Bước 2: Chạy file `./auto/module-4/write_ratings_by_star.cmd` để lấy chỉ tiêu số lượng sao từ 1 đến 5 sao cho các review.
- Bước 3: Đọc file `./reviews-rule.txt` để xác định chỉ tiêu tạo ra các review.
- Bước 4:
  - Dựa vào:
    - Cách hành văn viết review như người bản xứ.
    - Thông tin sản phẩm đã đọc được.
    - Thông tin hình ảnh đã lấy được.
  - Hãy đóng vai 1 người thường xuyên đặt hàng online để viết reviews (cho sản phẩm đã đọc được thông tin) vào file `./output/{product_id}-reviews.csv`. Quy tắc viết review: Ko được viết tên reviewer như bot (User 1 or ABC or myname123...), tên reviewer phải giống người thật, mail của reviewer phải là Gmail or Outlook.
  - Hãy viết cả những review phản hồi (reply) cho một số review đã viết (bao gồm cả các review 5 sao), ưu tiên viết phản hồi cho các review có số sao thấp (3-4 sao) để tạo sự tương tác và tăng tính chân thực cho các review.
  - Chỉ tạo reviews trong file CSV trong folder "output", ko tạo reviews trong file bên ngoài folder "output".

4. Sau khi viết xong reviews thì thêm thông tin sản phẩm và thông tin tạo review vào cuối file `./handled.json` (ko xóa nội dung hiện có).
5. Chạy file `./clean.cmd` để xóa các file tạm thời và các file không cần thiết.
6. Chạy file `./merge_csv.cmd` để gộp tất cả các file CSV reviews của các sản phẩm vào 1 file CSV duy nhất.
7. Viết báo cáo kết quả tạo reviews cho các sản phẩm vào file `./report.md`.
8. Khi xong việc, hãy chạy lệnh CLI `mod toast {message muốn thông báo}` để thông báo cho tôi biết.
