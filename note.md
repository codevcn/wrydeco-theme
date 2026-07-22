## Backup prompts

```text
Đảm bảo UI cuối cùng đáp ứng trên cả màn hình mobile.
Đảm bảo UI cuối cùng phải bám sát bản design.
Làm xong thì dùng playwright để check lại (playwright đã được cài đặt trong project này).


Đọc toàn bộ nội dung trong file nén tôi đính kèm để nắm bối cảnh và styling chủ đạo của app.



Ảnh đính kèm là bản design cho



Tôi sẽ nêu vấn đề với responsive trên màn hình điện thoại (ví dụ màn hình 360x670 px), bạn hãy dùng playwright để xem qua từng vấn đề rồi sửa lại:



ở trang chi tiết sản phẩm, tại sao khi vừa vào nó lại chọn ảnh thứ 2 làm ảnh lớn mà ko phải ảnh đầu? fix nó đi


tôi muốn nút "View Craftsmanship" khi nhấn vào sẽ random chạy vào 1 trong các route 

check file @Tiêu chí chấm điểm mức độ hoàn thành.txt - Notepad so với project hiện tại xem project có thiếu gì ko? bạn có thể hỏi lại tui nếu muốn, bạn có thể dùng playwright để check lại nếu cần (playwright đã được cài trong project này).



tôi cần 1 trang Care Guide, bạn hãy viết 1 bài blog về Care Guide, blog chia thành các mục 


<div class="description-root"></div>
```

## GID cho product category

Đây là danh sách chi tiết map (chuyển đổi) các Category name tôi đã đề xuất sang mã GID (Global ID) của
Shopify Standard Product Taxonomy để bạn cấu hình cho file CSV / API upload nhé:

### 1. Kệ sách đứng (Bookshelves / Bookcases)

Dành cho các product_type: bookshelf-modern, bookshelf-rustic

• Tên Category đầy đủ: Furniture > Shelving > Bookcases & Standing Shelves
• Shopify Taxonomy GID: gid://shopify/TaxonomyCategory/fr-19-1

### 2. Kệ treo tường (Floating Shelves)

Dành cho các product_type: floating-shelf-modern, floating-shelf-rustic, floating-shelf-boho

• Tên Category đầy đủ: Furniture > Shelving > Wall Shelves & Ledges
• Shopify Taxonomy GID: gid://shopify/TaxonomyCategory/fr-19-2

### 3. Bàn trà / Bàn cà phê (Coffee Tables)

Dành cho các product_type: coffee-table
• Tên Category đầy đủ: Furniture > Accent Tables > Coffee Tables
• Shopify Taxonomy GID: gid://shopify/TaxonomyCategory/fr-24-1-1

### 4. Tủ kệ lưu trữ đĩa than / Media Console

Dành cho các product_type: storage-cabinet, Vinyl Record Storage Cabinet

• Tên Category đầy đủ: Furniture > Cabinets & Storage > Media Storage Cabinets & Racks
• Shopify Taxonomy GID: gid://shopify/TaxonomyCategory/fr-4-10

### 5. Giường / Khung giường (Beds / Bed Frames)

Dành cho các product_type: bed-frame-with-headboard

• Tên Category đầy đủ: Furniture > Beds & Accessories > Beds & Bed Frames
• Shopify Taxonomy GID: gid://shopify/TaxonomyCategory/fr-2-2
──────
💡 Ghi chú khi sử dụng GID:
Nếu bạn dùng API GraphQL hoặc update trực tiếp qua tool json_to_shopify_csv.py, truyền trực tiếp chuỗi ID này
vào trường productCategory. Đối với file CSV truyền thống thông qua trang admin, bạn có thể truyền ID chuỗi
ngắn như fr-19-1 hoặc ghi chuỗi chữ Furniture > Shelving > Bookcases & Standing Shelves (Shopify sẽ tự nhận
dạng).

---

## GID cho product author info

Dưới đây là danh sách toàn bộ các entry của Meta Object "Author Info" (với type là product_author) trên hệ
thống store của bạn, kèm theo ID (GID) của từng đối tượng:

1. Lam Nguyen (Handle: lam-nguyen)
   • GID: gid://shopify/Metaobject/194643165241
2. Khoi Hoang (Handle: khoi-hoang)
   • GID: gid://shopify/Metaobject/194643198009
3. Tin Dang (Handle: alex-nguyen)
   • GID: gid://shopify/Metaobject/194643296313
4. Nhan Pham (Handle: nhan-pham)
   • GID: gid://shopify/Metaobject/195646947385
5. Nhien Le (Handle: nhien-le)
   • GID: gid://shopify/Metaobject/195647275065
6. Son Tran (Handle: son-tran)
   • GID: gid://shopify/Metaobject/195647701049

## Sản phẩm có checkmark trong biến thể

B0H6BRT2WD
