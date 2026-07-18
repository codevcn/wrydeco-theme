# Crawl dữ liệu sản phẩm Amazon bằng Playwright

Hãy trực tiếp sử dụng **Playwright** để mở trình duyệt và crawl trang Amazon sau:

```text
https://www.amazon.com/dp/B0H6FGCCVP
```

Không chỉ hướng dẫn hoặc phân tích. Hãy tự điều khiển trình duyệt trong phiên làm việc hiện tại, trực tiếp truy cập trang, scroll, click, mở modal, kiểm tra DOM/network và lưu kết quả thực tế.

## Yêu cầu bắt buộc

- Không tạo script crawler tự động.
- Không tạo file JavaScript, TypeScript, Python hoặc npm script để crawl.
- Không tạo script tải ảnh hoặc video.
- Không tải ảnh hoặc video về máy.
- Chỉ thu thập URL trực tiếp của ảnh và video.
- Có thể dùng Playwright evaluate, DOM inspection và network inspection trực tiếp trong phiên trình duyệt.
- Phải tạo file JSON kết quả và file báo cáo Markdown theo cấu trúc được chỉ định.
- Có thể ghi screenshot, HTML, network log hoặc dữ liệu trung gian vào folder `debug` trong quá trình crawl.

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
```

## Xử lý CAPTCHA

Nếu gặp CAPTCHA, Robot Check hoặc bước xác minh:

1. Giữ nguyên trình duyệt và trang hiện tại.
2. Không refresh, không đóng trình duyệt và không tự động vượt CAPTCHA.
3. Dừng thao tác và thông báo để tôi tự xử lý CAPTCHA trên trình duyệt.
4. Chờ tôi xác nhận đã hoàn thành.
5. Tiếp tục crawl trong đúng phiên trình duyệt hiện tại.

Không sử dụng dịch vụ giải CAPTCHA hoặc kỹ thuật né tránh hệ thống xác minh của Amazon.

## Cấu trúc đầu ra

Tạo cấu trúc sau:

```text
/crawl/
└── B0H6FGCCVP/
    ├── debug/
    ├── B0H6FGCCVP.json
    └── report.md
