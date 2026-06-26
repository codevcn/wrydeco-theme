# Ashdeco home mobile layout audit

- URL: https://ashdeco.com/
- Thiet bi/viewport: mobile, 390 x 844 px
- Cach audit: Playwright MCP, da cuon het trang de kich hoat lazy-load, sau do trich xuat DOM va doi chieu bang snapshot mobile.
- Ghi chu: mot so carousel/list ngang co item nam ngoai viewport ngang, nhung van nam trong DOM va duoc liet ke theo thu tu DOM/mobile.

## Thu tu layout tu tren xuong

### 0. Announcement bar va header

- Announcement/promo bar o tren cung. Noi dung co the rotate; lan audit thay `FREE SHIPPING ON ALL ORDERS`.
- Header mobile ben duoi gom nut search, logo Ashdeco o giua, cart va hamburger menu ben phai.
- Anh trong header: logo Ashdeco, icon UI. Khong tinh la anh noi dung cua homepage section.

### 1. Top promo image slider

- Section dau tien trong `main`.
- Layout: slider hinh ngang full-width mobile, ti le thap, co pagination dots.
- Text noi dung: khong co heading hien thi trong section.

Anh trong section:

1. `banner.jpg`  
   `https://ashdeco.com/cdn/shop/files/banner.jpg?v=1782465053&width=400`
2. `banner1.jpg`  
   `https://ashdeco.com/cdn/shop/files/banner1.jpg?v=1782465056&width=400`

### 2. Hero banner - Father's Day Gift Ideas

- Layout: card/hero doc, anh lon o tren, overlay copy ve collection, ben duoi la CTA `Go shopping` va dong thong tin store.
- Heading: `Father's Day Gift Ideas`
- CTA/link chinh: `/collections/father-day`, `/collections/all`

Anh trong section:

1. `Father's Day Gift Ideas`  
   `https://ashdeco.com/cdn/shop/files/ashdeco_father_day_mobile.webp?v=1778752624&width=480`

### 3. Browse by category

- Layout: cum chip/category link dang wrap tren mobile.
- Cac category hien thi: `Trending`, `Reading Nook`, `Surfaces`, `Bath & Sink`, `Bed Essentials`, `Mood Makers`.
- DOM co heading/preview an lien quan `Trending This Week`, nhung giao dien mobile thay duoc chu yeu la category nav.

Anh trong section:

- Khong co anh noi dung. Chi co icon nho trong chip `Trending`.

### 4. Collections by mood

- Layout: section carousel/list ngang cac mood collection.
- Heading: `Collections by mood`
- Moi collection card co cum collage 3 anh: 1 anh chinh lon va 2 anh phu nho.

Anh trong section theo thu tu:

1. Raw & Rooted - anh chinh  
   `https://ashdeco.com/cdn/shop/files/12.png?v=1778474448&width=600`
2. Raw & Rooted - anh phu  
   `https://ashdeco.com/cdn/shop/files/11.png?v=1778474449&width=300`
3. Raw & Rooted - anh phu  
   `https://ashdeco.com/cdn/shop/files/13.png?v=1778474448&width=300`
4. Into the Wood - anh chinh  
   `https://ashdeco.com/cdn/shop/files/21.png?v=1778474448&width=600`
5. Into the Wood - anh phu  
   `https://ashdeco.com/cdn/shop/files/22_d8ea6cf8-ac14-45a1-a5a0-6c218d88d33c.png?v=1778474448&width=300`
6. Into the Wood - anh phu  
   `https://ashdeco.com/cdn/shop/files/23.png?v=1778474448&width=300`
7. Relax Corner - anh chinh  
   `https://ashdeco.com/cdn/shop/files/31.png?v=1778474448&width=600`
8. Relax Corner - anh phu  
   `https://ashdeco.com/cdn/shop/files/32.png?v=1778474448&width=300`
9. Relax Corner - anh phu  
   `https://ashdeco.com/cdn/shop/files/33.png?v=1778474448&width=300`
10. Statement Wall - anh chinh  
    `https://ashdeco.com/cdn/shop/files/41.png?v=1778474448&width=600`
11. Statement Wall - anh phu  
    `https://ashdeco.com/cdn/shop/files/43.png?v=1778474448&width=300`
12. Statement Wall - anh phu  
    `https://ashdeco.com/cdn/shop/files/42.png?v=1778474448&width=300`

### 5. For you, today

