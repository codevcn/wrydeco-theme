# Phase 1

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

### Ghi chú:

```text
Sửa sau theo yêu cầu. Khi quay lại point này, hướng an toàn là không gọi đây là case study của một đơn hàng cụ thể vì media hiện có đến từ nhiều sản phẩm khác nhau; nên trình bày như workshop/process evidence thật của WRYDECO.
```

## 6. Các trust claims nào là thật

- review/rating lấy data realtime từ Loox global_stats cho toàn store/catalog; các claim còn lại giữ: 500+ homes, 99% satisfaction, 27+ years

### Kết quả fix point 6:

```text
Đã rà và đồng bộ các trust claim dạng số liệu tĩnh trong theme theo bộ claim được duyệt ban đầu; sau cập nhật mới bên dưới, review count/rating đã chuyển sang Loox realtime:
- 500+ homes
- 99% satisfaction
- 27+ years

Các thay đổi cụ thể:
- Trust statistics section: đổi "50+ Handcrafted Pieces" thành "500+ Homes Styled".
- Trust statistics section: đổi "100% PREVIEWED & APPROVED" thành "99% Client Satisfaction".
- Styling consultation advisor stats: đổi "32+ Years of Experience" thành "27+ Years of Experience".
- Product rating summary placeholder ban đầu: đổi "390+ reviews" thành "387 reviews"; sau cập nhật mới, PDP rating summary đã lấy count/rating từ Loox realtime.

Đây là minor copy/stat sync, không tạo UI mới và không sửa layout. Không chạy shopify theme check theo yêu cầu.
```

### Cập nhật point 6:

```text
Theo yêu cầu mới, phần "Verified Client Reviews" dưới hero homepage và rating summary dưới price trên PDP không dùng số hardcode hoặc product-level reviews nữa.

Đã kiểm tra Shopify Admin GraphQL: shop metafield Loox `loox.global_stats` hiện trả dạng `rating,count` và đang có giá trị realtime từ Loox là `4.7,226`.

Đã cập nhật:
- Homepage trust statistics: stat "Verified Client Reviews" lấy count từ `shop.metafields.loox["global_stats"]`; stat "Average Rating" lấy rating trung bình từ cùng nguồn Loox.
- PDP rating summary dưới price: lấy rating trung bình và tổng review toàn store/catalog từ `shop.metafields.loox["global_stats"]`, không còn phụ thuộc `product.metafields.loox.avg_rating` hoặc `product.metafields.loox.num_reviews`.

Nếu Loox global_stats đổi số, UI sẽ đổi theo dữ liệu Loox realtime trong Liquid SSR.

Đã dùng Playwright kiểm tra trên Shopify theme dev local:
- Homepage trust bar hiển thị "226 Verified Client Reviews" và "4.7 Average Rating".
- PDP rating dưới price hiển thị "4.7 (226 reviews)".
- Đã lưu ảnh kiểm tra tại `test-results/loox-homepage-trust-clean.png` và `test-results/loox-pdp-rating.png`.
```

## 7. Review thật

- tôi có danh sách review có verified nhưng chỉ nên hiển thị ở PDP
- ko có nền tảng review bên ngoài như Judge.me, Shopify Reviews, Trustpilot, Etsy, Google Business

### Kết quả fix point 7:

```text
Đã giữ nguyên homepage testimonial/review section tự render theo yêu cầu, không xóa khỏi homepage.

Đã giữ PDP Loox reviews là nguồn review chính:
- PDP vẫn dùng Loox app block tại section `loox-product-reviews-heading`.
- Đã chỉnh heading PDP review section từ "Product Reviews / What are our collectors saying?" thành "Verified Reviews / What our customers are saying" để nhấn mạnh nguồn review verified trên PDP.
- Không thêm claim về Judge.me, Shopify Reviews, Trustpilot, Etsy hoặc Google Business vì không có nền tảng review bên ngoài.

Đã kiểm tra lại bằng Playwright trên Shopify theme dev local:
- Homepage testimonial/review section tự render vẫn còn hiển thị.
- PDP Loox review section hiển thị heading mới "Verified Reviews / What our customers are saying".
- Trong theme dev preview, Loox app block vẫn có trạng thái loader "Reviews are taking a little longer to appear"; đây là phần app-rendered review list, không phải phần heading/copy theme vừa sửa.
- Đã lưu ảnh kiểm tra tại `test-results/point-7-home-testimonials-clean.png` và `test-results/point-7-pdp-loox-reviews-clean.png`.
```

