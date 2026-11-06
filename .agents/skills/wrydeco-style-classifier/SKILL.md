---
name: wrydeco-style-classifier
description: Quy trình phân tích thị giác AI kết hợp dữ liệu catalog để phân loại sản phẩm WRYDECO vào 4 interior styles chuẩn (Rustic vs Japandi, Mid-Century, Organic Modern) dựa trên hình thái cành thô nhọn vs bo tròn uốn lượn.
---

# WRYDECO Interior Style Classifier

## 1. Mục tiêu
Skill này dùng để chuẩn hóa và phân loại toàn bộ sản phẩm của WRYDECO vào **4 phong cách nội thất chuẩn**:
1. **`Rustic`**
2. **`Japandi`**
3. **`Mid-Century`**
4. **`Organic Modern`**

Theo đúng quy chuẩn thiết kế đã được Leader phê duyệt:
- **Nhóm 1 (Rustic):** Các sản phẩm dạng cành cây tự nhiên, đường nét thô mộc, cành nhọn/gồ ghề kiểu driftwood/live-edge xù xì $\rightarrow$ gán duy nhất **`Rustic`**.
- **Nhóm 2 (Còn lại):** Các sản phẩm có đường nét được bo tròn, uốn lượn mềm mại (organic curves / fluid waves), bề mặt láng mịn, tối giản thanh lịch $\rightarrow$ gán đồng thời vào cả 3 styles: **`Japandi`**, **`Mid-Century`**, **`Organic Modern`**.

---

## 2. Tiêu chí Phân loại Thị giác (Visual Criteria)

### A. Tiêu chuẩn nhận diện RUSTIC (Chỉ có dạng cành và ngọn nhọn):
* **Tuyệt đối không dựa vào chữ `"Rustic"` trong Title/Handle** (vì rất nhiều kệ đầu cành cụt, giường tổ chim, kệ rượu, kệ TV có chữ `"Rustic"` trong tên nhưng không thuộc hình thái Rustic).
* **Hình thái bắt buộc trên ảnh sản phẩm:** Ảnh sản phẩm **chỉ có dạng cành cây tự nhiên gồ ghề và các nhánh/ngọn nhọn vươn ra** (`dạng cành và ngọn nhọn`).
* **Mẫu đối chiếu chuẩn từ User & Leader:**
  - *Handcrafted Rustic Wood Tree Branch Floating Bookshelf* (`rustic-wood-tree-branch-floating-bookshelf-4-tier-decor`)
  - *Rustic Driftwood Solid Wood Floating Shelf Wall Decor* (`rustic-driftwood-solid-wood-floating-shelf-wall-decor`)
  - Các mẫu kệ cành cây đâm nhánh tự do với các đầu cành/nhánh vuốt nhọn tự nhiên.

### B. Tiêu chuẩn nhận diện CÒN LẠI (Japandi + Mid-Century + Organic Modern):
* Tất cả các sản phẩm không thuộc nhóm "chỉ có dạng cành và ngọn nhọn" nêu trên đều phân vào 3 dòng: `Japandi; Mid-Century; Organic Modern`.
* **Bao gồm cả các trường hợp loại trừ khỏi Rustic:**
  - *Large Wood Tree-Shaped Bookcase Rustic Branch Shelf* (`large-wood-tree-shaped-bookcase-rustic-branch-shelf`) và *Solid Wood Tree Branch Wall-Mounted Display Bookcase* (kệ hình cây nhưng thân/đầu cành cắt bằng, cụt hoặc bo tròn, không có nhánh ngọn nhọn).
  - *Handcrafted Live Edge Tree Branch Bookshelf with Bench* (kệ sách kèm băng ghế, các cạnh bo tròn).
  - *Bird Nest Wood Bed Frame with Branch Canopy Headboard* (giường đan vòm tổ chim tròn) và toàn bộ giường ngủ, kệ TV (*Rustic Live Edge Wood Floating Tree Branch TV Stand*), kệ rượu (*Rustic Wine Rack for Kitchen Island*), bàn trà, bàn console, ghế thay giày, đèn, gương, vanity.

---

## 3. Cấu trúc Thực thi

1. **Tải ảnh độ phân giải cao:**
   - Script `scripts/download_images.py` đọc file catalog CSV (`temp/fix-room/products_export_1.csv`), lọc lấy URL ảnh đại diện gốc (Full Resolution, loại bỏ các query parameters như `&width=...`).
   - Lưu trữ tại thư mục: `temp/fix-room/style-images/{handle}.jpg`.

2. **Phân tích Thị giác AI (Vision Pipeline):**
   - Script `scripts/classify_styles.py` duyệt từng sản phẩm và nạp ảnh tương ứng.
   - Kết hợp phân tích hình thái ảnh cục bộ cùng Title, Type, Category và tags sản phẩm.
   - Đánh giá chỉ số tin cậy (`Confidence_Score`) và đánh dấu `Flag_Review = YES` cho các trường hợp lai (hybrid).

3. **Xuất Báo cáo CSV:**
   - Lưu tại: `temp/fix-room/product_style_mapping.csv`.
