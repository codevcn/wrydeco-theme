# Danh sách sản phẩm có Variant Option Value được chuẩn hóa thành "Custom"

Tài liệu này ghi nhận quá trình chuẩn hóa toàn bộ option value của **30 sản phẩm** trong store **Wrydeco** (`wrydeco.myshopify.com`) từ định dạng `custom {other text}` (ví dụ: *Custom color*, *Custom size*, *Custom large size*, ...) thành **`Custom`**.

## 1. Tổng quan

- **Tổng số sản phẩm trong store:** 75 sản phẩm
- **Số sản phẩm được chỉnh sửa & chuẩn hóa option value:** **30** sản phẩm
- **Trạng thái chuẩn hóa:** Đã cập nhật thành công 100% trên store thông qua Shopify Admin API (các option value cũ như *Custom color*, *Custom size*, *Custom Large Size*, *CUSTOM LARGER SIZE*, *Custom Larger or Special Size*, *Yes, Custom Name/Text* đều đã được đổi thành **`Custom`**).

---

## 2. Bảng tổng hợp sản phẩm

| STT | ID sản phẩm | Handle | Tên sản phẩm | Option | Option Value (Đã chuẩn hóa) | Giá trị cũ trước khi sửa |
|:---:|:---|:---|:---|:---|:---|:---|
| 1 | 8355493773369 | `bird-nest-wood-platform-bed-branch-canopy-headboard-v2` | **Bird Nest Wood Bed Frame with Branch Canopy Headboard** | **Choose Size** | `Custom` | `CUSTOM LARGER SIZE` |
| 2 | 8355782295609 | `canyon-spirit-arbor-handcrafted-wood-tree-branch-shelf` | **Canyon Spirit Arbor Handcrafted Wood Tree Branch Shelf** | **Select color**<br>**Select size** | `Custom`<br>`Custom` | `Custom color`<br>`Custom size` |
| 3 | 8355804577849 | `custom-handcrafted-natural-wood-corner-tree-bookshelf` | **Custom Handcrafted Natural Wood Corner Tree Bookshelf** | **Select size** | `Custom` | `Custom Size` |
| 4 | 8355782197305 | `handcrafted-4-tier-wood-tree-branch-bookshelf-sequoia` | **Handcrafted 4-Tier Natural Wood Tree Branch Bookshelf** | **Select color**<br>**Select size** | `Custom`<br>`Custom` | `Custom color`<br>`Custom size` |
| 5 | 8355782230073 | `handcrafted-5-tier-wood-tree-branch-floating-bookshelf` | **Handcrafted 5-Tier Wood Tree Branch Floating Bookshelf** | **Select color**<br>**Select size** | `Custom`<br>`Custom` | `Custom color`<br>`Custom size` |
| 6 | 8355804545081 | `live-edge-tree-branch-bookshelf-with-bench-11-tier` | **Handcrafted Live Edge Tree Branch Bookshelf with Bench** | **Select color**<br>**Select size** | `Custom`<br>`Custom` | `Custom color`<br>`Custom size` |
| 7 | 8355804512313 | `natural-wood-corner-tree-branch-shelf-sun-climbers-ladder` | **Handcrafted Natural Wood Corner Tree Branch Bookshelf** | **Select color**<br>**Select size** | `Custom`<br>`Custom` | `Custom color`<br>`Custom Size` |
| 8 | 8355804676153 | `natural-wood-corner-tree-branch-bookshelf-custom-design` | **Handcrafted Natural Wood Corner Tree Branch Bookshelf** | **Select color**<br>**Select size** | `Custom`<br>`Custom` | `Custom color`<br>`Custom Size` |
| 9 | 8355782328377 | `rustic-wood-tree-branch-floating-bookshelf-4-tier-decor` | **Handcrafted Rustic Wood Tree Branch Floating Bookshelf** | **Select color**<br>**Select size** | `Custom`<br>`Custom` | `Custom color`<br>`Custom size` |
| 10 | 8355493314617 | `handmade-rustic-solid-wood-platform-bed-with-headboard` | **Handmade Rustic Solid Wood Platform Bed with Branch Headboard** | **Size** | `Custom` | `Custom Larger or Special Size` |
| 11 | 8355491151929 | `handmade-wooden-tree-bookshelf-kids-reading-room-storage` | **Handmade Wooden Tree Bookshelf for Kids Reading Spaces** | **Choose Size** | `Custom` | `Custom Large Size` |
| 12 | 8355492233273 | `modern-curved-sculptural-wood-bookcase-living-room` | **Modern Curved Sculptural Wood Bookcase Living Room** | **Choose Size (W X H X D)** | `Custom` | `Custom Larger Size` |
| 13 | 8355492397113 | `modern-sculptural-curved-solid-wood-bookshelf-decor` | **Modern Sculptural Curved Solid Wood Bookshelf Decor** | **Choose Size (W X H X D)** | `Custom` | `Custom Larger Size` |
| 14 | 8355491545145 | `mushroom-tree-bookshelf-tiered-wooden-display-shelves` | **Mushroom Tree Bookshelf with Tiered Wooden Display Shelves** | **Choose Size** | `Custom` | `Custom Large Size` |
| 15 | 8355491184697 | `nature-inspired-display-wooden-mushroom-tree-bookshelf-opt3` | **Nature Inspired Display Wooden Mushroom Tree Bookshelf** | **Choose Size** | `Custom` | `Custom Large Size` |
| 16 | 8355491381305 | `nature-inspired-mushroom-tree-bookshelf-fantasy-display-opt2` | **Nature Inspired Mushroom Tree Bookshelf Fantasy Display** | **Choose Size** | `Custom` | `Custom Large Size` |
| 17 | 8355493412921 | `solid-wood-platform-bed-with-tree-branch-headboard` | **Rustic Solid Wood Platform Bed with Branch Headboard** | **Size** | `Custom` | `Custom Larger or Special Size` |
| 18 | 8355493576761 | `solid-wood-platform-bed-branch-headboard` | **Rustic Solid Wood Platform Bed with Branch Headboard** | **Size** | `Custom` | `Custom Larger or Special Size` |
| 19 | 8355493183545 | `rustic-solid-wood-platform-bed-tree-branch-headboard` | **Rustic Solid Wood Platform Bed with Tree Branch Headboard** | **Size** | `Custom` | `Custom Larger or Special Size` |
| 20 | 8355492593721 | `rustic-solid-wood-tree-branch-bookshelf-vintage-decor` | **Rustic Solid Wood Tree Branch Bookshelf Vintage Decor** | **Choose Size** | `Custom` | `Custom Larger Size` |
| 21 | 8355493511225 | `rustic-solid-wood-platform-bed-tree-branch-headboard-v2` | **Rustic Wood Platform Bed with Tree Branch Headboard** | **Size** | `Custom` | `Custom Larger or Special Size` |
| 22 | 8355492134969 | `sculptural-solid-wood-curved-bookshelf-display-decor` | **Sculptural Solid Wood Curved Bookshelf Display Decor** | **Choose Size (W X H X D)** | `Custom` | `Custom Larger Size` |
| 23 | 8355490267193 | `solid-wood-arched-floating-two-tier-wall-shelf-option-1` | **Solid Wood Arched Floating Two Tier Wall Shelf Option 1** | **Would You Like To HAND-CARVE Text/Art To Custom Your Product?** | `Custom` | `Yes, Custom Name/Text` |
| 24 | 8355492331577 | `solid-wood-sculptural-curved-bookshelf-modern-storage` | **Solid Wood Sculptural Curved Bookshelf Modern Storage** | **Choose Size (W X H X D)** | `Custom` | `Custom Larger Size` |
| 25 | 8355493806137 | `solid-wood-tree-bird-nest-platform-bed-frame-canopy` | **Solid Wood Tree Bird Nest Platform Bed Frame with Canopy** | **Size** | `Custom` | `CUSTOM LARGER SIZE` |
| 26 | 8355492495417 | `solid-wood-tree-branch-wall-mounted-display-bookcase` | **Solid Wood Tree Branch Wall-Mounted Display Bookcase** | **Choose Size** | `Custom` | `Custom Larger Size` |
| 27 | 8355782262841 | `the-mesa-drift-canopy-handcrafted-wood-tree-branch-shelf` | **The Mesa Drift Canopy Handcrafted Wood Tree Branch Shelf** | **Select color**<br>**Select size** | `Custom`<br>`Custom` | `Custom color`<br>`Custom size` |
| 28 | 8355489841209 | `tree-bird-nest-wood-platform-canopy-bed-frame-2` | **Tree Bird Nest Wood Platform Canopy Bed Frame** | **Choose Size** | `Custom` | `CUSTOM LARGER SIZE` |
| 29 | 8355491283001 | `wooden-mushroom-tree-bookshelf-nature-inspired-display-opt4` | **Wooden Mushroom Tree Bookshelf Nature Inspired Display** | **Choose Size** | `Custom` | `Custom Large Size` |
| 30 | 8355491479609 | `wooden-mushroom-tree-bookshelf-tiered-display-shelves` | **Wooden Mushroom Tree Bookshelf with Tiered Display Shelves** | **Choose Size** | `Custom` | `Custom Large Size` |