## 8. Best Seller

- Sản phẩm thực sự là best seller là: rustic-wood-tree-branch-floating-bookshelf-4-tier-decor, tree-bookshelf-handcrafted-natural-wood-wall-shelf, natural-wood-corner-tree-branch-bookshelf-custom-design

### Kết quả fix point 8:

```text
Đã chuyển logic hiển thị badge "Best Seller" sang nguồn dữ liệu metaobject first entry theo yêu cầu.

Nguồn dữ liệu chuẩn:
- Metaobject type: `outstanding_materials`
- Entry: first entry
- Field: `best_seller_products`
- Format: text chứa product handles cách nhau bằng dấu phẩy

Đã kiểm tra Shopify Admin GraphQL: first entry hiện có value:
`rustic-wood-tree-branch-floating-bookshelf-4-tier-decor, tree-bookshelf-handcrafted-natural-wood-wall-shelf, natural-wood-corner-tree-branch-bookshelf-custom-design`

Đã cập nhật:
- Homepage Signature Pieces: badge "Best Seller" chỉ hiện nếu `product.handle` nằm trong `metaobjects.outstanding_materials.values | first`.best_seller_products; không còn dựa vào collection `signature-pieces`.
- Collection product cards: badge "Best Seller" chỉ hiện theo cùng metaobject field; badge này vẫn ưu tiên hơn "New" nếu một sản phẩm vừa là best seller vừa thuộc new arrivals.
- PDP gallery/media chính: badge "Best Seller" cũng chỉ hiện theo cùng metaobject field.
- Đã cập nhật comment/schema info để không còn mô tả sai rằng Best Seller dựa vào collection `signature-pieces`.

Đã dùng Playwright kiểm tra trên Shopify theme dev local:
- Homepage Signature Pieces: chỉ 3 handles trong metaobject hiện badge "Best Seller"; các card khác hiện "Most Loved".
- `/collections/all`: 3 handles trong metaobject hiện badge "Best Seller"; các sản phẩm khác không bị gắn Best Seller sai.
- PDP best-seller `rustic-wood-tree-branch-floating-bookshelf-4-tier-decor`: gallery/media chính có badge "Best Seller".
- PDP non-best-seller `custom-handcrafted-wave-solid-oak-wood-coffee-table`: gallery/media chính không có badge "Best Seller".
- Đã lưu ảnh kiểm tra tại `test-results/point-8-home-signature-pieces.png`, `test-results/point-8-collection-all.png`, `test-results/point-8-best-pdp-gallery.png`, `test-results/point-8-non-best-pdp-gallery.png`.

Cập nhật theo yêu cầu mới:
- Homepage Signature Pieces không còn hiển thị các badge phụ như "Most Loved" hoặc "Made to Order" trên product cards.
- Section này chỉ giữ lại badge "Best Seller" cho các product handles nằm trong metaobject `outstanding_materials.best_seller_products`.
```

## 9. Tone copy

- thay các từ tự khen bằng các từ nhẹ hơn nhưng vẫn phù hợp với bối cảnh của từ gốc

### Kết quả fix point 9:

```text
Đã làm nhẹ các cụm copy tự khen mạnh trong các khu vực chính, giữ tone premium/luxury nhưng giảm các claim tuyệt đối.

Các hướng chỉnh chính:
- "masterfully crafted" -> "thoughtfully crafted" hoặc "careful handwork".
- "statement of nature, artistry, and enduring quality" -> "natural form, careful handwork, and lasting character".
- "Exceptional craftsmanship" -> "Thoughtful craftsmanship".
- "masterpiece flawlessly fits and elevates your architecture" -> "piece fits naturally within your architecture".
- "ultimate protection", "heirloom quality", "last generations" -> wording thực tế hơn về hand finishing, solid materials, daily living, long-term use.
- "Why collectors choose this piece" -> "Why this piece works well" theo điều chỉnh đã duyệt.
- "functional art" trong About/FAQ defaults -> "furniture that reflects natural form, careful handwork, and lasting character".
- "perfect/perfectly", "premium", "exceptional" trong customization/styling defaults -> wording nhẹ hơn như "with care", "solid natural wood", "considered", "personal".

Đã cập nhật các file chính:
- Homepage/template copy: `templates/index.json`, `sections/hero-banner.liquid`, `sections/signature-pieces.liquid`, `sections/materials-craftsmanship.liquid`, `sections/meet-the-makers.liquid`.
- PDP copy: `sections/main-product.liquid`, `templates/product.json`, `snippets/product-detail-tab-content.liquid`.
- About/FAQ copy: `templates/page.about-us.json`, `templates/page.faq.json`, `sections/main-about-page.liquid`, `sections/main-faq-page.liquid`, `sections/about-craftsmanship.liquid`.
- Footer/wishlist/customization/styling copy: `sections/footer.liquid`, `snippets/wishlist-page-initial.liquid`, `snippets/wishlist-page-custom.liquid`, `sections/customization-consultation.liquid`, `sections/customization-gallery.liquid`, `sections/customization-process.liquid`, `sections/styling-consultation.liquid`.

Đã validate JSON/JSONC và section schemas cho các file liên quan. Đã dùng Playwright smoke check trên Shopify theme dev local cho homepage, PDP, About, FAQ và Customization:
- PDP render "Why this piece works well".
- About render "Where Natural Wood Meets Useful Form" và "Let’s Create Something Thoughtful".
- FAQ render intro mới với "reflects natural form, careful handwork".
- Customization render "Refined in three steps" và "something personal".
- Homepage render copy consultation mới "fits naturally within your architecture"; một số homepage copy/template defaults đã sửa không xuất hiện trong DOM hiện tại vì section/settings tương ứng không render dòng đó trên preview.

Không chạy `shopify theme check` theo yêu cầu.
```

## 10. Quyền sửa nội dung

- sửa trực tiếp Liquid/JSON template/section/snippet liên quan đến PDP, About, FAQ, footer. Trừ policy phải giữ nguyên, những gì liên quan đến policy thì phải lấy policy làm chuẩn để sửa theo

### Ghi chú:

```text
chỉ là 1 lưu ý, ko phải vấn đề cần fix.
```

# Phase 2

## 1. Media Thật

- ko có ảnh thật của từng artisan/nghệ nhân.
- có ảnh/video xưởng: cưa, đục, chà nhám, ghép, hoàn thiện, đóng gói.
- ko có ảnh gỗ thô, vân gỗ, mắt gỗ, cạnh live edge, các biến thể màu/vân thật.
- ko có Video/ảnh kỹ thuật: mối nối, khung đỡ, bracket, wall mounting, điểm chịu lực.
- có Ảnh sản phẩm trong nhà thật hoặc ảnh có vật chuẩn như sofa/người/cửa. (dữ liệu review file csv có sẵn)

### Ghi chú:

```text
Sửa sau theo yêu cầu. Khi quay lại point này, hướng an toàn là dùng media thật hiện có như workshop/process evidence của WRYDECO, không gọi là case study hoàn chỉnh của một đơn hàng cụ thể nếu media đến từ nhiều sản phẩm khác nhau. Không dùng ảnh artisan, ảnh gỗ thô, ảnh biến thể gỗ hoặc media kỹ thuật nếu chưa có dữ liệu thật.
```

### Kết quả fix point 1:
```text
Đã triển khai section mới "Workshop Evidence" trên PDP, đặt bên dưới Product Author và bên trên "No Two Pieces Are Ever Truly Alike".

Data media lấy từ first entry của metaobject `store_media_info`:
- Video handcrafting: field `proof_handcratf_video_url`.
- Video assembly: field `proof_assembly_video_url`.
- Packaging fanned cards: parse field `proof_packaging_image_urls`, các URL cách nhau bởi dấu phẩy.

Đã tạo `sections/workshop-evidence.liquid` với nội dung SSR-first: heading, subheading, 2 video proof cards, fanned packaging cards, labels Handcrafting / Assembly / Packaging. Section chỉ render khi có ít nhất một media thật.

Cập nhật follow-up: đã bỏ CTA "Explore Craftsmanship" khỏi section. Packaging fan được thay bằng carousel ảnh trong card theo design mới, có nút Previous/Next nằm trên mép khối và slider dots ở đáy khối. User bấm vào ảnh packaging sẽ mở lightbox ảnh đơn; đã bỏ preview modal carousel cũ.

Đã thêm section vào `templates/product.json` theo đúng vị trí yêu cầu: sau `product_artist`, trước `no_two_pieces_alike`.

Đã dùng Iconify tool trong `my-tools/iconify` để lấy inline SVG icon mới theo CODING_RULES.md.

Đã validate `templates/product.json` và schema `sections/workshop-evidence.liquid`. Không chạy shopify theme check theo yêu cầu. Đã dùng Playwright kiểm tra PDP local ở desktop 1520x900, tablet 820x1180 và mobile 390x844: HTTP 200, section render đúng, có 2 video không còn native controls/fullscreen button, packaging carousel có 5 slides/5 dots/2 nav buttons, lightbox mở và đóng đúng, không horizontal overflow.
```

