# Yêu cầu crawl dữ liệu sản phẩm Amazon

Dùng `playwright` truy cập link amazon "https://www.amazon.com/dp/B0H6D25Y8T" sau đó:

- Cào thông tin cơ bản của sản phẩm trong link vào `file json`:
  - product title
  - product base price
  - about this item

- Cào A+ content của sản phẩm trong link vào `folder riêng`:
  - tìm đến khu vực A+ Content và cào toàn bộ ảnh & video trong khu vực đó về folder riêng
  - lấy size ảnh từ 1200 trở lên.

- Cào product video của sản phẩm trong link vào `folder riêng`:
  - tìm đến khu vực "<h2 ...>Product Videos</h2>" và cào toàn bộ video từ khu vực này về folder riêng

- Cào tất cả các option Color Swatch của sản phẩm trong link vào `file json`:
  - tìm đến mục Color Swatches thuộc khu vực Amazon Twister, tại đây sẽ có các option Color Swatch
  - sau đó chọn từng option Color Swatch
  - đối với mỗi option Color Swatch khi được chọn:
    - sẽ có product base price khác nhau, liệt kê price này vào file json
    - sau khi liệt kê price của option Color Swatch đó xong thì nhấn vào nút "Customize now" trên trang, đợi một chút sẽ có 1 popup "Customize" hiện lên
    - trong popup "Customize" này có các customization type, mỗi customization type sẽ có các customization option khác nhau
    - liệt kê vào file json:
      - tất cả các customization option cùng với giá tăng thêm cho sản phẩm đổi với từng customization option.

> `File json` là file được lưu vào bên trong folder "/crawl" với tên file là slug của link amazon đó (ví dụ "/crawl/B0H6D25Y8T.json").
> `Folder riêng` là folder được lưu vào bên trong folder "/crawl" với tên folder là slug của link amazon đó (ví dụ "/crawl/B0H6D25Y8T")
> `Playwright` đã được cài đặt trong project này qua npm.

---

## Cấu trúc folder "crawl" đề xuất

Cấu trúc nên tách rõ **thông tin sản phẩm**, **tài nguyên A+ Content**, **Product Videos**, và **dữ liệu từng Color Swatch**.

### Cấu trúc thư mục

```text
/crawl/
├── B0H6D25Y8T.json
└── B0H6D25Y8T/
    ├── aplus-content/
    │   ├── images/
    │   │   ├── image-001.jpg
    │   │   ├── image-002.png
    │   │   └── ...
    │   └── videos/
    │       ├── video-001.mp4
    │       └── ...
    └── product-videos/
        ├── video-001.mp4
        ├── video-002.mp4
        └── ...
```

### Cấu trúc đề xuất cho `/crawl/B0H6D25Y8T.json`

