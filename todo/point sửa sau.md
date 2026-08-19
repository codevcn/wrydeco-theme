## Point sửa sau

### Phase 1

- point 5:

```text
• Plan Point 5

  Point 5 có media thật nhưng không cùng một sản phẩm, nên mình không nên gọi là “case study của một đơn hàng”. Cách an toàn hơn là tạo section dạng Workshop Evidence /
  Mình đề xuất sửa như sau:

  1. Tạo section mới: sections/workshop-evidence.liquid
          - wrydeco-handcrafting-process-workshop.mp4
          - wrydeco-workshop-product-assembly.mp4
          - wrydeco-product-packaging-for-shipping.jpg

      - 2 video dùng <video controls preload="metadata" playsinline>.
      - Ảnh packaging có alt, width, height, loading="lazy".
      - Copy sẽ nói rõ đây là “real workshop moments”, không claim là cùng một đơn hàng.

  2. Gắn section vào homepage: templates/index.json
      - Vị trí đề xuất: sau welcome_video, trước shop_collections hoặc trước made_to_order.
      - Hiển thị trên website: homepage /.
      - Lý do: homepage cần trust proof mạnh nhất, giúp khách thấy sản xuất/assembly/packaging thật sớm.

  - API Shopify Admin hiện không tìm thấy 3 filename qua Files query, dù mình dùng token fallback client credentials. Có thể do search API không match filename, hoặc
    file chưa upload/đổi tên. Nếu bạn duyệt, mình vẫn có thể dùng file_url đúng theo filename trong todo.md; nếu file thật sự chưa có trên Shopify Files thì media sẽ
    không render đúng trên live.

  - Sau khi sửa xong, mình sẽ chạy validation JSON/schema và dùng Playwright kiểm tra UI desktop/mobile vì đây là section UI mới.
```

### Phase 2

- point 1:

```text
• Plan Phase 2 - Point 1: Media Thật

  Mục tiêu của point này: tăng bằng chứng thật bằng media xưởng/quy trình/đóng gói/review photo, nhưng không gọi sai là “case study của một đơn hàng” vì media đang đến
  từ nhiều sản phẩm khác nhau.

  Những thứ chuẩn bị sửa

  1. Tạo hoặc cập nhật section process evidence trên PDP
      - Vị trí code dự kiến: sections/ tạo section mới, ví dụ:
          - sections/workshop-process-evidence.liquid

      - Gắn vào:
          - templates/product.json

      - Hiển thị trên website:
          - PDP, nên đặt sau section “No Two Pieces Are Ever Truly Alike” và trước “Order Process & Delivery”.

      - Nội dung:
          - Video cưa/đục/chế tác: wrydeco-handcrafting-process-workshop.mp4
          - Video lắp ráp: wrydeco-workshop-product-assembly.mp4
          - Ảnh đóng gói: wrydeco-product-packaging-for-shipping.jpg

      - Copy English, hướng an toàn:
          - Inside the WRYDECO Workshop
          - Real workshop moments from shaping, assembly, and shipment preparation.
          - Tránh wording như this exact order, from start to finish, the product you will receive.

  2. Thêm teaser/section ngắn trên About page
      - Vị trí code:
          - Có thể reuse cùng section mới trong templates/page.about-us.json

      - Hiển thị trên website:
          - About page, đặt sau phần craftsmanship/workshop story nếu template hiện có vị trí phù hợp.

      - Nội dung:
          - Nhấn mạnh media thật từ workshop/process.
          - Copy kiểu: A closer look at how our pieces are shaped, assembled, checked, and prepared for shipment.

  3. Không dùng ảnh artisan nếu chưa có
      - Point 1 phase 2 nói rõ: không có ảnh thật từng artisan.
      - Vì vậy tôi sẽ không tạo profile artisan có ảnh giả, không dùng avatar placeholder như người thật.
  4. Không dùng ảnh kỹ thuật/load-bearing nếu chưa có
      - Point 1 nói rõ chưa có media kỹ thuật về mối nối/bracket/wall mounting/điểm chịu lực.
      - Tôi sẽ không viết claim kỹ thuật cụ thể kiểu load-tested, supports X lb, engineered bracket, nếu không có dữ liệu.

  5. Có thể dùng review/home photos nhưng cẩn thận
      - Point 1 nói có ảnh sản phẩm trong nhà thật từ review CSV.
        nếu cần.

  File Có Thể Sửa

  - Tạo mới: sections/workshop-process-evidence.liquid
  - Sửa: templates/product.json
  - Sửa: templates/page.about-us.json
  - Ghi kết quả sau khi làm: todo/todo.md

  Highlight Cần Lưu Ý

  - Đây là tạo UI mới / sửa UI đáng kể, cần bạn duyệt trước.
  - Sẽ dùng file_url cho Shopify Files, đúng CODING_RULES.md.
  - Nội dung public UI sẽ viết bằng English.
  - Section phải SSR-first: video/image markup render sẵn trong Liquid, không phụ thuộc JS để có content chính.
  - Sau khi sửa sẽ dùng Playwright check PDP và About, gồm desktop 1520px và mobile.
  - Không chạy shopify theme check.

  Cần bạn xác nhận thêm trước khi tôi làm: 3 file media trên Shopify Files chắc chắn đã upload chưa? Nếu chưa chắc, tôi sẽ dùng Shopify Admin token trong folder admin để
  kiểm tra trước khi code.
```

- point 2:

```text
Phần "1-2 sản phẩm/dòng sản phẩm từng làm" cần quay lại sau khi có dữ liệu thật.

Hiện metaobject product_author trên store có các field thật: author_name, role, exp_years, author_image_url, author_bio, author_slogan, display_features.
Chưa có field/link dữ liệu chuẩn để map từng artisan với 1-2 sản phẩm hoặc dòng sản phẩm đã làm, nên chưa public claim này trên website để tránh tạo thông tin không có nguồn xác thực.
```