## 2. Artisan Info

- Toàn bộ thông tin về artisan như "Tên artisan muốn public", "Vai trò", "Số năm kinh nghiệm", "avatar" đều lấy từ data thật trong metaobject trên store.
- 1-2 sản phẩm/dòng sản phẩm từng làm. (note vào file "point sửa sau.md" để sau này quay lại làm)

### Kết quả fix point 2:

```text
Đã kiểm tra Shopify Admin GraphQL: metaobject `product_author` hiện có 6 entries thật và có các field: author_name, role, exp_years, author_image_url, author_bio, author_slogan, display_features.

Đã đồng bộ theme để thông tin artisan cá nhân chỉ lấy từ dữ liệu thật trong `product_author`:
- Homepage Meet the Makers (/): `snippets/maker-card.liquid` không còn fallback tên/role/avatar giả như WRYDECO Maker hoặc Master Craftsperson; section vẫn dùng `metaobjects.product_author.values`.
- About page (/pages/about-us): `snippets/about-makers-carousel.liquid` không còn fallback tên/role/avatar giả; `display_features` vẫn được dùng để render các điểm đặc trưng artist.
- PDP (/products/...): `sections/product-artist.liquid` lấy role từ `author.role.value`, years từ `author.exp_years.value`, và chỉ render section khi có author info thật.
- Author profile page: `sections/metaobject-product-author.liquid` bỏ fallback/hardcode như Our Artist, Lead Artist & Craftsman, 20+ Years of Dedication to Wood; role/years/stats lấy từ metaobject.
- Product cards/cart/search: bỏ fallback dùng `product.vendor` làm maker/artist trong `sections/signature-pieces.liquid`, `sections/collection.liquid`, `sections/search-v3.liquid`, `sections/cart-drawer.liquid`.
- Homepage template: xóa các block maker hardcode cũ trong `templates/index.json`.
- Product template: xóa setting `role_label` hardcode khỏi `templates/product.json`.

Đã note phần "1-2 sản phẩm/dòng sản phẩm từng làm" vào `todo/point sửa sau.md` vì hiện metaobject chưa có field/link dữ liệu chuẩn để public claim này.

Đã validate JSON/section schema cơ bản cho templates/index.json, templates/product.json, sections/meet-the-makers.liquid, sections/product-artist.liquid, sections/metaobject-product-author.liquid. Không chạy shopify theme check theo yêu cầu. Không chạy Playwright vì point 2 chưa thuộc rule bắt buộc từ point 3 trở đi và thay đổi không tạo UI mới.
```

## 3. Thông Tin Kết Cấu / Độ Bền

- các thông tin như "Tải trọng khuyến nghị cho từng dòng chính", "Loại mối nối/khung/bracket/hardware đang dùng", "Dòng nào cần wall mounting, dòng nào free-standing" sẽ được bao gồm trong tài liệu hướng dẫn sử dụng khi nhận hàng
- tùy sản phẩm có dịch vụ lắp đặt, tùy sản phẩm ko có

### Kết quả fix point 3:

```text
Đã cập nhật nội dung construction/durability/installation theo quyết định mới: không public thông số tải trọng, bracket, hardware, hoặc wall/free-standing cụ thể trên website khi chưa có data thật; các thông tin này được nói là nằm trong product-specific guidance đi kèm khi nhận hàng, nếu applicable.

Các thay đổi đã làm:
- PDP accordion Dimensions: thêm note rằng use, placement, mounting, hardware, and recommended load guidance được cung cấp cùng sản phẩm khi applicable và dựa trên final design.
- PDP accordion Delivery & Refunds: thêm item "Installation guidance", làm rõ một số sản phẩm freestanding, một số có thể cần wall mounting/anchoring/professional installation; standard shipping không bao gồm installation nếu chưa được confirm in writing.
- PDP accordion Care Guide: thêm ý delivered piece includes product-specific use, placement, and care guidance where applicable.
- PDP product comparison feature "Hand-shaped joinery": giảm claim quá cụ thể, chuyển sang wording an toàn về hand-shaped/assembled for long-term residential use và guidance theo từng sản phẩm.
- PDP Order Process & Delivery: cập nhật bước packing/shipping/lead delivery để nói product-specific use or installation guidance được included where applicable, còn specialized installation/placement service phải confirmed separately in writing.
- FAQ page (/pages/faq): cập nhật shipping, care/restoration, và warranty answers để đồng bộ: installation/specialized services confirmed in writing; product-specific mounting/hardware/recommended load guidance đi kèm khi applicable; warranty không cover misuse, incorrect installation, unsuitable environments, excessive load, hoặc post-delivery alterations.

Không ghi note vào `todo/point sửa sau.md` theo yêu cầu. Đã validate JSON/section schema cơ bản cho templates/product.json, templates/page.faq.json, sections/order-process-delivery.liquid, snippets/product-detail-tab-content.liquid. Không chạy shopify theme check theo yêu cầu. Không chạy Playwright vì đây là copy/content sync minor trong UI hiện có, không tạo UI mới hoặc sửa layout đáng kể.
```

## 4. Quy Trình Custom Order

- quy trình custom order:
```text
Khách gửi yêu cầu tư vấn
↓
Yêu cầu tư vấn được gửi tới server riêng của Wrydeco thành công
↓
Hệ thống tự động gửi email xác nhận đã nhận yêu cầu từ khách
↓
WRYDECO xem xét yêu cầu tư vấn
↓
Liên hệ khách hàng
Email / Điện thoại / WhatsApp để trao đổi chi tiết nhu cầu
↓
Trao đổi nhu cầu
Kích thước / Màu sắc / Không gian / Thiết kế / ...
↓
Khách hàng gửi kích thước thực tế / hình ảnh không gian
↓
WRYDECO đề xuất phương án phù hợp
↓
Gửi báo giá + thông số chi tiết của sản phẩm
↓
Khách hàng xác nhận
↓
Tạo Draft Order trên Shopify
↓
Khách hàng thanh toán qua invoice email / link thanh toán
↓
Gửi bản thiết kế / proof để khách duyệt
↓
Sản xuất
↓
Giao hàng
```
- Sau khi order, khách còn được đổi gì và đến thời điểm nào sẽ dựa hoàn toàn vào chính sách, đọc các file html trong folder `backup\policy\public` để biết tất cả các nội dung chính sách hiện tại. Không thêm claim gì ngoài chính sách.
- Consultation là miễn phí.
- Consultation có thể kéo dài tùy vào nhu cầu của khách và đội ngũ tư vấn của WRYDECO, cố gắng ko đề cập thời gian cụ thể.
- Response time: trong 24-48 giờ (business day).
- CTA chính muốn dùng: Book Consultation.

### Kết quả fix point 4:
```text
Đã đồng bộ custom order / consultation flow theo quyết định mới:

- Customization page (/pages/customization): cập nhật process thành Book Consultation -> Review Scope & Quote -> Approve, Pay & Produce; nêu rõ request được review, trao đổi qua email/phone/WhatsApp khi cần, gửi scope/spec/quote, secure payment link, proof approval, production, final confirmation và delivery coordination.
- Customization hero và guidance card (/pages/customization): đổi CTA cũ "Request a consultation" / "Schedule a consultation" sang "Book Consultation".
- Customization consultation form (/pages/customization): đổi CTA thành "Book Consultation"; request label/placeholder tập trung vào project, room, dimensions, finish direction, budget range, timeline, references; thêm response time "24-48 business hours" trong security text và success message; không nêu duration cố định.
- PDP consultation CTA/popup (/products/...): đổi CTA thành "Book Consultation"; copy nhấn mạnh complimentary consultation before ordering, response within 24-48 business hours; bỏ claim 30 minutes và bỏ timezone label khỏi selected consultation result.
- Homepage (/): cập nhật made-to-order steps, materials/custom CTA, styling consultation, và FAQ snapshot để đồng bộ flow: request, scope & quote, secure payment link, proof/production, final confirmation, packing/shipping; không dùng response 24 hours hoặc duration cố định.
- FAQ page (/pages/faq): cập nhật answers về custom request, consultation, full bespoke commission, cancellation/change theo đúng policy: change/cancellation chỉ có thể được xem xét trước khi production/preparation/fulfillment bắt đầu; custom/made-to-order không thể cancel/change/return/refund sau đó trừ trường hợp luật yêu cầu hoặc issue damage/defect/fulfillment được duyệt.
- Product Order Process & Delivery (/products/...): đã revert về wording cũ theo yêu cầu vì quy trình custom order đã được mô tả rõ ở trang Customization.
- Đồng bộ CTA default "Book Consultation" ở các section phụ liên quan để tránh merchant thêm section mới mà kéo lại wording cũ.

Đã validate JSON/JSONC và section schemas cho các file liên quan. Không chạy shopify theme check theo yêu cầu. Đã chạy Playwright sau khi sửa để kiểm tra UI customization/PDP/homepage/FAQ ở local Shopify theme dev.
```

