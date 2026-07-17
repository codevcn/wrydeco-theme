## Thiết lập phiên Amazon US trước khi crawl

Ngay sau khi truy cập trang sản phẩm, phải chuyển delivery location của phiên Amazon sang Hoa Kỳ bằng ZIP code:

```text
90001
```

Mục tiêu:

- Amazon hiển thị giá bằng `USD`.
- Hiển thị đúng các tùy chọn dành cho thị trường Hoa Kỳ.
- Hiển thị nút `Customize now` nếu sản phẩm hỗ trợ customization.
- Không crawl dữ liệu trong khi phiên Amazon đang dùng vị trí Việt Nam hoặc hiển thị giá bằng `VND`.

Thực hiện bằng cách điều khiển trực tiếp giao diện Amazon trong Playwright:

1. Truy cập trang sản phẩm.

2. Mở mục `Deliver to`, `Update location` hoặc thành phần tương đương trên header.

3. Nhập ZIP code:

```text
90001
```

4. Nhấn `Apply`, `Done` hoặc nút xác nhận tương đương.

5. Chờ trang reload hoặc dữ liệu sản phẩm cập nhật hoàn tất.

6. Kiểm tra lại delivery location đang tương ứng với ZIP code `90001`.

7. Xác nhận giá sản phẩm đang hiển thị bằng ký hiệu `$` hoặc currency `USD`.

8. Chỉ bắt đầu crawl sau khi phiên Amazon US đã được thiết lập thành công.

Nếu Amazon yêu cầu đăng nhập để thay đổi location, hãy thử tiếp tục bằng chế độ guest trước. Không tự tạo tài khoản hoặc tự đăng nhập bằng thông tin không được cung cấp.

### Xác minh sau khi chuyển region

Trước khi crawl dữ liệu chính, phải kiểm tra:

- Delivery ZIP code là `90001`.
- Currency là `USD`.
- Giá hiển thị bằng dollar Mỹ.
- Trang không còn hiển thị giá bằng `VND`.
- Nút `Customize now` đã được kiểm tra sau khi chọn từng Color Swatch.
- URL hoặc nội dung trang đã ổn định sau khi location được cập nhật.

Không được chỉ đổi currency bằng cách tự quy đổi giá VND sang USD. Phải lấy trực tiếp giá USD đang hiển thị trên phiên Amazon US.

Nếu giá vẫn hiển thị bằng VND:

1. Không tiếp tục crawl price.
2. Kiểm tra lại delivery location.
3. Reload trang trong cùng browser context nếu cần.
4. Xác nhận ZIP code `90001` vẫn đang được áp dụng.
5. Ghi screenshot và thông tin debug nếu không thể chuyển sang USD.

Nếu không thể ép phiên sang Amazon US, đặt trạng thái crawl là `partial` hoặc `failed`, đồng thời ghi rõ nguyên nhân trong JSON và `report.md`.

````

Đồng thời, cập nhật phần `crawl_metadata` trong cấu trúc JSON thành:

```json
{
  "crawl_metadata": {
    "crawled_at": null,
    "status": "completed",
    "marketplace": "amazon.com",
    "delivery_country": "US",
    "delivery_zip_code": "90001",
    "display_currency": "USD",
    "location_applied": false,
    "currency_verified": false,
    "errors": [],
    "warnings": []
  }
}
````

Bổ sung các quy tắc sau vào phần **Quy tắc dữ liệu**:

```markdown
- `base_price.currency` phải là `USD` sau khi phiên Amazon US được thiết lập.
- Không tự chuyển đổi giá từ VND hoặc currency khác sang USD.
- Giá phải được lấy trực tiếp từ giao diện Amazon sau khi áp dụng ZIP code `90001`.
- Chỉ đặt `location_applied` thành `true` sau khi xác nhận location đã cập nhật.
- Chỉ đặt `currency_verified` thành `true` sau khi xác nhận giá hiển thị bằng USD.
- Nếu vẫn thấy giá VND, không được lưu giá đó làm product base price.
- Nếu một Color Swatch làm trang đổi ASIN hoặc reload, phải kiểm tra location và currency vẫn là US/USD trước khi lấy giá.
- Với mỗi Color Swatch, phải kiểm tra lại nút `Customize now` sau khi variation cập nhật hoàn tất.
```

Trong `report.md`, bổ sung mục sau:

```markdown
## Amazon session configuration

- Marketplace: amazon.com
- Delivery country: United States
- Delivery ZIP code: 90001
- Location applied:
- Display currency:
- Currency verified:
- Customize now found:
- Notes:
```

Cập nhật phần báo cáo cuối cùng để Agent phải xác nhận thêm:

```markdown
- Phiên Amazon đã được chuyển sang ZIP code `90001` hay chưa.
- Giá đã được xác minh là USD hay chưa.
- Nút `Customize now` xuất hiện ở bao nhiêu Color Swatch.
- Color Swatch nào không hiển thị nút `Customize now`.
```