```

Trong đó:

- File dữ liệu chính:

```text
/crawl/B0H6FGCCVP/B0H6FGCCVP.json
```

- File báo cáo kết quả:

```text
/crawl/B0H6FGCCVP/report.md
```

- Dữ liệu debug:

```text
/crawl/B0H6FGCCVP/debug/
```

Không tạo folder riêng để chứa ảnh hoặc video vì chỉ cần lưu URL media vào file JSON.

## Dữ liệu cần crawl

### 1. Thông tin cơ bản

Thu thập:

- Product title.
- Product base price.
- Toàn bộ nội dung `About this item`.
- Toàn bộ Product Attributes hoặc Product Details dạng key-value.

Product Attributes phải được crawl động từ các khu vực như:

- Product overview.
- Product information.
- Product details.
- Technical details.
- Additional information.
- Các bảng hoặc cặp label-value tương đương.

Không hard-code danh sách thuộc tính.

Mỗi thuộc tính lưu theo dạng:

```json
{
  "key": "product_dimensions",
  "label": "Product Dimensions",
  "value": "80\"L x 60\"W x 20\"H",
  "raw_value": "80\"L x 60\"W x 20\"H"
}
```

Quy tắc:

- Chuyển `label` thành `snake_case` để tạo `key`.
- Vẫn giữ nguyên `label` và `raw_value`.
- Loại bỏ khoảng trắng thừa.
- Không ghi đè dữ liệu nếu nhiều thuộc tính có cùng key.
- Không gộp seller information, ranking hoặc warranty vào Product Attributes nếu chúng thuộc khu vực khác.

### 2. Product Media Gallery

Tìm khu vực Product Media Gallery ở phần đầu trang sản phẩm. Khu vực này thường được chia thành hai phần:

1. Danh sách ảnh hoặc video thu nhỏ (`thumbnail list`).
2. Khu vực hiển thị ảnh hoặc video lớn đang được chọn (`main/large media area`).

Phải crawl toàn bộ media trong gallery, bao gồm:

- Tất cả ảnh sản phẩm.
- Tất cả video sản phẩm.
- Media trong thumbnail carousel.
- Media chỉ xuất hiện sau khi click thumbnail hoặc mở modal gallery.

#### Quy trình bắt buộc khi crawl ảnh Product Media Gallery

Không được lấy URL ảnh trực tiếp từ danh sách thumbnail rồi ghi URL đó làm ảnh chính.

Với từng thumbnail ảnh trong danh sách ảnh nhỏ, phải thực hiện lần lượt:

1. Scroll thumbnail vào viewport nếu cần.
2. Click vào thumbnail để ảnh tương ứng được hiển thị trong khu vực ảnh lớn.
3. Chờ khu vực ảnh lớn cập nhật hoàn tất.
4. Xác nhận ảnh lớn đã thay đổi tương ứng với thumbnail vừa chọn, thông qua URL, thuộc tính DOM hoặc trạng thái selected.
5. Lấy URL từ chính phần tử ảnh lớn đang hiển thị, không lấy URL từ phần tử thumbnail.
6. Kiểm tra các nguồn ảnh độ phân giải cao của phần tử ảnh lớn, bao gồm nếu có:
   - `data-old-hires`
   - `data-a-dynamic-image`
   - `srcset`
   - `src`
   - URL ảnh được tải qua network khi ảnh lớn được chọn
7. Chọn URL có độ phân giải thực tế lớn nhất làm `resolved_url`.
8. Chỉ lưu URL thumbnail vào `thumbnail_url` để tham chiếu, không dùng thumbnail URL làm `source_url` hoặc `resolved_url`.
9. Tiếp tục với thumbnail kế tiếp cho đến khi đã duyệt hết danh sách.

Ví dụ URL ảnh nhỏ sau không được dùng làm ảnh chính:

```text
https://m.media-amazon.com/images/I/51SYulnawIL._AC_US100_.jpg
```

Các URL có transform kích thước nhỏ như sau cũng không được ghi vào `source_url` hoặc `resolved_url` của ảnh chính:

```text
_AC_US100_
_SS64_
_SX38_
```

Nếu phần tử ảnh lớn trả về nhiều candidate URL, ưu tiên theo thứ tự:

1. `data-old-hires` nếu là URL ảnh lớn hợp lệ.
2. Candidate có kích thước lớn nhất trong `data-a-dynamic-image`.
3. Candidate lớn nhất trong `srcset`.
4. `src` của ảnh lớn.
5. URL ảnh lớn quan sát được từ network request.

Sau đó có thể chuẩn hóa Amazon image transform để lấy phiên bản lớn nhất thực tế. Ưu tiên ảnh từ `1200px` trở lên nếu Amazon cung cấp, nhưng không được upscale giả.

Nếu sau khi click thumbnail mà chỉ lấy được URL ảnh nhỏ:

- Không ghi URL nhỏ đó vào `source_url` hoặc `resolved_url`.
- Vẫn có thể lưu nó vào `thumbnail_url`.
- Ghi warning vào JSON.
- Lưu screenshot hoặc DOM snapshot liên quan vào folder `debug`.

#### Với ảnh, lấy:

- `source_url`: URL lấy từ phần tử ảnh lớn đang hiển thị sau khi click thumbnail.
- `resolved_url`: URL ảnh lớn nhất hoặc ảnh gốc Amazon cung cấp.
- `thumbnail_url`: URL của thumbnail đã click, chỉ dùng để đối chiếu.
- Alt text nếu có.
- Thứ tự hiển thị theo danh sách thumbnail.

#### Với video, lấy:

- URL video thực tế.
- URL MP4 nếu có.
- URL HLS `.m3u8` nếu có.
- Poster hoặc thumbnail URL.
- Tiêu đề nếu có.
- Thứ tự hiển thị.

Với thumbnail video, có thể click thumbnail, mở media modal và kiểm tra DOM hoặc network request để lấy URL video thực tế.

### 3. A+ Content

Tìm khu vực A+ Content hoặc Product Description và lấy toàn bộ URL:

- Ảnh.
- Video.
- Poster video nếu có.

#### Với ảnh:

- Lấy URL trực tiếp từ DOM.
- Lấy URL ảnh gốc hoặc phiên bản lớn nhất.
- Ưu tiên chiều rộng từ `1200px` trở lên nếu có.
- Có thể loại bỏ hoặc thay đổi Amazon image transform như `_SX970_`.
- Không lưu URL ảnh nhỏ nếu có thể lấy URL chất lượng cao hơn.
- Loại bỏ URL trùng lặp.

#### Với video:

- Lấy URL video thực tế, không chỉ thumbnail.
- Kiểm tra `<video>`, `<source>`, JSON nhúng và network request.
- Lưu cả MP4 URL và HLS URL nếu có.

### 4. Product Videos

Tìm khu vực có heading:

```text
Product Videos
```

Lấy URL của toàn bộ video trong khu vực này.

Nếu video nằm trong carousel hoặc modal:

1. Scroll đến khu vực Product Videos.
2. Chờ lazy loading hoàn tất.
3. Duyệt toàn bộ item trong carousel.
4. Click từng video khi cần.
5. Lấy URL video thực tế từ DOM hoặc network.
6. Đóng modal trước khi chuyển sang video tiếp theo.

Không nhầm Product Videos với video trong Product Media Gallery hoặc A+ Content.

### 5. Color Swatches và Customize

Tìm toàn bộ Color Swatch trong Amazon Twister, bao gồm swatch đang được chọn mặc định.

Với từng Color Swatch:

1. Click chọn swatch.
2. Chờ variation, URL, ASIN và giá cập nhật ổn định.
3. Thu thập:
   - Tên hoặc label.
   - ASIN.
   - Product URL.
   - Swatch image URL.
   - Availability.
   - Product base price.

4. Crawl lại Product Attributes nếu thuộc tính thay đổi theo swatch.
5. Click nút `Customize now`.
   - **Lưu ý quan trọng**: Amazon có thể render 2 nút "Customize Now" trong DOM. Tuyệt đối **không click** vào nút giả có ID `#gestalt-fake-popover-button-announce` vì nó sẽ gây chuyển hướng hoặc lỗi tải trang. Phải click chính xác vào nút thật có ID: `#gestalt-popover-button-announce`.
