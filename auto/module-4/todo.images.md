> Nếu có mâu thuẫn dữ liệu trong quá trình tạo review, hãy dừng toàn bộ quá trình tạo review và báo cho tôi biết.

1. Đọc toàn bộ file `./human-reviews.md` để biết cách hành văn viết các review sản phẩm cho giống người bản xứ.

> QUAN TRỌNG: Các review phải mang tính "cá nhân hóa sâu sắc 100%". Tức là ở bước đọc thông tin chi tiết của sản phẩm bên dưới, sẽ phải dùng trí tuệ nhân tạo đọc kỹ tiêu đề và mô tả sản phẩm để tự tay viết hoàn toàn từng dòng review một (sẽ mất nhiều thời gian hơn để viết nhưng đổi lại sẽ có được các review mang tính chân thực cao).

2. Đọc file `./template.csv` để biết cấu trúc viết review trong file CSV.
3. Với mỗi sản phẩm được khai báo trong file `./config.images.json`, bạn hãy thực hiện lần lượt các bước sau:

- Bước 1 **(QUAN TRỌNG)**: Truy cập vào store Wrydeco bằng `./access-token.md` để đọc thông tin chi tiết của sản phẩm để viết review bám sát sản phẩm hơn, thay vì viết review chung chung.
- Bước 2: Truy cập vào từng folder con của folder `products.images_folder_path_to_add_into_csv`, ví dụ truy cập vào `./media/images/8355804676153/r1` ("r1" là Review ID), mỗi folder con là 1 review, ở mỗi folder con (folder con chứa các file ảnh review, nếu folder con có nhiều ảnh thì tức là review đó có nhiều ảnh) cần thực hiện tuần tự:
  - Bước 2.1: **Đọc trực tiếp từng file ảnh** trong folder con để nắm rõ chi tiết màu sắc, kiểu dáng, chất liệu, vị trí đặt và bối cảnh thực tế của sản phẩm trong ảnh. Bước này đã lấy được `thông tin về sản phẩm trong ảnh review`.
  - Bước 2.2: Chạy file `./upload.images.cmd "{folder_path}"` (ví dụ: `./upload.images.cmd "media/images/8355804676153/r1"`) để tự động upload toàn bộ file ảnh trong folder con lên Shopify store và nhận về danh sách URL ảnh public (CDN). Bước này đã lấy được `danh sách URL ảnh public (CDN)`.
  - Bước 2.3: Hãy đóng vai 1 người mua hàng online để tiến hành viết review. Hãy tạo 1 json object trong mảng `products.reviews` của sản phẩm đang xử lý. Mỗi json object là 1 review cho sản phẩm đang xử lý với các field như sau:
    - "review_id": "{Review ID}",
    - "product_handle": "{handle của sản phẩm đang xử lý}",
    - "product_id": "{ID của sản phẩm đang xử lý}",
    - "rating": {rating ngẫu nhiên từ 3-5 sao, tỷ lệ là: 3 sao: 10%, 4 sao: 40%, 5 sao: 50%},
    - "author": "{tên người viết review tham khảo từ file `./human-info-list.md`}",
    - "email": "{email của người viết review tham khảo từ file `./human-info-list.md`}",
    - "body": "{viết nội dung review dựa vào Cách hành văn viết review như người bản xứ, Thông tin sản phẩm đã đọc được ở Bước 1, Thông tin về sản phẩm trong ảnh review đã đọc được ở Bước 2.1, Danh sách URL ảnh public (CDN) đã upload xong ở Bước 2.2}",
    - "created_at": "{thời gian tạo review hiện tại theo format ISO 8601}",
    - "photo_urls": [{danh sách URL của ảnh review đã upload}],
    - "reply": "{phản hồi từ người bán, phản hồi các review theo tỷ lệ: 3 sao: 50%, 4 sao: 30%, 5 sao: 20%}",
    - "replied_at": "{thời gian phản hồi review hiện tại theo format ISO 8601, nếu không có phản hồi thì để chuỗi rỗng}",
    - "verified_purchase": {luôn là true},
    - "incentivized": {luôn là false},
  - Bước 2.4: Đọc file `./template.csv` để biết cấu trúc viết review trong file CSV, sau đó ánh xạ json object của review đã viết xong ở bước 2.3 vào file `./output/{product_id}-reviews.images.csv` (chỉ tạo reviews CSV trong folder "output", ko tạo reviews bên ngoài folder "output".).
  - Bước 2.5: hãy lưu lại toàn bộ thông tin sản phẩm và thông tin review đã viết vào file `./handled.images.json` (ko xóa nội dung hiện có).
  - Bước 2.6: Lặp lại các bước 2.1 đến 2.5 cho tất cả các folder con còn lại.
- Bước 4: Sau khi đã viết xong hết tất cả các review cho sản phẩm đang xử lý, tiếp tục với các sản phẩm còn lại trong file `./config.images.json`.

4. Chạy file `./clean.cmd` để xóa các file tạm thời và các file không cần thiết.
5. Chạy file `./merge_csv.cmd` để gộp tất cả các file CSV reviews của các sản phẩm vào 1 file CSV duy nhất.
6. Viết báo cáo kết quả tạo reviews cho các sản phẩm vào file `./report.md`.
7. Khi xong việc, hãy chạy lệnh CLI `mod toast {message muốn thông báo}` để thông báo cho tôi biết.