---

## 3. Danh sách chi tiết

### 1. Bird Nest Wood Bed Frame with Branch Canopy Headboard

- **Product ID:** `8355493773369`
- **Handle:** `bird-nest-wood-platform-bed-branch-canopy-headboard-v2`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `CUSTOM LARGER SIZE`)*

### 2. Canyon Spirit Arbor Handcrafted Wood Tree Branch Shelf

- **Product ID:** `8355782295609`
- **Handle:** `canyon-spirit-arbor-handcrafted-wood-tree-branch-shelf`
- **Option Values:**
  - **Select color**: **`Custom`** *(trước đây: `Custom color`)*
  - **Select size**: **`Custom`** *(trước đây: `Custom size`)*

### 3. Custom Handcrafted Natural Wood Corner Tree Bookshelf

- **Product ID:** `8355804577849`
- **Handle:** `custom-handcrafted-natural-wood-corner-tree-bookshelf`
- **Option Values:**
  - **Select size**: **`Custom`** *(trước đây: `Custom Size`)*

### 4. Handcrafted 4-Tier Natural Wood Tree Branch Bookshelf

- **Product ID:** `8355782197305`
- **Handle:** `handcrafted-4-tier-wood-tree-branch-bookshelf-sequoia`
- **Option Values:**
  - **Select color**: **`Custom`** *(trước đây: `Custom color`)*
  - **Select size**: **`Custom`** *(trước đây: `Custom size`)*