6. Chờ popup `Customize`.
   - Dữ liệu customization sẽ được load bên trong một iframe có ID là `gc-iframe`.
   - Để bóc tách dữ liệu, cần evaluate bên trong iframe này, hoặc trích xuất `src` của iframe và điều hướng trình duyệt đến URL đó để parse DOM dễ dàng hơn nếu gặp lỗi cross-origin.
7. Thu thập toàn bộ customization type.
8. Với từng customization type, thu thập toàn bộ customization option và giá tăng thêm (ví dụ click nút "See all X options" nếu bị ẩn đi).
9. Đóng popup.
10. Tiếp tục với swatch tiếp theo.

Không giả định các swatch có cùng giá, thuộc tính hoặc customization.

Với mỗi customization option, lấy:

- Name hoặc label.
- ID hoặc value nếu có.
- Available hoặc disabled.
- Có được chọn mặc định hay không.
- Giá tăng thêm.
- Chuỗi giá gốc hiển thị trên Amazon.

Nếu giá tăng thêm không hiển thị trực tiếp nhưng tổng giá thay đổi:

1. Ghi nhận giá trước khi chọn.
2. Chọn option.
3. Chờ giá cập nhật ổn định.
4. Ghi nhận giá sau khi chọn.
5. Tính phần chênh lệch.
6. Khôi phục trạng thái trước khi kiểm tra option khác.

Không suy đoán giá khi không thể xác định.

## Cấu trúc JSON đầu ra

Tạo file:

```text
/crawl/B0H6FGCCVP/B0H6FGCCVP.json
```

Cấu trúc tối thiểu cần phải có:

```json
{
  "schema_version": "1.2.0",
  "asin": "mã ASIN",
  "source_url": "Link sản phẩm Amazon",
  "crawl_metadata": {
    "crawled_at": null,
    "status": "completed",
    "errors": [],
    "warnings": []
  },
  "product": {
    "title": string | null,
    "base_price": {
      "amount": number | null,
      "currency": string | null,
      "formatted": string | null,
      "raw_text": string | null
    },
    "about_this_item": [],
    "product_attributes": {
      "items": [],
      "by_key": {}
    }
  },
  "assets": {
    "product_media_gallery": {
      "images": [],
      "videos": []
    },
    "aplus_content": {
      "images": [],
      "videos": []
    },
    "product_videos": []
  },
  "color_swatches": []
}
```

## Cấu trúc dữ liệu ảnh

Mỗi ảnh nên có cấu trúc:

```json
{
  "index": 1,
  "source_url": null,
  "resolved_url": null,
  "thumbnail_url": null,
  "alt_text": null
}
```

Trong đó:

- `source_url`: URL lấy từ phần tử ảnh lớn đang hiển thị sau khi click thumbnail tương ứng. Không dùng URL của thumbnail cho field này.
- `resolved_url`: URL ảnh lớn nhất hoặc ảnh gốc lấy từ `data-old-hires`, `data-a-dynamic-image`, `srcset`, `src` hoặc network request của khu vực ảnh lớn.
- `thumbnail_url`: URL của ảnh nhỏ trong danh sách thumbnail, chỉ dùng để đối chiếu.
- Nếu chỉ tìm thấy URL ảnh nhỏ như `_AC_US100_`, `_SS64_` hoặc `_SX38_`, đặt `source_url`/`resolved_url` là `null`, giữ URL nhỏ trong `thumbnail_url` và ghi warning.

## Cấu trúc dữ liệu video

Mỗi video nên có cấu trúc:

```json
{
  "index": 1,
  "title": null,
  "source_url": null,
  "mp4_url": null,
  "hls_url": null,
  "poster_url": null
}
```

Không lưu `blob:` URL nếu có thể lấy URL HTTP/HTTPS thực tế từ DOM hoặc network request.

## Cấu trúc Color Swatch

Mỗi Color Swatch phải chứa tối thiểu:

```json
{
  "name": string | null,
  "asin": string | null,
  "product_url": string | null,
  "swatch_image_url": string | null,
  "availability": boolean | null,
  "base_price": {
    "amount": number | null,
    "currency": string | null,
    "formatted": string | null,
    "raw_text": string | null
  },
  "product_attributes": {
    "items": [],
    "by_key": {}
  },
  "customization_types": []
}
```

Mỗi customization type phải được liệt kê theo cấu trúc sau:

```json
{
  "name": string | null,
  "required": boolean | null,
  "selection_type": string | null,
  "options": []
}
```

Mỗi customization option phải dược liệt kê theo cấu trúc sau:

```json
{
  "value": string | null,
  "increase_amount": string | null,
}
```

## Dữ liệu debug

Trong quá trình crawl, có thể lưu các dữ liệu hỗ trợ kiểm tra vào:

```text
/crawl/B0H6FGCCVP/debug/
```

Dữ liệu debug có thể bao gồm:

- Screenshot khi gặp lỗi hoặc CAPTCHA.
- Screenshot từng khu vực quan trọng.
- HTML snapshot.
- Nội dung DOM đã trích xuất.
- Network request log.
- Response JSON liên quan đến video hoặc variation.
- Danh sách selector đã thử.
- Dữ liệu trung gian trước khi ghi vào JSON.
- Log lỗi cho từng media, swatch hoặc customization option.

Đặt tên file debug rõ ràng, ví dụ:

```text
debug/
├── captcha.png
├── product-page.html
├── product-media-gallery.json
├── aplus-network-requests.json
├── product-videos-network.json
├── swatch-option-01.json
└── errors.log
```

Không bắt buộc phải giữ dữ liệu debug không còn giá trị. Tuy nhiên, phải giữ lại dữ liệu giúp giải thích các lỗi hoặc dữ liệu chưa crawl được.