- Layout: product discovery section, masonry grid 2 cot tren mobile.
- Heading: `For you, today`
- Filter pills: `All`, `Newest`, `Under $2000`
- Cuoi section co CTA `View all products`.

Anh trong section theo thu tu:

1. Corner Tree Floating Bookshelf - Driftwood Branch Wall Mounted Hanging Shelf, Artistic Corner Furniture Decoration  
   `https://ashdeco.com/cdn/shop/files/vananhtse_58851_httpss.mj.runC1B3uQNk99k_A_wall_shelf_made_of_t_eb3940ee-e7e8-4fad-99be-ff90cb818a5e.png?v=1776088597&width=600`
2. Rustic Driftwood Tree Branch Floating Shelf - Handcrafted Solid Wood Wall Shelf  
   `https://ashdeco.com/cdn/shop/files/hjj_19039889-e917-4e41-80d2-ec96f530d9d0.jpg?v=1776092169&width=600`
3. Solid Wood Floating Corner Shelf - Driftwood Branch Wall Shelf  
   `https://ashdeco.com/cdn/shop/files/ytuu.jpg?v=1776092090&width=600`
4. Floating Bookshelf - Tree Branch Wall-Mounted Bookcase for Rustic Home Decor  
   `https://ashdeco.com/cdn/shop/files/fdgg.jpg?v=1776092025&width=600`
5. Tree Kids Bookshelf - Handmade Natural Wood Shelf for Baby Room Decor  
   `https://ashdeco.com/cdn/shop/files/gh_4fd85dde-1f23-42df-8bc6-c5b74e880e1d.jpg?v=1776090258&width=600`
6. Tree Bookshelf - Rustic Wooden Book Tree Shelf, Wall-Mounted Natural Wood Decor  
   `https://ashdeco.com/cdn/shop/files/ghj_dd8fcc48-a560-4a60-be13-77d3ffb3e29f.jpg?v=1776089998&width=600`
7. Rustic Tree Shaped Wooden Bookshelf with Branch Design for Living Room or Home Library  
   `https://ashdeco.com/cdn/shop/files/Wall_Tree_Bookshelf.jpg?v=1776089873&width=600`
8. Sculptural Tree Branch Live Edge Solid Wood Wall Shelf - Dramatic Black Organic Bookshelf  
   `https://ashdeco.com/cdn/shop/files/SculpturalTreeBranchLiveEdgeSolidWoodWallShelf_DramaticBlackOrganicBookshelf1.jpg?v=1780547477&width=600`
9. Natural Wooden Wall Shelf for Plants & Decor, Unique Handmade Gift  
   `https://ashdeco.com/cdn/shop/files/NaturalWoodenWallShelfforPlants_Decor_UniqueHandmadeGift2.png?v=1778829743&width=600`
10. Kids Custom Bookcase Decor Bed Room Kids Personalized Gift  
    `https://ashdeco.com/cdn/shop/files/corner_tree_bookdhelf_10.jpg?v=1776096774&width=600`
11. Handcrafted Solid Wood Nursery Decor & Kids' Library  
    `https://ashdeco.com/cdn/shop/files/Standing_Tree_Bookshelf_13.jpg?v=1776096619&width=600`
12. Solid Wood Nursery Decor & Unique Birthday Gift for Toddlers  
    `https://ashdeco.com/cdn/shop/files/Standing_Tree_Bookshelf_9.jpg?v=1776096611&width=600`

### 6. Featured Artisans

- Layout: intro copy o tren, carousel artist cards ben duoi.
- Eyebrow: `Featured This Week`
- Heading: `Meet the makers behind every piece`
- Card artist gom anh, ten, tagline, stat va link profile.

Anh trong section theo thu tu:

1. Huan Ngo  
   `https://ashdeco.com/cdn/shop/files/Huan_Ngo.png?v=1778150057&width=800`
2. Dien Luc  
   `https://ashdeco.com/cdn/shop/files/Dien_Luc.png?v=1778060022&width=800`
3. Trung Le  
   `https://ashdeco.com/cdn/shop/files/Trung_Le.png?v=1778060022&width=800`

### 7. Wood that lives beautifully

- Layout: editorial/image banner cao, text overlay o phan duoi anh.
- Heading: `Wood that lives beautifully`
- Copy: `Handcarved. One of a kind. Yours.`
- CTAs: `EXPLORE COLLECTION`, `CUSTOMIZE YOURS`
- DOM co 2 slide/anh trong section.

Anh trong section theo thu tu:

1. Collection banner - father's day  
   `https://ashdeco.com/cdn/shop/files/ashdeco_collection_banner_fatherday.webp?v=1778755579&width=550`