### 5. Handcrafted 5-Tier Wood Tree Branch Floating Bookshelf

- **Product ID:** `8355782230073`
- **Handle:** `handcrafted-5-tier-wood-tree-branch-floating-bookshelf`
- **Option Values:**
  - **Select color**: **`Custom`** *(trước đây: `Custom color`)*
  - **Select size**: **`Custom`** *(trước đây: `Custom size`)*

### 6. Handcrafted Live Edge Tree Branch Bookshelf with Bench

- **Product ID:** `8355804545081`
- **Handle:** `live-edge-tree-branch-bookshelf-with-bench-11-tier`
- **Option Values:**
  - **Select color**: **`Custom`** *(trước đây: `Custom color`)*
  - **Select size**: **`Custom`** *(trước đây: `Custom size`)*

### 7. Handcrafted Natural Wood Corner Tree Branch Bookshelf

- **Product ID:** `8355804512313`
- **Handle:** `natural-wood-corner-tree-branch-shelf-sun-climbers-ladder`
- **Option Values:**
  - **Select color**: **`Custom`** *(trước đây: `Custom color`)*
  - **Select size**: **`Custom`** *(trước đây: `Custom Size`)*

### 8. Handcrafted Natural Wood Corner Tree Branch Bookshelf

- **Product ID:** `8355804676153`
- **Handle:** `natural-wood-corner-tree-branch-bookshelf-custom-design`
- **Option Values:**
  - **Select color**: **`Custom`** *(trước đây: `Custom color`)*
  - **Select size**: **`Custom`** *(trước đây: `Custom Size`)*