## Quy tắc dữ liệu

- Không tạo dữ liệu giả.
- Không dùng dữ liệu mẫu để thay thế dữ liệu không tìm thấy.
- Giá `amount` phải là `number` hoặc `null`.
- Lưu cả giá đã parse và text gốc.
- Không tìm thấy dữ liệu thì dùng:
  - `null`
  - `false`
  - `[]`
  - `{}`

- Giữ đúng thứ tự media và option trên Amazon.
- Loại bỏ URL media trùng lặp.
- Với video HLS, lưu URL `.m3u8` thực tế.
- Với ảnh Amazon, ưu tiên URL không chứa transform kích thước nhỏ.
- Trong Product Media Gallery, bắt buộc click từng thumbnail rồi lấy URL từ ảnh lớn đang hiển thị.
- Không dùng URL thumbnail làm `source_url` hoặc `resolved_url`.
- Không chấp nhận URL ảnh chính chứa transform kích thước nhỏ như `_AC_US100_`, `_SS64_` hoặc `_SX38_`.
- Sau mỗi lần click thumbnail, phải chờ và xác nhận ảnh lớn đã cập nhật trước khi đọc URL.
- Một media, swatch hoặc customization bị lỗi không được làm mất toàn bộ kết quả.
- Thường xuyên cập nhật file JSON để tránh mất dữ liệu khi phiên trình duyệt gặp lỗi.
- Nếu crawl được một phần, đặt `status` là `partial`.
- Nếu đang chờ tôi xử lý CAPTCHA, đặt `status` là `blocked`.
- Nếu không thể hoàn thành do lỗi khác, đặt `status` là `failed`.
- Chỉ đặt `status` là `completed` khi các khu vực có thể truy cập đã được kiểm tra đầy đủ.
- `base_price.currency` phải là `USD` sau khi phiên Amazon US được thiết lập.
- Không tự chuyển đổi giá từ VND hoặc currency khác sang USD.
- Giá phải được lấy trực tiếp từ giao diện Amazon sau khi áp dụng ZIP code `90001`.
- Chỉ đặt `location_applied` thành `true` sau khi xác nhận location đã cập nhật.
- Chỉ đặt `currency_verified` thành `true` sau khi xác nhận giá hiển thị bằng USD.
- Nếu vẫn thấy giá VND, không được lưu giá đó làm product base price.
- Nếu một Color Swatch làm trang đổi ASIN hoặc reload, phải kiểm tra location và currency vẫn là US/USD trước khi lấy giá.
- Với mỗi Color Swatch, phải kiểm tra lại nút `Customize now` sau khi variation cập nhật hoàn tất.

---

# File báo cáo

Tạo file:

```text
/crawl/B0H6FGCCVP/report.md
```

File `report.md` phải bao gồm tối thiểu:

```markdown
# Amazon Crawl Report

## Product

- ASIN:
- Source URL:
- Product title:
- Base price:
- Crawl time:
- Final status:

## Crawl results

- Product Attributes:
- About this item entries:
- Product Media Gallery images:
- Product Media Gallery videos:
- A+ Content images:
- A+ Content videos:
- Product Videos:
- Color Swatches:
- Customization types:
- Customization options:

## Output files

- JSON:
- Report:
- Debug folder:

## Warnings

- Không có hoặc liệt kê từng warning.

## Errors

- Không có hoặc liệt kê từng error.

## Missing data

- Liệt kê các khu vực hoặc trường dữ liệu không tìm thấy.

## Notes

- Ghi rõ các giới hạn, dữ liệu cần kiểm tra thủ công hoặc vấn đề liên quan đến CAPTCHA, lazy loading, network request và variation.
```

Báo cáo phải phản ánh đúng kết quả thực tế trong file JSON, không ghi kết quả giả định.

## Hoàn thành công việc

Sau khi crawl xong:

1. Xác nhận đã tạo:

```text
/crawl/B0H6FGCCVP/B0H6FGCCVP.json
/crawl/B0H6FGCCVP/report.md
```

