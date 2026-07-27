# Quy trình làm mới chỉ mục (Re-indexing) trên Google Search cho website Wrydeco

Khi website Shopify từng ở chế độ bảo vệ bằng mật khẩu (Password Page / Storefront Password) hoặc "Coming Soon", Googlebot có thể đã cào (crawl) và lưu cache nội dung của trang mật khẩu. Để Google nhanh chóng cập nhật chỉ mục mới với toàn bộ nội dung SEO đã được tối ưu (36 Collection, Products, Pages...), cần thực hiện tuần tự các bước dưới đây:

---

## 1. Gỡ bỏ chế độ bảo vệ mật khẩu trên Shopify Admin
- [ ] **Kiểm tra và tắt Storefront Password:**
  - Truy cập Shopify Admin -> **Online Store** -> **Preferences** -> Cuộn xuống mục **Password protection**.
  - Bỏ chọn (uncheck) ô **"Restrict access to visitors with the password"**.
  - Nhấn **Save** để mở công khai (publish) website cho người dùng và bot tìm kiếm.
- [ ] **Kiểm tra dưới góc độ ẩn danh (Incognito Mode):**
  - Mở trình duyệt ẩn danh, truy cập domain chính của cửa hàng (ví dụ: `https://wrydeco.com` hoặc domain `.myshopify.com` đang dùng) để đảm bảo không còn bị chuyển hướng đến trang `/password`.
  - Đảm bảo mã phản hồi HTTP của trang chủ và các trang con là **200 OK** (không phải 302/301 sang `/password` hay 403 Forbidden).

---

## 2. Kiểm tra file `robots.txt` và Thẻ Meta Robots
- [ ] **Xác minh không bị chặn trong `robots.txt`:**
  - Mở trình duyệt truy cập `https://[your-domain]/robots.txt`.
  - Đảm bảo Shopify không có chỉ thị `Disallow: /` đối với `User-agent: *` hay `User-agent: Googlebot`. *(Mặc định Shopify tự động tạo file `robots.txt` chuẩn; khi tắt trang mật khẩu, bot sẽ được phép truy cập).*
- [ ] **Kiểm tra thẻ `<meta name="robots">` trong mã nguồn:**
  - Xem nguồn trang (View Page Source - `Ctrl + U`) tại Trang chủ (`/`) và các Collection (`/collections/...`).
  - Đảm bảo KHÔNG có thẻ `<meta name="robots" content="noindex, nofollow">`. Thẻ đúng phải là `index, follow` (hoặc Shopify tự động loại bỏ thẻ `noindex` khi website chuyển sang trạng thái công khai).

---

