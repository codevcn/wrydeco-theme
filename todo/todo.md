## 2. Thiếu Shopify Category

`Shopify Category` là phân loại chuẩn của Shopify, khác với:

- `Collection`: nhóm merchandising như Signature Pieces hoặc New Arrivals.
- `Product type`: nhãn nội bộ tùy chỉnh của cửa hàng.
- `Tags`: dữ liệu hỗ trợ quản trị hoặc filter.

Mỗi sản phẩm chỉ có một Shopify Category và nên chọn category cụ thể nhất. Category không nhất thiết hiển thị trực tiếp trên storefront, nhưng được Shopify sử dụng để:

- Đồng bộ chính xác hơn với Google, Facebook và các sales channel.
- Mở các category metafield/product attribute chuẩn.
- Hỗ trợ filter và automatic collection.
- Cải thiện phân loại sản phẩm và tính thuế.

Shopify khuyến nghị tất cả sản phẩm đều được gán category; sản phẩm chưa gán sẽ ở trạng thái `Uncategorized`. [Shopify Standard Product Taxonomy](https://help.shopify.com/en/manual/products/details/product-category)

## Hướng sửa đề xuất

### Bước 1: Lập bảng kiểm kê catalog

Với mỗi sản phẩm active, ghi lại:

- Handle và SKU.
- Thiết kế/hình dáng.
- Công năng.
- Kích thước.
- Loại gỗ và finish.
- Giá.
- Category hiện tại.
- Review và URL đang có traffic, nếu có.

Sau đó gom chúng thành các “design family” để xác định sản phẩm nào thực sự trùng.

### Bước 2: Xử lý theo ba trường hợp

**Cùng thiết kế, chỉ khác kích thước hoặc finish**

Gộp thành một product và chuyển kích thước/finish thành variant. Việc này giúp tập trung review, SEO và lượt bán vào một PDP.

**Hình dáng gần giống nhưng có khác biệt đáng kể**

Giữ riêng, nhưng phải phân biệt rõ:

- Tên sản phẩm.
- Ảnh đại diện.
- Mô tả và câu chuyện thiết kế.
- Công năng hoặc không gian sử dụng.
- Kích thước và đặc điểm hình dáng.

Nên áp dụng cấu trúc tên nhất quán, chẳng hạn:

`[Design name] + [Product form] + [Distinctive feature]`

Ví dụ: `Arbor Floating Wall Shelf — Natural Branch Form`.

Không nên đưa SKU vào tiêu đề hiển thị cho khách.

**Sản phẩm bị import hoặc tạo trùng hoàn toàn**

Giữ lại URL có dữ liệu tốt nhất, chuyển SKU/variant cần thiết sang đó, rồi tạo redirect 301 từ URL cũ. Không nên chỉ xóa sản phẩm cũ vì có thể làm mất backlink và tạo lỗi 404.

### Bước 3: Gán Shopify Category

Các category phù hợp với catalog hiện tại có thể là:

- Kệ treo tường: `Furniture > Shelving > Wall Shelves & Ledges`
- Kệ đứng/bookcase: `Furniture > Shelving > Bookcases & Standing Shelves`
- Category cụ thể hơn như `Floating Wall Shelves & Ledges` có thể được dùng nếu Shopify Admin hiện cung cấp lựa chọn đó.

Danh mục hiện hành có thể đối chiếu tại [Shopify Taxonomy Explorer](https://shopify.github.io/product-taxonomy/).

Thực hiện trong Shopify Admin:

1. Vào `Products`.
2. Chọn các sản phẩm cùng nhóm.
3. Chọn `Bulk edit`.
4. Thêm cột `Product category`.
5. Gán category cụ thể nhất và lưu lại.

Không nên gán tất cả sản phẩm chung chung vào `Furniture`; cần chọn sâu đến `Wall Shelves`, `Bookcases`, `Nightstands`… tùy sản phẩm.

## Thứ tự ưu tiên phù hợp

Mình đề xuất thực hiện:

1. Gán Category cho toàn bộ sản phẩm active.
2. Loại các bản trùng hoàn toàn.
3. Gộp các sản phẩm chỉ khác finish/kích thước thành variants.
4. Viết lại tên và nội dung cho các sản phẩm tương tự nhưng cần giữ riêng.
5. Kiểm tra redirect, review, filter và collection sau khi gộp.

Đây chủ yếu là công việc dữ liệu trong Shopify Admin, chưa cần sửa Liquid. Theme chỉ cần chỉnh tiếp nếu sau đó muốn dùng category metafield làm bộ lọc storefront.
