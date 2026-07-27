1. Đọc toàn bộ file `./human-reviews.md` để biết cách hành văn viết các review sản phẩm cho giống người bản xứ.
2. Đọc file `./template.csv` để biết cấu trúc của file CSV cần viết reviews.
3. Với mỗi sản phẩm được khai báo trong file `./config.json`, bạn hãy:

- Chạy file `./auto/module-4/write_ratings_by_star.cmd` để tạo ra quy tắc về số lượng các review từ 1 đến 5 sao.
- Đọc file `./reviews-rule.txt` để xác định quy tắc tạo các review.
- Tạo reviews vào file `./output/{product_id}-reviews.csv` theo quy tắc đã xác định (chỉ tạo reviews trong file CSV trong folder "output", ko tạo file bên ngoài folder này).
- Sau khi tạo reviews trong file CSV xong, lặp lại các bước trên cho các sản phẩm còn lại.

6. Viết báo cáo kết quả tạo reviews cho các sản phẩm vào file `./report.md`.
7. Sau khi viết xong reviews thì thêm thông tin sản phẩm và thông tin tạo review vào file `./handled.json`.
8. Chạy file `./clean.cmd` để xóa các file tạm thời và các file không cần thiết.
9. Khi xong việc, hãy chạy lệnh CLI `mod toast {message muốn thông báo}` để thông báo cho tôi biết.