2. Collection banner - Ashdeco  
   `https://ashdeco.com/cdn/shop/files/banner_collection_banner_ashdeco.webp?v=1778755579&width=550`

### 8. What's getting saved right now

- Layout: product/social proof section, masonry grid 2 cot tren mobile.
- Heading: `What's getting saved right now`
- Filter pills: `All`, `Under $200`
- Cuoi section co CTA xem them.

Anh trong section theo thu tu:

1. Rustic Corner Wall Shelf - Natural Live Edge Wood Floating Shelf for Candles and Plants  
   `https://ashdeco.com/cdn/shop/files/11bc2f4d-1748-4361-b196-10e2eef2914e.png?v=1777859148&width=600`
2. Custom Wood Coat Rack - Driftwood Wall Mount Clothes Rack with Unique Hooks  
   `https://ashdeco.com/cdn/shop/files/Tree_Coat_Rack_1.jpg?v=1776090220&width=600`
3. Rustic Reclaimed Wood Coffee Table with Shelf - Handmade Farmhouse Barnwood Furniture  
   `https://ashdeco.com/cdn/shop/files/lk_8631bb20-c5da-4b21-b2d5-84b069cdbbf8.jpg?v=1776089946&width=600`
4. Rustic Live Edge Floating Vanity - Handmade Wooden Bathroom Shelf with Brackets  
   `https://ashdeco.com/cdn/shop/files/tyui_f44e8974-9dac-4130-9c80-0cb6db01836a.jpg?v=1776088897&width=600`
5. Handcrafted Live Edge Floating Bar Shelf - Rustic Solid Wood Wall Shelf for Kitchen or Bar  
   `https://ashdeco.com/cdn/shop/files/6b9ce53d-9be5-4d9c-88e7-b578043a3039.png?v=1777860691&width=600`
6. Rustic Teak Root Wood Corner Shelf - Floating Corner Shelf Decor  
   `https://ashdeco.com/cdn/shop/files/a-warm-minimalist-interior-scene-featuri_UueoJSqKRMCuU8xEAkZ0cg_u5zljZhjTt2KeDPDeUQYHg.png?v=1776089125&width=600`
7. Solid Wood Turntable Stand - Rustic Record Player Cabinet with Farmhouse Storage  
   `https://ashdeco.com/cdn/shop/files/be6aaba4-ae5d-44ba-b0bb-5ff6b991f3dd.png?v=1776095568&width=600`
8. Natural Driftwood Coat Rack - Handcrafted Tree Branch Standing Hanger for Entryway or Bedroom  
   `https://ashdeco.com/cdn/shop/files/Coat_Racks_Hangers.jpg?v=1776089714&width=600`
9. Handcrafted Organic Wooden Floating Wall Shelf - Live Edge Solid Wood  
   `https://ashdeco.com/cdn/shop/files/dfe_716dfc32-293e-4208-a6a0-f2f4f6480e5c.jpg?v=1776093874&width=600`
10. Live Edge Corner Floating Shelf - Handcrafted Solid Wood Wall Shelf  
    `https://ashdeco.com/cdn/shop/files/67.png?v=1776096271&width=600`
11. Handcrafted Rustic Mushroom Floating Shelf - Live Edge Wooden Wall Decor  
    `https://ashdeco.com/cdn/shop/files/Handcrafted_Rustic_Mushroom_Floating_Shelf_Live_Edge_Wooden_Wall_D_cor3.webp?v=1778739942&width=600`
12. Rustic Live Edge Corner Shelf - Handmade Solid Wood Floating Wall Shelf  
    `https://ashdeco.com/cdn/shop/files/hg_9ae0d281-7bd8-4b3b-af5a-523c0e3d4c5f.jpg?v=1776090974&width=600`
13. Rustic Live Edge Corner Floating Shelf - Handmade Solid Wood Wall Shelf  
    `https://ashdeco.com/cdn/shop/files/yt_58e6020d-1327-47a3-986f-4c441435bea9.jpg?v=1776090940&width=600`
14. Rustic Driftwood Floor Lamp - Handmade Solid Wood Standing Light for Home Decor  
    `https://ashdeco.com/cdn/shop/files/io_7d49e26b-d301-4d7d-accd-05212a5b8509.jpg?v=1776089795&width=600`
15. Handcrafted Rustic Floating Bathroom Vanity - Custom Live Edge Shelf, Solid Wood Bathroom Decor  
    `https://ashdeco.com/cdn/shop/files/jghkhk_1.jpg?v=1776088865&width=600`

