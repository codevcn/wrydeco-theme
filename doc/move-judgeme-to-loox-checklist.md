# Checklist chuyển từ Judge.me sang Loox

## Mục tiêu

- Giữ nguyên toàn bộ published reviews hợp lệ khi chuyển nền tảng.
- Trên mọi PDP, hiển thị một khu vực **Collector Reviews** lấy visual reviews từ toàn catalog hoặc từ danh sách review được curate thủ công.
- Review Widget chính trên PDP chỉ hiển thị reviews của sản phẩm hiện tại.
- Rating dưới giá và rating trên product card chỉ phản ánh đúng sản phẩm tương ứng.
- Không để Judge.me và Loox đồng thời gửi review-request emails, render widget trùng hoặc tạo structured data trùng.
- Duy trì kiến trúc Liquid SSR-first, khả năng truy cập, hiệu năng và phong cách cao cấp của WRYDECO.

## Trạng thái ban đầu

- [x] Đã export file CSV **published reviews** từ Judge.me.
- [x] Đã cài đặt Loox trên Shopify store.
- [x] Lưu một bản CSV gốc không chỉnh sửa ở nơi an toàn.
- [x] Ghi lại tổng số published reviews trong Judge.me trước migration.
- [x] Ghi lại số reviews, average rating và số visual reviews của một số sản phẩm đại diện để đối chiếu sau import.
- [x] Ghi lại plan hiện tại của Judge.me và plan/trial hiện tại của Loox.

## 2. Kiểm tra và import dữ liệu reviews

- [x] Kiểm tra file CSV có các cột quan trọng:
  - [x] Product ID hoặc product handle.
  - [x] Rating.
  - [x] Review title và body.
  - [x] Reviewer name.
  - [x] Review date.
  - [x] Image URLs.
  - [x] Public reply nếu có.
- [x] Không sửa trực tiếp file CSV gốc; chỉ chỉnh trên một bản sao nếu Loox báo lỗi import.
- [x] Trong Loox, chọn đúng luồng import dành cho **Judge.me** và upload file CSV đúng định dạng đã export.
- [x] Lưu email import summary từ Loox.
- [x] Nếu có dòng import thất bại:
  - [x] Tải error CSV từ Loox.
  - [x] Phân loại lỗi theo product mapping, dữ liệu thiếu, encoding, URL ảnh hoặc định dạng ngày.
  - [x] Sửa trên bản sao CSV và chỉ re-import các dòng lỗi để tránh duplicate.
- [x] Đối chiếu tổng số reviews import thành công với tổng published reviews trong Judge.me.
- [x] Kiểm tra ít nhất các nhóm dữ liệu sau trong Loox:
  - [x] Review 5 sao và 4 sao.
  - [x] Review có một ảnh.
  - [x] Review có nhiều ảnh.
  - [x] Review text-only.
  - [x] Review có public reply.
  - [x] Review có ký tự đặc biệt hoặc nội dung dài.
  - [x] Review của product đã đổi handle nếu có.
- [x] Kiểm tra ảnh review thực sự tải được, không chỉ có URL trong dashboard.
- [x] Xác nhận attribution: mỗi review vẫn liên kết đúng product gốc.

## 3. Cấu hình Loox trước khi đưa lên storefront

- [x] Kiểm tra Loox core script/app embed đã được bật trên theme migration.
- [x] Cấu hình branding theo design system WRYDECO:
  - [x] Typography.
  - [x] Star color.
  - [x] Text và background colors.
  - [x] Button styling.
  - [x] Border radius và spacing.
- [x] Cấu hình ngôn ngữ storefront hoàn toàn bằng English.
- [x] Cấu hình moderation và auto-publish phù hợp với chính sách review của store.
- [x] Kiểm tra sender name, reply-to email, timing, reminders và timezone.
- [x] Xác nhận Loox plan đáp ứng nhu cầu hiện tại và ngưỡng total orders của Beginner.

## 4. Collector Reviews trên mọi PDP

- [x] Đã pull cấu hình **Loox Cards Carousel** từ live theme về local.
- [x] Kích hoạt Loox Cards Carousel trong product template và loại Judge.me Cards Carousel khỏi template để không render trùng.
- [x] Đặt carousel ở vị trí hiện tại của section Collector Reviews, trước Review Widget chính.
- [x] Dùng Cards Carousel toàn catalog (`productIds` để trống) để ưu tiên visual reviews từ nhiều sản phẩm trên mọi PDP.
- [ ] Nếu sau này cần kiểm soát chính xác từng review, chuyển sang **Curated:** Trong Manage Reviews, dùng `Add to Widgets > Add to Carousels` cho từng review muốn trưng bày.
- [ ] Nếu dùng Curated, chọn đủ review có ảnh chất lượng cao để carousel ổn định trên desktop và mobile.
- [x] Xác nhận quickview của review chéo sản phẩm có liên kết “View product” trỏ về product gốc.
- [x] Dùng heading rõ ràng như “What Our Collectors Are Saying” để khách hiểu đây là social proof toàn catalog.