## 5. Support Timezone / Địa Chỉ

- Public support timezone muốn dùng: Central Time (CT)
- Support hours chính xác là 24/7
- Response time muốn cam kết: trong 24-48 giờ (business day).
- Địa chỉ Mỹ hiện tại là loại "registered business address"
- ko có showroom cho khách ghé thăm

### Kết quả fix point 5:
```text
Đã đồng bộ support timezone / địa chỉ theo quyết định mới:

- Footer toàn site: đổi label địa chỉ thành "Registered Business Address"; support hours fallback thành "24/7 online support, Central Time (CT)".
- Footer group JSON: đổi support hours cũ "Daily: 9AM - 8:30PM (Asia/Saigon)" thành "24/7 online support, Central Time (CT)"; thêm note rõ không có retail showroom hoặc walk-in visits.
- Homepage FAQ/support sidebar (/): đổi support hours thành "24/7 online support, Central Time (CT)".
- Contact page (/pages/contact): đổi address label default thành "Registered Business Address"; đổi online support default thành "24/7 online support, Central Time (CT)"; không còn wording "Private showroom visits by appointment"; consultation info hiển thị "Online by appointment. No retail showroom or walk-in visits."
- FAQ contact CTA (/pages/faq): đổi response time default thành "We respond within 24-48 business hours."
- Shopify metaobject store_legal_info: cập nhật online_store_hours thành "24/7 online support, Central Time (CT)" và consultation_hours thành "Online by appointment. No retail showroom or walk-in visits." để tránh dữ liệu store override theme fallback.

Đã validate JSON/JSONC và section schemas cho các file liên quan. Không chạy shopify theme check theo yêu cầu. Đã dùng Playwright kiểm tra homepage, contact page và FAQ page ở desktop 1520x900 và mobile 390x844: HTTP 200, không horizontal overflow, text mới render đúng, không còn các cụm cũ Asia/Saigon, EST, Mon-Sat, private showroom visits, hoặc response within two business days.
```

## 6. External Proof

- ko có Google Business Profile
- mấy kênh socials của wrydeco có link hết ở footer rồi, và đều là link sống 100% ko cần kiểm tra
- ko có dấu vết thương hiệu ngoài website

### Kết quả fix point 6:
```text
Đã xử lý External Proof theo hướng không overclaim:

- Không thêm Google Business Profile, Trustpilot, Etsy, PR, directory, marketplace, hoặc external proof section vì hiện chưa có nguồn thật để public.
- Đã rà soát theme files và không thấy claim public kiểu Google Business, Trustpilot, Etsy, "as seen on", "featured on", hoặc "verified by external platform".
- Giữ nguyên social links hiện có ở footer vì đây là các kênh WRYDECO đã confirm: TikTok, YouTube, Pinterest, Facebook, Instagram, Amazon.
- Footer toàn site: đổi nhãn social từ "Follow Us" thành "Follow WRYDECO" để rõ đây là kênh theo dõi brand, nhưng không claim "verified" hoặc nguồn xác thực bên ngoài.

Đã validate schema sections/footer.liquid. Không chạy shopify theme check theo yêu cầu. Đã dùng Playwright smoke check homepage footer ở desktop 1520x900 và mobile 390x844.
```