### 9. Handcrafted Rustic Wood Tree Branch Floating Bookshelf

- **Product ID:** `8355782328377`
- **Handle:** `rustic-wood-tree-branch-floating-bookshelf-4-tier-decor`
- **Option Values:**
  - **Select color**: **`Custom`** *(trước đây: `Custom color`)*
  - **Select size**: **`Custom`** *(trước đây: `Custom size`)*

### 10. Handmade Rustic Solid Wood Platform Bed with Branch Headboard

- **Product ID:** `8355493314617`
- **Handle:** `handmade-rustic-solid-wood-platform-bed-with-headboard`
- **Option Values:**
  - **Size**: **`Custom`** *(trước đây: `Custom Larger or Special Size`)*

### 11. Handmade Wooden Tree Bookshelf for Kids Reading Spaces

- **Product ID:** `8355491151929`
- **Handle:** `handmade-wooden-tree-bookshelf-kids-reading-room-storage`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `Custom Large Size`)*

### 12. Modern Curved Sculptural Wood Bookcase Living Room

- **Product ID:** `8355492233273`
- **Handle:** `modern-curved-sculptural-wood-bookcase-living-room`
- **Option Values:**
  - **Choose Size (W X H X D)**: **`Custom`** *(trước đây: `Custom Larger Size`)*

### 13. Modern Sculptural Curved Solid Wood Bookshelf Decor

- **Product ID:** `8355492397113`
- **Handle:** `modern-sculptural-curved-solid-wood-bookshelf-decor`
- **Option Values:**
  - **Choose Size (W X H X D)**: **`Custom`** *(trước đây: `Custom Larger Size`)*

### 14. Mushroom Tree Bookshelf with Tiered Wooden Display Shelves

- **Product ID:** `8355491545145`
- **Handle:** `mushroom-tree-bookshelf-tiered-wooden-display-shelves`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `Custom Large Size`)*

### 15. Nature Inspired Display Wooden Mushroom Tree Bookshelf

- **Product ID:** `8355491184697`
- **Handle:** `nature-inspired-display-wooden-mushroom-tree-bookshelf-opt3`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `Custom Large Size`)*

### 16. Nature Inspired Mushroom Tree Bookshelf Fantasy Display

- **Product ID:** `8355491381305`
- **Handle:** `nature-inspired-mushroom-tree-bookshelf-fantasy-display-opt2`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `Custom Large Size`)*

### 17. Rustic Solid Wood Platform Bed with Branch Headboard

- **Product ID:** `8355493412921`
- **Handle:** `solid-wood-platform-bed-with-tree-branch-headboard`
- **Option Values:**
  - **Size**: **`Custom`** *(trước đây: `Custom Larger or Special Size`)*

### 18. Rustic Solid Wood Platform Bed with Branch Headboard

- **Product ID:** `8355493576761`
- **Handle:** `solid-wood-platform-bed-branch-headboard`
- **Option Values:**
  - **Size**: **`Custom`** *(trước đây: `Custom Larger or Special Size`)*

### 19. Rustic Solid Wood Platform Bed with Tree Branch Headboard

- **Product ID:** `8355493183545`
- **Handle:** `rustic-solid-wood-platform-bed-tree-branch-headboard`
- **Option Values:**
  - **Size**: **`Custom`** *(trước đây: `Custom Larger or Special Size`)*

### 20. Rustic Solid Wood Tree Branch Bookshelf Vintage Decor