## 5. Review Widget riêng của product hiện tại

- [x] Thay Judge.me Review Widget trong PDP bằng Loox Reviews Widget.
- [x] Cấu hình widget chỉ lấy product reviews của sản phẩm hiện tại (`product_reviews_only`).
- [x] Không hiển thị store reviews trong widget chính trên PDP.
- [ ] Cấu hình rating distribution, sorting và reviews per page.
- [x] Xác nhận nút “Write a review” hiển thị bằng English trên product có reviews.
- [ ] Kiểm tra empty state và xác nhận toàn bộ nội dung empty state bằng English trên product chưa có review.
- [x] Đảm bảo Review Widget chính và Collector Reviews có mục đích trực quan khác nhau: Loox hiển thị review chi tiết của product hiện tại; Judge.me Collector Reviews tạm thời vẫn phục vụ social proof toàn catalog.

## 6. Thay rating badge và metafields trong theme

- [ ] Thay Judge.me rating dưới giá trong `sections/main-product.liquid`.
- [ ] Ưu tiên Shopify standard review metafields nếu dữ liệu Loox đã sync đúng:
  - [ ] `product.metafields.reviews.rating.value`
  - [ ] `product.metafields.reviews.rating_count`
- [ ] Nếu cần dùng Loox-specific metafields, kiểm tra:
  - [ ] `product.metafields.loox.avg_rating`
  - [ ] `product.metafields.loox.num_reviews`
- [ ] Render rating/count quan trọng bằng Liquid trong HTML ban đầu; chỉ dùng Loox JavaScript cho enhancement/interactivity.
- [ ] Không hiển thị rating giả hoặc empty stars nếu business rule không yêu cầu.
- [ ] Rating dưới giá chỉ dùng rating của product hiện tại, không dùng average rating toàn store.
- [ ] Thay Judge.me rating trong `sections/collection.liquid`.
- [ ] Thay Judge.me rating trong `sections/signature-pieces.liquid`.
- [ ] Tìm lại toàn codebase để bảo đảm không còn storefront reference ngoài ý muốn tới:
  - [ ] `product.metafields.judgeme.badge`
  - [ ] `judgeme.review_widget_data`
  - [ ] `.jdgm-*`
  - [ ] `.jm-*`

## 7. Cập nhật sections, CSS và JavaScript

- [x] Thay toàn bộ app block Judge.me trong `templates/product.json` bằng Loox app blocks trên theme migration.
  - [x] Đã thay riêng Judge.me Review Widget bằng Loox Reviews Widget.
  - [x] Đã chuyển Judge.me Collector Reviews sang Loox Cards Carousel.
- [x] Xóa `sections/judgeme-cards-carousel.liquid` sau khi Loox Cards Carousel đã thay thế hoàn toàn và không còn template nào tham chiếu section cũ.
- [ ] Thay thế `sections/judgeme-reviews.liquid`.
- [ ] Xóa Judge.me overrides trong `assets/base.css` sau khi Loox đã hoạt động ổn định.
- [ ] Không tái sử dụng các selector `.jm-*` hoặc `.jdgm-*` cho Loox.
- [ ] Không giữ `MutationObserver` trang trí Judge.me modal.
- [ ] Nếu custom giao diện Loox, scope CSS trong section để tránh ảnh hưởng widget khác.
- [ ] Viết CSS desktop-first và override bằng max-width breakpoints.
- [ ] Giữ touch targets tối thiểu 44x44px.
- [ ] Không thay đổi `display` của `.shopify-section`; nếu thực sự cần phải xin phép trước.
- [ ] Mọi icon mới phải là inline SVG và phải lấy/tạo qua Iconify theo `CODING_RULES.md`.
- [ ] Mọi thông báo tạm thời do custom JavaScript tạo ra phải dùng global `window.showToast(...)`.
- [ ] Chỉ dùng `file_url` cho file nằm trong Shopify Content > Files; giữ `asset_url` cho file thực sự nằm trong theme `assets/`.

## 8. SEO, SSR và structured data