2. Báo cáo ngắn gọn:
   - Product title và base price.
   - Số Product Attributes.
   - Số ảnh và video trong Product Media Gallery.
   - Số ảnh và video trong A+ Content.
   - Số Product Videos.
   - Số Color Swatches.
   - Số customization type và option.
   - Trạng thái cuối cùng.
   - Dữ liệu không tìm thấy hoặc lỗi còn tồn tại.

## Amazon session configuration

- Marketplace: amazon.com
- Delivery country: United States
- Delivery ZIP code: 90001
- Location applied:
- Display currency:
- Currency verified:
- Customize now found:
- Notes:

---

# Hậu xử lý nội dung sau khi crawl hoàn tất

Chỉ thực hiện các bước trong mục này **sau khi toàn bộ quá trình crawl đã hoàn thành**, các khu vực có thể truy cập đã được kiểm tra đầy đủ và file JSON kết quả đã được tạo thành công.

## 1. Viết lại Product Title chuẩn SEO

- Viết lại `product.title` dựa trên product title gốc và toàn bộ dữ liệu sản phẩm đã crawl được.
- Product title mới phải tự nhiên, rõ nghĩa, mô tả đúng sản phẩm và không chứa thông tin không có trong dữ liệu nguồn.
- Độ dài bắt buộc: **từ 50 đến 70 ký tự**, tính cả khoảng trắng.
- Ưu tiên đặt từ khóa chính gần đầu title.
- Không nhồi nhét từ khóa, không lặp từ vô nghĩa, không dùng câu quảng cáo quá mức và không tự tạo thông số kỹ thuật.
- Ghi đè giá trị title mới vào field:

```json
product.title
```

## 2. Viết lại Product Description thành HTML

- Dùng nội dung từ `product.about_this_item`, Product Attributes và các thông tin sản phẩm thực tế đã crawl được để viết lại product description.
- Chỉ tham khảo **cấu trúc HTML, bố cục và inline style** bên dưới.
- Toàn bộ heading, paragraph, badge và nội dung mô tả phải được viết lại theo đúng sản phẩm đang crawl.
- Không sao chép các nội dung mẫu về bookshelf, storage, finish color hoặc vật trang trí nếu chúng không phù hợp với sản phẩm thực tế.
- Không tạo đặc điểm, vật liệu, công dụng, màu sắc, kích thước hoặc phụ kiện không có trong dữ liệu đã crawl.
- Có thể tăng hoặc giảm số block đánh số để phù hợp với số lượng ý chính thực tế, nhưng phải giữ phong cách và cấu trúc trình bày thống nhất.
- Ghi HTML hoàn chỉnh vào field:

```json
product.about_this_item
```

Field này sau bước hậu xử lý sẽ là một **chuỗi HTML**, không còn là mảng bullet thô.

Cấu trúc HTML tham khảo:

```html
<div
  class="dm-tabs__rte"
  style="margin:0; padding:0; background:transparent; color:#2a211b; font-family:inherit;"
>
  <div style="display:grid; gap:16px; margin:0; padding:0; background:transparent;">
    <div
      style="padding:16px 18px; border-radius:16px; background:rgba(91,50,24,0.055); border:1px solid rgba(92,58,35,0.10);"
    >
      <div
        style="margin:0 0 6px; color:#5a3218; font-size:11px; line-height:1; font-weight:600; letter-spacing:0.16em; text-transform:uppercase;"
      >
        Sculptural Tree-Inspired Storage
      </div>
      <p
        style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
      >
        Bring natural warmth and artistic character into your home with a tree branch floor shelf
        featuring flowing trunk lines, organic supports, and sculptural multi-level storage.
      </p>
    </div>
    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        01
      </span>
      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Tree Branch Statement Design
        </h3>
        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Flowing trunk lines, organic branch supports, and sculptural shelf placement create a
          nature-inspired focal point that adds rustic warmth and visual movement to the room.
        </p>
      </div>
    </div>
    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        02
      </span>
      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Rich Wood Grain Appearance
        </h3>
        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          A rich wood grain appearance, smooth rounded shelf edges, and handcrafted-style curves
          give the bookcase a warm vintage character suited to cozy and nature-inspired interiors.
        </p>
      </div>
    </div>
    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        03
      </span>
      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Multi-Level Display Storage
        </h3>
        <p
          style="margin:0 0 10px; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Multiple shelf levels provide decorative display space for arranging books, plants,
          keepsakes, and personal décor in a warm and visually balanced way.
        </p>
        <div style="display:flex; flex-wrap:wrap; gap:7px; margin:0; padding:0;">
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Books</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Plants</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Pottery</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Lanterns</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Framed Photos</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Candles</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Baskets</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.09); border:1px solid rgba(92,58,35,0.13); color:#5a3218; font-size:12px; line-height:1;"
            >Collectibles</span
          >
        </div>
      </div>
    </div>

    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        04
      </span>

      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Functional Storage With Artistic Style
        </h3>

        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Combining practical organization with decorative character, this tree bookshelf can serve
          as a bookcase, plant display shelf, rustic storage piece, or sculptural statement feature.
        </p>
      </div>
    </div>

    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        05
      </span>

      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Choose Your Finish Color
        </h3>

        <p
          style="margin:0 0 10px; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Choose from four finish colors to coordinate the bookshelf with rustic, farmhouse, boho,
          vintage, cottage, cabin, woodland, or organic-modern décor.
        </p>

        <div style="display:flex; flex-wrap:wrap; gap:7px; margin:0; padding:0;">
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Warm Wood</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Dark Warm Wood</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.06); border:1px solid rgba(92,58,35,0.10); color:rgba(42,33,27,0.78); font-size:12px; line-height:1;"
            >Cool Dark Wood</span
          >
          <span
            style="display:inline-flex; padding:6px 9px; border-radius:999px; background:rgba(91,50,24,0.09); border:1px solid rgba(92,58,35,0.13); color:#5a3218; font-size:12px; line-height:1;"
            >Natural Finish</span
          >
        </div>
      </div>
    </div>

    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        06
      </span>

      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Designed for Cozy Interiors
        </h3>

        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          A warm decorative addition to living rooms, bedrooms, reading nooks, offices, cabins,
          cottages, and other welcoming spaces with rustic or nature-inspired styling.
        </p>
      </div>
    </div>

    <div
      style="display:grid; grid-template-columns:34px 1fr; gap:14px; padding:0 0 16px; border-bottom:1px solid rgba(92,58,35,0.14); background:transparent;"
    >
      <span
        style="width:30px; height:30px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(91,50,24,0.09); color:#5a3218; font-size:11px; font-weight:600; letter-spacing:0.04em; line-height:1;"
      >
        07
      </span>

      <div style="margin:0; padding:0; background:transparent;">
        <h3
          style="margin:0 0 7px; padding:0; color:#1f1712; font-family:var(--font-heading-family, Georgia, serif); font-size:17px; line-height:1.35; font-weight:500;"
        >
          Naturally Unique Character
        </h3>

        <p
          style="margin:0; padding:0; color:rgba(42,33,27,0.76); font-size:14px; line-height:1.7; font-weight:400;"
        >
          Each piece may vary slightly in branch curve, shelf edge, decorative leaf placement, wood
          grain, color tone, and finish appearance, giving every bookshelf its own distinctive look.
        </p>
      </div>
    </div>

    <div
      style="margin:2px 0 0; padding:13px 15px; border-radius:14px; background:rgba(91,50,24,0.06); color:rgba(42,33,27,0.72); font-size:13px; line-height:1.6; border:1px solid rgba(92,58,35,0.08);"
    >
      Books, plants, pottery, lanterns, framed photos, baskets, and other decorative objects shown
      in product photos are for presentation only unless explicitly included.
    </div>
  </div>
</div>
```

## 3. Thêm `extra_fields` vào cuối JSON crawl

Sau khi đã viết lại title và description, thêm object `extra_fields` ở cấp cao nhất, tại cuối file JSON:

```json
{
  "extra_fields": {
    "seo_product_title": "string",
    "page_title": "string",
    "meta_description": "string",
    "url_slug": "string"
  }
}
```

Quy tắc cho từng field:

### `extra_fields.seo_product_title`

- Viết từ product title gốc thành dạng **long-tail keyword**.
- Phải mô tả đúng loại sản phẩm, đặc điểm nổi bật, vật liệu hoặc phong cách thực tế nếu dữ liệu crawl có cung cấp.
- Không nhồi nhét từ khóa và không thêm thông tin không có trong dữ liệu nguồn.
- Không bắt buộc giống `product.title` hoặc `page_title`.

### `extra_fields.page_title`

- Đây là tiêu đề hiển thị trên công cụ tìm kiếm.
- Viết chuẩn SEO, tự nhiên và tập trung vào từ khóa chính.
- Độ dài bắt buộc: **từ 50 đến 60 ký tự**, tính cả khoảng trắng.
- Không tự động thêm tên thương hiệu nếu việc đó làm vượt giới hạn ký tự.

### `extra_fields.meta_description`

- Viết chuẩn SEO dựa trên nội dung thật của sản phẩm.
- Độ dài bắt buộc: **từ 150 đến 160 ký tự**, tính cả khoảng trắng.
- Mô tả rõ sản phẩm, điểm nổi bật và mục đích sử dụng chính.
- Không nhồi nhét từ khóa, không dùng thông tin giả và không kết thúc bằng câu bị cắt dở.

### `extra_fields.url_slug`

- Viết dưới dạng URL slug chuẩn SEO.
- Độ dài bắt buộc: **từ 50 đến 60 ký tự**, tính cả dấu gạch nối.
- Chỉ sử dụng chữ thường ASCII, chữ số và dấu gạch nối `-`.
- Không dấu tiếng Việt, không khoảng trắng, không ký tự đặc biệt.
- Không bắt đầu hoặc kết thúc bằng dấu gạch nối.
- Không có hai dấu gạch nối liên tiếp.
- Ưu tiên từ khóa mô tả đúng sản phẩm và tránh các từ không mang giá trị SEO.

Ví dụ cấu trúc cuối file JSON:

```json
{
  "schema_version": "1.2.0",
  "asin": "B0H6FGCCVP",
  "source_url": "https://www.amazon.com/dp/B0H6FGCCVP",
  "crawl_metadata": {},
  "product": {},
  "assets": {},
  "color_swatches": [],
  "extra_fields": {
    "seo_product_title": "Long-tail keyword product title generated from the original title",
    "page_title": "SEO page title between 50 and 60 characters",
    "meta_description": "SEO meta description between 150 and 160 characters, written naturally from the actual crawled product information without invented claims.",
    "url_slug": "seo-friendly-product-url-slug-between-50-and-60-chars"
  }
}
```

## 4. Xác minh bắt buộc sau hậu xử lý

Trước khi kết thúc, phải kiểm tra và ghi nhận:

- `product.title` có độ dài từ 50 đến 70 ký tự.
- `product.about_this_item` là một chuỗi HTML hoàn chỉnh, hợp lệ và dùng đúng nội dung của sản phẩm đã crawl.
- HTML không còn nội dung mẫu không liên quan đến sản phẩm thực tế.
- `extra_fields.seo_product_title` có dạng long-tail keyword và không chứa thông tin bịa đặt.
- `extra_fields.page_title` có độ dài từ 50 đến 60 ký tự.
- `extra_fields.meta_description` có độ dài từ 150 đến 160 ký tự.
- `extra_fields.url_slug` có độ dài từ 50 đến 60 ký tự và đúng định dạng slug.
- File JSON vẫn parse hợp lệ sau khi cập nhật.
- Không làm mất hoặc thay đổi sai dữ liệu crawl gốc ngoài các field được yêu cầu hậu xử lý.
- Cập nhật `report.md` để ghi rõ rằng bước SEO và định dạng description đã hoàn thành, đồng thời ghi lại độ dài thực tế của title, page title, meta description và URL slug.