```json
{
  "schema_version": "1.0.0",
  "asin": "B0H6D25Y8T",
  "source": {
    "platform": "amazon",
    "url": "https://www.amazon.com/dp/B0H6D25Y8T",
    "marketplace": "amazon.com"
  },
  "crawl_metadata": {
    "crawled_at": "2026-07-17T00:00:00.000Z",
    "status": "completed",
    "errors": []
  },
  "product": {
    "title": "Example product title",
    "base_price": {
      "amount": 199.99,
      "currency": "USD",
      "formatted": "$199.99",
      "raw_text": "$199.99"
    },
    "about_this_item": ["First bullet point", "Second bullet point", "Third bullet point"]
  },
  "assets": {
    "aplus_content": {
      "found": true,
      "folder": "/crawl/B0H6D25Y8T/aplus-content",
      "images": [
        {
          "index": 1,
          "filename": "image-001.jpg",
          "local_path": "/crawl/B0H6D25Y8T/aplus-content/images/image-001.jpg",
          "source_url": "https://m.media-amazon.com/images/...",
          "resolved_url": "https://m.media-amazon.com/images/..._SX1594_...",
          "width": 1594,
          "height": 986,
          "mime_type": "image/jpeg",
          "alt_text": "Example A+ image",
          "download_status": "success"
        }
      ],
      "videos": [
        {
          "index": 1,
          "filename": "video-001.mp4",
          "local_path": "/crawl/B0H6D25Y8T/aplus-content/videos/video-001.mp4",
          "source_url": "https://...",
          "poster_url": "https://...",
          "title": null,
          "mime_type": "video/mp4",
          "download_status": "success"
        }
      ]
    },
    "product_videos": {
      "found": true,
      "section_heading": "Product Videos",
      "folder": "/crawl/B0H6D25Y8T/product-videos",
      "videos": [
        {
          "index": 1,
          "filename": "video-001.mp4",
          "local_path": "/crawl/B0H6D25Y8T/product-videos/video-001.mp4",
          "source_url": "https://...",
          "poster_url": "https://...",
          "title": "Product overview",
          "duration_seconds": null,
          "mime_type": "video/mp4",
          "download_status": "success"
        }
      ]
    }
  },
  "color_swatches": [
    {
      "index": 1,
      "id": "natural",
      "name": "Natural",
      "label": "Natural Wood",
      "asin": "B0H6D25Y8T",
      "product_url": "https://www.amazon.com/dp/B0H6D25Y8T",
      "swatch": {
        "image_url": "https://m.media-amazon.com/images/...",
        "alt_text": "Natural"
      },
      "availability": {
        "status": "in_stock",
        "raw_text": "In Stock"
      },
      "base_price": {
        "amount": 199.99,
        "currency": "USD",
        "formatted": "$199.99",
        "raw_text": "$199.99"
      },
      "customize_now": {
        "available": true,
        "popup_opened": true,
        "customization_types": [
          {
            "index": 1,
            "id": "size",
            "name": "Size",
            "label": "Choose a size",
            "required": true,
            "selection_type": "single",
            "options": [
              {
                "index": 1,
                "id": "small",
                "name": "Small",
                "label": "Small",
                "selected_by_default": true,
                "available": true,
                "price_delta": {
                  "amount": 0,
                  "currency": "USD",
                  "formatted": "+$0.00",
                  "raw_text": "Included"
                },
                "calculated_product_price": {
                  "amount": 199.99,
                  "currency": "USD",
                  "formatted": "$199.99"
                }
              },
              {
                "index": 2,
                "id": "large",
                "name": "Large",
                "label": "Large",
                "selected_by_default": false,
                "available": true,
                "price_delta": {
                  "amount": 50,
                  "currency": "USD",
                  "formatted": "+$50.00",
                  "raw_text": "+$50.00"
                },
                "calculated_product_price": {
                  "amount": 249.99,
                  "currency": "USD",
                  "formatted": "$249.99"
                }
              }
            ]
          },
          {
            "index": 2,
            "id": "finish",
            "name": "Finish",
            "label": "Choose a finish",
            "required": false,
            "selection_type": "single",
            "options": [
              {
                "index": 1,
                "id": "matte",
                "name": "Matte",
                "label": "Matte Finish",
                "selected_by_default": true,
                "available": true,
                "price_delta": {
                  "amount": 0,
                  "currency": "USD",
                  "formatted": "+$0.00",
                  "raw_text": "Included"
                },
                "calculated_product_price": {
                  "amount": 199.99,
                  "currency": "USD",
                  "formatted": "$199.99"
                }
              },
              {
                "index": 2,
                "id": "glossy",
                "name": "Glossy",
                "label": "Glossy Finish",
                "selected_by_default": false,
                "available": true,
                "price_delta": {
                  "amount": 20,
                  "currency": "USD",
                  "formatted": "+$20.00",
                  "raw_text": "+$20.00"
                },
                "calculated_product_price": {
                  "amount": 219.99,
                  "currency": "USD",
                  "formatted": "$219.99"
                }
              }
            ]
          }
        ],
        "errors": []
      }
    }
  ]
}
```

### Một số quy ước nên dùng

- `amount` luôn là kiểu `number`, không lưu `"$199.99"` làm giá trị chính.
- `formatted` dùng để hiển thị.
- `raw_text` lưu nguyên văn Amazon trả về để kiểm tra khi parser sai.
- Không tìm thấy dữ liệu thì dùng `null`, `false` hoặc mảng rỗng `[]`.
- `price_delta.amount`:
  - `0`: không tăng giá.
  - Số dương: tăng thêm.
  - Số âm: giảm giá.

- `calculated_product_price` là giá dự kiến sau khi cộng riêng option đó vào `base_price`.
- Mỗi Color Swatch chứa customization riêng vì popup hoặc mức giá có thể thay đổi theo từng màu.
- Giữ `index` theo đúng thứ tự hiển thị trên Amazon.
- Chỉ tải ảnh có kích thước thực tế hoặc URL resize đạt chiều rộng tối thiểu `1200px`.

Với các customization phụ thuộc lẫn nhau, nên bổ sung điều kiện:

```json
{
  "id": "premium-finish",
  "name": "Premium Finish",
  "price_delta": {
    "amount": 40,
    "currency": "USD",
    "formatted": "+$40.00"
  },
  "conditions": [
    {
      "customization_type_id": "size",
      "selected_option_id": "large"
    }
  ]
}
```

Cấu trúc này phù hợp để AI Agent crawl tuần tự, dễ debug và vẫn đủ linh hoạt khi giao diện customization của từng Color Swatch không giống nhau.
