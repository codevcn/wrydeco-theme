## 1. Câu chuyện vận hành thật của WRYDECO

- Brand đăng ký/vận hành ở Mỹ.
- Xưởng/nghệ nhân ở Việt Nam.
- Hàng ship từ Việt Nam qua kho/đối tác tại Mỹ đến khách Mỹ.
- Team support online.
- dùng wording kiểu: “US-operated brand, handcrafted by artisans in Vietnam, shipped directly to customers in the United States”.

### Kết quả fix point 1:

```text
Đã đồng bộ câu chuyện vận hành/provenance ở các vị trí SSR chính:
- About page (/pages/about-us): cập nhật hero_text, purpose_statement_two và craft_text để nói rõ WRYDECO là US-operated, sản phẩm handcrafted bởi artisans in Vietnam, có online team hỗ trợ custom details, production updates và delivery support.
- FAQ page (/pages/faq): cập nhật câu "Who actually makes these pieces?" để giải thích WRYDECO operated ở United States, sản phẩm handcrafted in Vietnam, support team online.
- Contact page (/pages/contact): thêm dòng "Brand & craft" trong contact details: US-operated, handcrafted by artisans in Vietnam, supported online.
- PDP (/products/...): cập nhật default craft trust copy thành "Handcrafted in Vietnam" và mô tả support coordination nhẹ hơn.
- Footer toàn site: giữ footer ngắn gọn theo yêu cầu, chỉ dùng fallback slogan "Bespoke wooden furniture, handcrafted for timeless spaces and meaningful living."; không còn câu dài "WRYDECO is a US-operated furniture brand..."

Đã kiểm tra JSON hợp lệ cho templates/page.about-us.json, templates/page.faq.json, sections/footer-group.json và schema hợp lệ cho sections/main-contact.liquid, sections/footer.liquid, sections/main-product.liquid. Không chạy shopify theme check theo yêu cầu.
```

## 2. Chính sách damage/defect chính xác

- khách phải báo damage trong 30 ngày
- Mốc này áp dụng cho tất cả
- Có yêu cầu ảnh/video khi báo lỗi

### Kết quả fix point 2:

```text
Đã xác minh policy chuẩn mới nhất tại https://wrydeco.com/policies/refund-policy và Shopify Admin Policies: Refund policy hiện dùng 30 calendar days cho damaged, defective, or incorrect items.

Đã đồng bộ các nội dung theme đang lệch 7 days sang 30 calendar days:
- FAQ page (/pages/faq): câu "My piece arrived damaged or incorrect. What should I do?" yêu cầu liên hệ trong 30 calendar days, kèm order number, mô tả lỗi, ảnh sản phẩm, toàn bộ packaging, shipping label, visible damage và video nếu phù hợp.
- PDP (/products/...): accordion Delivery & Refunds đổi heading thành "Report within 30 calendar days" và đồng bộ bằng chứng cần gửi theo policy.
- PDP (/products/...): drawer Damage & Defect Support đổi claim window và important note sang 30 calendar days.
- Homepage (/): FAQ snapshot câu "What happens if my piece arrives damaged?" đổi sang 30 calendar days và bổ sung yêu cầu ảnh/video theo policy.

Đã kiểm tra không còn "7 calendar days", "within 7 days", hoặc "7 days of delivery" trong các template/section/snippet liên quan. Đã validate templates/page.faq.json và templates/index.json (có header comment auto-generated) hợp lệ. Không chạy shopify theme check theo yêu cầu.
```

## 3. Delivery & Installation

- Khu vực giao chính: toàn thế giới

## 4. Quy trình giảm rủi ro trước sản xuất

- Có bước gửi video quay sản phẩm cho khách trước khi giao hàng để khách xác nhận, tránh rủi ro khách không hài lòng khi nhận hàng.
- Khách có được tư vấn miễn phí trước khi order.

## 5. Bằng chứng đơn hàng thật / case study

- tôi chỉ có video đục đẽo, cưa (tên file video trên Shopify Files là wrydeco-handcrafting-process-workshop.mp4) & video lắp ráp sản phẩm, ghép các phần sản phẩm lại với nhau (tên file video trên Shopify Files là wrydeco-workshop-product-assembly.mp4) & ảnh đóng gói sản phẩm (tên file ảnh trên Shopify Files là wrydeco-product-packaging-for-shipping.jpg).

## 6. Các trust claims nào là thật

- giữ nguyên trust bar: 387 reviews, 4.9 rating, 500+ homes, 99% satisfaction, 27+ years

## 7. Review thật

- danh sách review có verified nhưng chỉ hiển thị ở PDP
- ko có nền tảng review bên ngoài như Judge.me, Shopify Reviews, Trustpilot, Etsy, Google Business

## 8. Best Seller

- Sản phẩm thực sự là best seller là: rustic-wood-tree-branch-floating-bookshelf-4-tier-decor, tree-bookshelf-handcrafted-natural-wood-wall-shelf, natural-wood-corner-tree-branch-bookshelf-custom-design

## 9. Tone copy

- thay các từ tự khen bằng các từ nhẹ hơn nhưng vẫn phù hợp với bối cảnh của từ gốc

## 10. Quyền sửa nội dung

- sửa trực tiếp Liquid/JSON template/section/snippet liên quan đến PDP, About, FAQ, footer. Trừ policy phải giữ nguyên, những gì liên quan đến policy thì phải lấy policy làm chuẩn để sửa theo
