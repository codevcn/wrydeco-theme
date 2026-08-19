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

### Kết quả fix point 3:

```text
Đã đối chiếu Shipping Policy live tại https://wrydeco.com/policies/shipping-policy: WRYDECO offers worldwide shipping to eligible destinations; complimentary standard shipping applies to eligible worldwide orders; standard shipping does not include assembly, installation, wall mounting, furniture placement, packaging removal, or property modification unless expressly confirmed in writing.

Đã đồng bộ các nội dung delivery/installation trong theme:
- FAQ page (/pages/faq): cập nhật câu timeline từ United States sang eligible destinations worldwide; cập nhật câu "Is shipping included, and who delivers it?" sang eligible addresses worldwide; cập nhật câu "Can you deliver outside the United States?" để nói WRYDECO offers worldwide shipping to eligible destinations.
- PDP (/products/...): cập nhật drawer Free Delivery từ eligible United States addresses sang eligible addresses worldwide; giữ rõ standard delivery không gồm unpacking/assembly; optional/specialized services phải confirmed separately/in writing.
- PDP (/products/...): cập nhật default trust delivery title/text thành "Worldwide delivery available" và "Complimentary standard shipping for eligible destinations."
- Product benefits fallback: đổi "White-glove delivery & setup" thành "Complimentary worldwide standard shipping."
- Cart drawer: đổi reassurance từ "White-glove delivery details confirmed at checkout" thành "Special delivery services confirmed separately."
- Wishlist page: đổi assurance từ "White-Glove Delivery / Carefully delivered and placed in your home" sang "Worldwide Standard Shipping / Included for eligible destinations; special services confirmed separately."
- Homepage/trust/preset copy: đổi "White-Glove Delivery US" hoặc "White-glove service" sang wording an toàn hơn như "Worldwide Standard Shipping" hoặc "Special handling available."
- Customization process default: đổi "Delivery & installation" sang "Delivery Coordination" và nói rõ specialized delivery, placement, assembly, or installation service must be confirmed separately in writing.
- Footer config: service area đổi thành eligible destinations worldwide.

Đã kiểm tra không còn các cụm "White-Glove Delivery US", "White-glove delivery", "White glove delivery", "White-glove delivery & setup", "white-glove service", "Carefully delivered and placed", "eligible United States addresses", "United States addresses", hoặc "US & EU" trong templates/sections/snippets. Đã validate JSON/JSONC và section schemas liên quan. Không chạy shopify theme check theo yêu cầu. Không chạy Playwright vì các thay đổi ở point này là minor copy sync, không tạo UI mới hoặc sửa đáng kể layout/UI hiện có.
```

## 4. Quy trình giảm rủi ro trước sản xuất

- Có bước gửi video quay sản phẩm cho khách trước khi giao hàng để khách xác nhận, tránh rủi ro khách không hài lòng khi nhận hàng.
- Khách có được tư vấn miễn phí trước khi order.

### Kết quả fix point 4:

```text
Đã đồng bộ quy trình giảm rủi ro trước sản xuất/giao hàng vào các nội dung SSR chính:
- PDP (/products/...): cập nhật Order Process & Delivery để nói rõ có gửi sample photos/video ở giai đoạn duyệt mẫu, gửi final photos/video trước khi đóng gói, chỉ pack sau khi khách final confirmation, và đổi bước shipping sang wording an toàn theo eligible destination.
- PDP (/products/...): cập nhật card Private design guidance thành complimentary consultation before ordering để khách hiểu có thể hỏi về dimensions, finish, layout, fit trước khi mua.
- FAQ page (/pages/faq): cập nhật production timeline, consultation và bespoke commission answers để nói rõ consultation miễn phí trước khi order, duyệt specification/quote trước production, và final photos/video trước packing.
- Homepage (/): cập nhật custom order steps thành "Approve, Craft & Confirm" và "Pack & Ship"; cập nhật Private Styling Consultation để nhấn mạnh complimentary consultation before ordering và final photos/video confirmation before packing.
- Homepage FAQ snapshot (/): cập nhật câu made-to-order để nói rõ gửi final photos/video trước packing; đồng thời sửa nốt các câu shipping còn sót từ United States sang eligible destinations/address worldwide.
- Customization page (/pages/customization): cập nhật FAQ pricing/timeline/delivery và default process copy để nói rõ complimentary consultation, final photos/video confirmation, và delivery/specialized services được confirm riêng bằng văn bản.
- Custom consultation section default: cập nhật description và benefit copy để nêu rõ consultation miễn phí trước khi order và support tới final confirmation.

Đã validate JSON/JSONC cho templates/product.json, templates/index.json, templates/page.faq.json, templates/page.customization.json và section schemas cho sections/customization-process.liquid, sections/customization-consultation.liquid. Không chạy shopify theme check theo yêu cầu. Không chạy Playwright vì point này chỉ là minor copy/content sync, không tạo UI mới hoặc sửa layout/UI đáng kể.
```

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