## 3. Cấu hình và khai báo trên Google Search Console (GSC)
- [ ] **Thêm và xác minh tài khoản Google Search Console:**
  - Nếu chưa có, truy cập [Google Search Console](https://search.google.com/search-console) và thêm tài sản (property) cho domain của Wrydeco.
  - Xác minh quyền sở hữu thông qua bản ghi TXT trong DNS của tên miền hoặc thẻ HTML tag (dán vào phần `<head>` trong file `layout/theme.liquid`).
- [ ] **Gửi sơ đồ trang web (Sitemap.xml):**
  - Trong GSC, chọn mục **Sitemaps** (Sơ đồ trang web) ở menu bên trái.
  - Nhập đường dẫn sitemap mặc định của Shopify: `sitemap.xml` *(Hệ thống Shopify tự động cập nhật sitemap động chứa tất cả products, collections, blogs, pages)*.
  - Nhấn **Submit** (Gửi) và kiểm tra trạng thái hiển thị **"Success"** (Thành công).
- [ ] **Yêu cầu lập chỉ mục lại (Request Indexing) cho các URL quan trọng:**
  - Chọn công cụ **URL Inspection** (Kiểm tra URL) ở menu trên cùng của GSC.
  - Dán URL Trang chủ -> Nhấn Enter -> Nhấn nút **Request Indexing** (Yêu cầu lập chỉ mục) để ưu tiên Googlebot cào lại ngay lập tức.
  - Thực hiện lặp lại bước này cho các trang quan trọng nhất (các Collection Top Best Sellers, New Arrivals, Signature Pieces...).

---

## 4. Xử lý Cache cũ và bộ nhớ đệm (Removals & Clear Cache)
- [ ] **Sử dụng công cụ Xóa bỏ URL cũ (nếu snippet trên Google hiển thị sai lệch trầm trọng):**
  - Trong GSC, chọn mục **Removals** (Xóa bỏ) -> Chọn tab **Clear Cached URL** (Xóa URL đã lưu trong bộ nhớ đệm).
  - Yêu cầu xóa cache của trang chủ và các URL đang bị hiển thị nội dung "Password Page / Coming Soon" trong kết quả tìm kiếm.
  - *⚠️ Lưu ý cực kỳ quan trọng: Chỉ chọn xóa bộ nhớ đệm (Clear cache only), KHÔNG chọn xóa URL khỏi chỉ mục tìm kiếm (Remove URL temporarily) vì sẽ làm web bị biến mất tạm thời khỏi Google.*
- [ ] **Kiểm tra phiên bản Cache hiện tại trên Google Search:**
  - Tìm kiếm trên Google với cú pháp: `cache:wrydeco.com` (hoặc tìm cú pháp `site:wrydeco.com` rồi bấm vào biểu tượng 3 chấm bên cạnh kết quả -> chọn **Cached**).
  - Theo dõi mốc thời gian để nhận biết thời điểm Googlebot chụp lại bản snapshot mới nhất của trang web sau khi mở mật khẩu.

---

## 5. Tạo tín hiệu thu hút Googlebot cào lại trang (External & Internal Signals)
- [ ] **Tối ưu liên kết nội bộ (Internal Linking):**
  - Kiểm tra các menu điều hướng (Header Navigation, Footer Menu) đã gắn đầy đủ link tới các Collection quan trọng vừa tối ưu SEO.
  - *Hệ thống mô tả HTML mới của 36 Collection đã được chúng ta tích hợp sẵn các internal links, giúp Googlebot dễ dàng đi theo các đường dẫn này để cào hết toàn bộ store.*
- [ ] **Tạo tín hiệu từ bên ngoài (Social Signals & External Links):**
  - Chia sẻ link trang chủ và các Collection mới lên các trang mạng xã hội của thương hiệu (Facebook, Instagram, Pinterest, Reddit...).
  - Các tín hiệu truy cập (traffic) từ social media và liên kết ngoài sẽ kích thích Googlebot truy cập và cào trang với tần suất dày đặc hơn.

---

## 6. Theo dõi và đo lường kết quả (Monitoring)
- [ ] **Kiểm tra tiến độ thu thập dữ liệu trong GSC:**
  - Vào GSC -> **Pages** (Trang) -> Kiểm tra báo cáo **Indexing** để xem số lượng trang chuyển từ trạng thái "Discovered - currently not indexed" sang "Indexed" (Đã lập chỉ mục).
- [ ] **Kiểm tra thực tế trên Google Search:**
  - Định kỳ (2 - 3 ngày/lần) gõ cú pháp `site:wrydeco.com` trên thanh tìm kiếm của Google để kiểm tra xem Tiêu đề (SEO Page Title) và Mô tả (Meta Description) của 36 Collection và sản phẩm đã được làm mới theo đúng các nội dung tối ưu hay chưa.

---
> **💡 Mẹo nhỏ:** Quá trình Googlebot cào lại và làm mới toàn bộ bộ nhớ đệm (cache) trên kết quả tìm kiếm thường mất từ **24 giờ đến 7 ngày** tùy thuộc vào độ uy tín của tên miền (Domain Authority) và ngân sách thu thập dữ liệu (Crawl Budget) mà Google dành cho website.