### 9. What people are searching

- Layout: grid/list cac search tiles dang 2 cot tren mobile.
- Heading: `What people are searching`
- Moi tile co anh vuong, query va badge/ngan mo ta.

Anh trong section theo thu tu:

1. `live edge dining table` tile  
   `https://ashdeco.com/cdn/shop/files/hhh.jpg?v=1776092751&width=600`
2. `tree branch bookshelf` tile  
   `https://ashdeco.com/cdn/shop/files/gj_674eb5eb-f165-4fb0-9b9c-bd40b559dbdd.jpg?v=1776094942&width=600`
3. `floating bathroom vanity` tile  
   `https://ashdeco.com/cdn/shop/files/hk_3b17a977-5638-4f4a-b0ae-ed01578582f2.jpg?v=1776094720&width=600`
4. `entryway shoe bench` tile  
   `https://ashdeco.com/cdn/shop/files/Shoe_Bench_2.png?v=1776097445&width=600`
5. `floating wood shelves` tile  
   `https://ashdeco.com/cdn/shop/files/1.jpg?v=1776095132&width=600`
6. `rustic tv stand` tile  
   `https://ashdeco.com/cdn/shop/files/kl_1_93b36364-bb4d-4d20-be1a-aed6345cec99.jpg?v=1776090156&width=600`

### 10. What our customers are saying

- Layout: testimonial/social proof section.
- Heading: `What our customers are saying`
- Phan tren co cac avatar/anh customer nho dang orbit/cluster, ben duoi la testimonial cards.

Anh trong section theo thu tu:

1. Colorado customer image  
   `https://ashdeco.com/cdn/shop/files/Colorado.jpg?v=1778058570&width=320`
2. Florida customer image  
   `https://ashdeco.com/cdn/shop/files/Florida.jpg?v=1778058569&width=320`
3. Ohio customer image  
   `https://ashdeco.com/cdn/shop/files/Ohio.jpg?v=1778058569&width=320`
4. New Jersey customer image  
   `https://ashdeco.com/cdn/shop/files/New_Jersey.jpg?v=1778058570&width=320`
5. Arizona customer image  
   `https://ashdeco.com/cdn/shop/files/Arizona.jpg?v=1778058569&width=320`
6. Pennsylvania customer image  
   `https://ashdeco.com/cdn/shop/files/Pennsylvania.jpg?v=1778058569&width=320`
7. Michigan customer image  
   `https://ashdeco.com/cdn/shop/files/michigan_6292a230-a0ec-41e9-9408-ce4dedb5194c.jpg?v=1778039391&width=320`

### 11. Consultation / room-fit CTA

- Layout: consultation CTA section.
- Eyebrow: `Speak with the Ashdeco`
- Heading: `Unsure what will fit your room?`
- Co 3 option button: send photos, video consultation, trade-in.
- Ben duoi la CTA dat lich va card advisor/founder.

Anh trong section:

1. Mr Nguyen avatar  
   `https://ashdeco.com/cdn/shop/files/fouder_ashdeco.webp?v=1776093038&width=128`

### 12. Frequently asked questions

- Layout: FAQ accordion.
- Heading: `Frequently asked questions`
- Tabs: `All`, `Shipping`, `Commissions`, `Care`, `Returns`, `Payment`
- Danh sach accordion cau hoi va link `Get in touch`.

Anh trong section:

- Khong co anh noi dung.

### 13. Shopify app / empty section

- Layout: section app Shopify (`shopify-section--apps`) cao khoang 696 px.
- Tai thoi diem audit mobile, section nay khong co text, khong co iframe va khong co anh trong DOM. Co ve la app slot/spacer dang render rong.

Anh trong section:

- Khong co.

### 14. Newsletter signup

- Layout: section nen do, copy can giua, email input va button `Join the list`, ben duoi la 3 trust bullet.
- Heading: `Get new pieces 24 hours early`

Anh trong section:

- Khong co anh noi dung. Chi co icon nho cho benefit bullets.

### 15. Footer

- Layout: footer mobile gom contact info, Company links, Help Center links, newsletter footer input, social links, country/currency selector, payment icons va copyright.
- Trustpilot review collector co the xuat hien gan footer trong snapshot/widget, nhung lan DOM audit sau cung khong thay iframe trong app section chinh.

Anh trong footer:

- Chi co social/payment/icon UI, khong co anh noi dung homepage.
