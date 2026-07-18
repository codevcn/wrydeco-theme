# Báo cáo crawl và import Wrydeco

## Kết quả tổng quan

- Trạng thái cuối cùng: Hoàn thành
- ASIN: B0H7H3HCTJ
- Link nguồn Amazon: https://www.amazon.com/dp/B0H7H3HCTJ
- Product title: Modern Wooden Record Stand with Turntable Storage Shelf
- Base price: $2,585.00 USD
- Swatch đã crawl: OPTION 4
- Số color swatch: 1
- Product Attributes: 18
- Product Media Gallery images: 9
- Product Media Gallery videos: 1
- A+ Content images: 0
- A+ Content videos: 0
- Product Videos: 2
- Customization types: 3
- Customization options: 7

## Xác minh crawl

- Delivery country: United States
- Delivery ZIP code: 90001
- Location applied: true
- Display currency: USD
- Currency verified: true
- Customize now found: true
- CAPTCHA: Không gặp CAPTCHA.
- JSON validate: PASS với auto/validate_crawl_json.cmd

## SEO và description

- Đã rewrite product.title theo chuẩn SEO.
- Đã rewrite product.about_this_item thành HTML với root class dm-tabs__rte.
- Đã thêm extra_fields ở cuối JSON.
- product.title length: 55
- page_title length: 55
- meta_description length: 156
- url_slug length: 50

## Xử lý ảnh/logo

- Script: process_product_images_with_logo.cmd
- Kết quả: Updated=9, skipped=0, failed=0
- 9 ảnh gallery đã được upload lên Shopify Files và cập nhật source_url trong JSON đã archive.

## CSV và import store

- CSV đã tạo: auto/warehouse/B0H7H3HCTJ.20260718T123607-1.csv
- CSV conversion: products=1, variants=4, images=7
- Shopify product ID: gid://shopify/Product/8346048888889
- Shopify handle: modern-wooden-record-stand-turntable-storage-shelf
- Import result: Created=1, skipped(existing)=0, failed=0
- uploaded.json đã ghi nhận product mới.

## Output files

- JSON crawl cuối cùng: crawl/B0H7H3HCTJ/B0H7H3HCTJ.json
- Report crawl chi tiết: crawl/B0H7H3HCTJ/report.md
- Debug folder: crawl/B0H7H3HCTJ/debug/
- JSON đã xử lý và archive: auto/warehouse/B0H7H3HCTJ.20260718T123607-1.json
- CSV đã import và archive: auto/warehouse/B0H7H3HCTJ.20260718T123607-1.csv

## Warnings

- In-app browser endpoint không khả dụng, nên Playwright được chạy trực tiếp trong phiên Node.
- Khi click thumbnail, visible image element của Amazon không cập nhật ổn định cho từng thumbnail; dữ liệu gallery đã được resolve từ Amazon image block data của đúng swatch OPTION 4 để tránh ghi URL trùng.
- Không tìm thấy URL ảnh/video trong A+ Content/Product Description.
- Product Videos item #2 không có title/poster rõ ràng trong DOM/script đã kiểm tra.
- Converter CSV bỏ option size đầu tiên theo rule có sẵn: 36"W x 34"H x 16"D.
- Converter CSV bỏ customization type Add On-Site Installation theo IGNORE_CUSTOMIZATION_TYPE.
- Importer bỏ qua metafield custom.author_info vì definition là metaobject_reference và cần GID/JSON value.

## Errors

- Không có lỗi dừng pipeline.