- [ ] Kiểm tra rating/count của product có trong initial server-rendered HTML.
- [ ] Không dùng review toàn catalog làm `Product.aggregateRating` cho product hiện tại.
- [ ] Bảo đảm chỉ có một nguồn tạo `Product.aggregateRating` sau cutover.
- [ ] Bật rich snippets của Loox, tắt rich snippets của Judge.me.
- [ ] Kiểm tra JSON-LD không có aggregate rating trùng, sai product hoặc sai review count.
- [ ] Giữ nguyên canonical URL và index/noindex strategy của PDP.
- [ ] Bảo đảm tên product gốc và liên kết attribution là crawlable khi Loox hỗ trợ.
- [ ] Không coi carousel client-rendered là nguồn nội dung SEO chính của PDP.
- [ ] Kiểm tra trang vẫn truyền đạt đầy đủ product title, description, price và primary image khi tắt JavaScript.

## 9. Accessibility, responsive và performance QA

- [ ] Kiểm tra layout tại tối thiểu:
  - [x] Desktop 1440px cho Reviews Widget và Cards Carousel.
  - [ ] Laptop 1024px.
  - [ ] Tablet 768px.
  - [x] Mobile 390px cho Reviews Widget và Cards Carousel.
  - [ ] Mobile 320px hoặc viewport nhỏ tương đương.
- [ ] Kiểm tra ảnh review không tải kích thước quá lớn so với kích thước hiển thị.
- [ ] Kiểm tra Loox không làm chậm LCP của main product image.

## 10. Playwright test matrix

> Ở bước chuyển Reviews Widget, chạy các case Playwright cơ bản theo yêu cầu; các case carousel và migration hoàn chỉnh sẽ thực hiện ở bước tương ứng.

- [x] Chạy test trên product ID `8355494395961` có 54 reviews và review images.
- [ ] Chạy test trên một product không có review riêng nhưng Collector Reviews vẫn hiển thị review toàn catalog.
- [ ] Chạy test trên product có rating nhưng không có visual review.
- [ ] Xác nhận rating dưới giá khớp với Review Widget của product hiện tại.
- [x] Xác nhận review trong Collector Reviews có thể thuộc product khác.
- [x] Xác nhận product attribution/link trong Collector Reviews mở đúng product gốc.
- [ ] Test carousel arrows, swipe, pagination và modal/lightbox.
- [x] Test cơ bản Cards Carousel: visual reviews, ảnh tải hoàn chỉnh, desktop arrows, mobile active card và mở quickview.
- [ ] Test Review Widget sorting, filtering, pagination và Write a review.
- [x] Test cơ bản Reviews Widget: đúng Product ID, `product_reviews_only`, 54 reviews, giới hạn 15 reviews mỗi lần tải, nút Write a review và client hydration.
- [ ] Test empty state.
- [ ] Test responsive screenshots và so sánh với baseline Judge.me.
- [ ] Test bằng JavaScript disabled cho phần nội dung PDP quan trọng.
- [x] Lưu screenshots desktop/mobile và kết quả Playwright cho Reviews Widget và Cards Carousel trước khi publish.

## 11. Cutover

- [ ] Tạm dừng Judge.me review-request emails trước khi bật Loox emails.
- [ ] Nếu có review mới kể từ CSV ban đầu, export/import phần chênh lệch mà không tạo duplicate.
- [ ] Kiểm tra lần cuối review totals và product mapping.
- [ ] Disable Judge.me widgets/app embed trên theme chuẩn bị publish.
- [x] Enable Loox core script/app embed và Loox Reviews Widget trên theme migration.
- [ ] Enable các Loox widgets còn lại sau khi hoàn tất từng bước migration.
- [ ] Publish theme migration trong cửa sổ cutover đã chọn.
- [ ] Smoke test production ngay sau publish.
- [ ] Xác nhận chỉ Loox gửi review-request emails.
- [ ] Xác nhận chỉ một review app tạo structured data/rich snippets.
- [ ] Giữ Judge.me được cài nhưng không hoạt động trong một khoảng theo dõi ngắn để có thể rollback.

## 12. Theo dõi sau launch và hoàn tất migration

> Mục này để tôi làm thủ công, AI ko cần làm.

- [ ] Theo dõi import errors, widget errors và review-request delivery trong Loox.
- [ ] Kiểm tra review count/rating trên một nhóm product mỗi ngày trong giai đoạn đầu.
- [ ] Theo dõi Core Web Vitals và JavaScript errors.
- [ ] Kiểm tra Google Rich Results Test cho một số PDP tiêu biểu.
- [ ] Kiểm tra review mới đầu tiên được Loox thu thập, publish và hiển thị đúng product.
- [ ] Kiểm tra photo review mới xuất hiện trong quy trình curate/Carousel như mong muốn.
- [ ] Xác nhận dữ liệu Judge.me backup đã đầy đủ trước khi uninstall.
- [ ] Chỉ uninstall Judge.me sau khi:
  - [ ] Dữ liệu Loox đã được đối chiếu.
  - [ ] Loox emails hoạt động đúng.
  - [ ] Theme production ổn định.
  - [ ] Structured data không lỗi.
  - [ ] Thời gian rollback đã kết thúc.
