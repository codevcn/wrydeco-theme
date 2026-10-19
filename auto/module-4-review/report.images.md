# Báo cáo kết quả tạo Reviews (Images)

**Thời gian chạy:** 2026-08-11
**Module:** module-4 (image reviews)
**Tổng số sản phẩm xử lý:** 3
**Tổng số review đã tạo:** 13

## Chi tiết theo sản phẩm:

1. **Handcrafted Natural Wood Tree Branch Bookshelf for Living Room** (ID: 8355547054137)
   - Số review tạo: 4
   - Trạng thái: Upload ảnh thành công và ghi nhận review tốt

2. **Handcrafted Wooden Floor Sculpture Tall Rustic Art** (ID: 8355494395961)
   - Số review tạo: 4
   - Trạng thái: Upload ảnh thành công và ghi nhận review tốt

3. **Handcrafted Rustic Wood Tree Branch Floating Bookshelf** (ID: 8355782328377)
   - Số review tạo: 5
   - Trạng thái: Upload ảnh thành công và ghi nhận review tốt

## Các thao tác đã thực hiện:
- Đã đọc cấu hình từ `config.images.json`.
- Truy cập vào từng thư mục ảnh con của sản phẩm và upload lên CDN Shopify qua script `upload.images.cmd`.
- Đã sinh các JSON review kèm mô tả thực tế về bối cảnh trong ảnh và link CDN của ảnh, bổ sung vào trường `products.reviews`.
- Ánh xạ JSON ra file CSV trong folder `output`.
- Ghi dữ liệu đã xử lý vào `handled.images.json`.
- Chạy `clean.cmd` để dọn dẹp thư mục và chạy `merge_csv.cmd` để gộp toàn bộ thành `output/merged-reviews.csv`.
