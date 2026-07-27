1. Đọc toàn bộ file `./human-reviews.md` để biết cách hành văn viết các review sản phẩm cho giống người bản xứ.
2. Đọc file `./template.csv` để biết cấu trúc viết review trong file CSV.
3. Với mỗi sản phẩm được khai báo trong file `./config.json`, bạn hãy thực hiện các bước sau:

- Bước 1 (BẮT BUỘC): Truy cập vào store Wrydeco bằng access token trong file `./.env` để đọc thông tin chi tiết của sản phẩm để viết review bám sát sản phẩm hơn, thay vì viết review chung chug.
- Bước 2: Chạy file `./auto/module-4/write_ratings_by_star.cmd` để tạo ra quy tắc về số lượng các review từ 1 đến 5 sao.
- Bước 3: Đọc file `./reviews-rule.txt` để xác định quy tắc tạo ra các review.
- Bước 4: Hãy đóng vai 1 người thường xuyên đặt hàng online để viết reviews (cho sản phẩm đã đọc được thông tin) vào file `./output/{product_id}-reviews.csv` theo quy tắc đã xác định (chỉ tạo reviews trong file CSV trong folder "output", ko tạo file bên ngoài folder này).
- Bước 5: Sau khi viết reviews trong file CSV xong, lặp lại các bước trên cho các sản phẩm còn lại.

4. Sau khi viết xong reviews thì thêm thông tin sản phẩm và thông tin tạo review vào file `./handled.json`.
5. Chạy file `./clean.cmd` để xóa các file tạm thời và các file không cần thiết.
6. Chạy file `./merge_csv.cmd` để gộp tất cả các file CSV reviews của các sản phẩm vào 1 file CSV duy nhất.
7. Viết báo cáo kết quả tạo reviews cho các sản phẩm vào file `./report.md`.
8. Khi xong việc, hãy chạy lệnh CLI `mod toast {message muốn thông báo}` để thông báo cho tôi biết.