- [ ] Sau khi uninstall, chạy lại tìm kiếm codebase và xóa phần Judge.me không còn sử dụng.
- [ ] Cập nhật tài liệu nội bộ về cách curate review mới trong Loox.

## Những điều cần lưu ý khi thực hiện

> Mục này để tôi làm thủ công, AI ko cần làm.

1. **Không uninstall Judge.me quá sớm.** CSV published reviews không chứa video và không chứa verified status trực tiếp. Giữ app cũ cho đến khi hoàn tất đối chiếu và xử lý dữ liệu đặc biệt.
2. **Không bật email automation của hai app cùng lúc.** Khách có thể nhận hai review requests cho cùng một order.
3. **Không bật hai nguồn rich snippets cùng lúc.** Judge.me và Loox cùng inject `aggregateRating` có thể tạo structured data trùng hoặc mâu thuẫn.
4. **Collector Reviews là social proof toàn catalog.** Heading và product attribution phải làm rõ review có thể thuộc sản phẩm khác; không được làm khách hiểu đó là review của product đang xem.
5. **Curated carousel của Loox là global.** Những review được `Add to Carousels` sẽ dùng chung cho các Loox carousel trên toàn site. Điều này phù hợp khi mọi PDP dùng cùng một bộ Collector Reviews, nhưng cần lưu ý nếu sau này homepage hoặc landing page muốn một bộ review khác.
6. **Cards Carousel thiên về visual reviews.** Text-only reviews không xuất hiện trong Cards/Gallery Carousel theo tài liệu Loox; dùng Review Widget hoặc Testimonial Carousel nếu cần trưng bày text-only content.
7. **Review có nhiều ảnh chỉ dùng cover trong carousel.** Phải chọn cover image tốt và kiểm tra crop trên mobile.
8. **Imported review không mặc nhiên giữ verified badge.** Chỉ hiển thị “Verified purchase” khi Loox xác nhận review đáp ứng quy tắc xác minh của họ.
9. **Rating theo product phải tách khỏi rating toàn store.** Không cộng review chéo sản phẩm vào rating dưới giá hoặc Product structured data.
10. **Theme Editor settings là một phần của migration.** Thay đổi app blocks/app embed có thể cập nhật `templates/product.json` và `config/settings_data.json`; kiểm tra diff để không ghi đè thay đổi khác của merchant.
11. **Không phụ thuộc sâu vào DOM nội bộ của Loox nếu không cần thiết.** Cách custom modal Judge.me hiện tại rất dễ hỏng khi app thay markup; ưu tiên setting chính thức và CSS scope ổn định.
12. **Kiểm tra điều kiện plan trước cutover.** Loox Beginner có giới hạn eligibility theo total orders; không giả định store sẽ được dùng miễn phí lâu dài nếu chưa xác nhận số order và plan trong Loox Admin.
13. **Giữ access token an toàn.** Nếu cần kiểm tra Shopify config qua folder `admin`, không in token vào terminal output, source code, log, screenshot hoặc tài liệu này.
14. **Mọi storefront copy phải bằng English.** Checklist có thể bằng tiếng Việt, nhưng headings, buttons, labels, empty states và notification trên website phải dùng English.

## Tài liệu chính thức tham khảo

- [Importing Reviews from Judge.me to Loox](https://help.loox.io/article/660-importing-reviews-from-judge-me-to-loox)
- [Loox Carousel Widgets](https://help.loox.io/article/607-loox-carousel-widgets)
- [Adding Loox Widgets to a Shopify 2.0 Theme](https://help.loox.io/article/533-integrating-loox-widgets-with-store-2-0-themes)
- [Loox Star Rating Widget](https://help.loox.io/article/649-the-loox-rating-widget)
- [Shopify Standard Metafields for Loox Reviews](https://help.loox.io/support/solutions/articles/501000353558-shopify-standard-metafields-for-loox-reviews)
- [How Loox Impacts SEO](https://help.loox.io/support/solutions/articles/501000162406-how-loox-impacts-seo)
- [Judge.me: Exporting Reviews](https://judge.me/help/en/articles/8236266-exporting-reviews)