- **Product ID:** `8355492593721`
- **Handle:** `rustic-solid-wood-tree-branch-bookshelf-vintage-decor`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `Custom Larger Size`)*

### 21. Rustic Wood Platform Bed with Tree Branch Headboard

- **Product ID:** `8355493511225`
- **Handle:** `rustic-solid-wood-platform-bed-tree-branch-headboard-v2`
- **Option Values:**
  - **Size**: **`Custom`** *(trước đây: `Custom Larger or Special Size`)*

### 22. Sculptural Solid Wood Curved Bookshelf Display Decor

- **Product ID:** `8355492134969`
- **Handle:** `sculptural-solid-wood-curved-bookshelf-display-decor`
- **Option Values:**
  - **Choose Size (W X H X D)**: **`Custom`** *(trước đây: `Custom Larger Size`)*

### 23. Solid Wood Arched Floating Two Tier Wall Shelf Option 1

- **Product ID:** `8355490267193`
- **Handle:** `solid-wood-arched-floating-two-tier-wall-shelf-option-1`
- **Option Values:**
  - **Would You Like To HAND-CARVE Text/Art To Custom Your Product?**: **`Custom`** *(trước đây: `Yes, Custom Name/Text`)*

### 24. Solid Wood Sculptural Curved Bookshelf Modern Storage

- **Product ID:** `8355492331577`
- **Handle:** `solid-wood-sculptural-curved-bookshelf-modern-storage`
- **Option Values:**
  - **Choose Size (W X H X D)**: **`Custom`** *(trước đây: `Custom Larger Size`)*

### 25. Solid Wood Tree Bird Nest Platform Bed Frame with Canopy

- **Product ID:** `8355493806137`
- **Handle:** `solid-wood-tree-bird-nest-platform-bed-frame-canopy`
- **Option Values:**
  - **Size**: **`Custom`** *(trước đây: `CUSTOM LARGER SIZE`)*

### 26. Solid Wood Tree Branch Wall-Mounted Display Bookcase

- **Product ID:** `8355492495417`
- **Handle:** `solid-wood-tree-branch-wall-mounted-display-bookcase`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `Custom Larger Size`)*

### 27. The Mesa Drift Canopy Handcrafted Wood Tree Branch Shelf

- **Product ID:** `8355782262841`
- **Handle:** `the-mesa-drift-canopy-handcrafted-wood-tree-branch-shelf`
- **Option Values:**
  - **Select color**: **`Custom`** *(trước đây: `Custom color`)*
  - **Select size**: **`Custom`** *(trước đây: `Custom size`)*

### 28. Tree Bird Nest Wood Platform Canopy Bed Frame

- **Product ID:** `8355489841209`
- **Handle:** `tree-bird-nest-wood-platform-canopy-bed-frame-2`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `CUSTOM LARGER SIZE`)*

### 29. Wooden Mushroom Tree Bookshelf Nature Inspired Display

- **Product ID:** `8355491283001`
- **Handle:** `wooden-mushroom-tree-bookshelf-nature-inspired-display-opt4`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `Custom Large Size`)*

### 30. Wooden Mushroom Tree Bookshelf with Tiered Display Shelves

- **Product ID:** `8355491479609`
- **Handle:** `wooden-mushroom-tree-bookshelf-tiered-display-shelves`
- **Option Values:**
  - **Choose Size**: **`Custom`** *(trước đây: `Custom Large Size`)*

---

## 4. Ghi chú bổ sung: Các sản phẩm có option value nguyên bản là "Custom"

Ngoài 30 sản phẩm đã được chỉnh sửa chuẩn hóa ở trên, trong store còn có **60 sản phẩm** có sẵn các option value chỉ là chữ **`Custom`** đơn lẻ từ trước (thường ở option `Wood Finish` hoặc `Choose Size`). Toàn bộ các giá trị này vẫn được duy trì nguyên vẹn và đồng bộ với hệ thống.
