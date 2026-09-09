Mình đã crawl lại **wrydeco.com trong hôm nay, 09/09/2026**, trực tiếp từ homepage, Journal và các collection hiện tại. Mình **không dùng các bản product page mà crawler trả về cache 2–3 tuần trước**; những URL không xác nhận được freshness mình loại khỏi kết luận. Vì vậy phần dưới tập trung vào dữ liệu mình xác nhận là **“Crawled: today”**. Đây là audit về **on-page SEO + keyword architecture + ecommerce merchandising**; mình chưa chấm robots.txt/sitemap/Core Web Vitals vì lần fetch hiện tại không cho mình xác minh các phần đó đủ chắc chắn.

## Kết luận trước

Nếu chỉ chấm **on-page SEO + cách phân bố keyword hiện tại**, mình cho WRYDECO khoảng:

| Hạng mục                    |        Điểm |
| --------------------------- | ----------: |
| Homepage positioning        |    **8/10** |
| Collection SEO              |    **5/10** |
| Keyword architecture        |    **6/10** |
| Internal linking / taxonomy |  **6.5/10** |
| Product naming              |    **8/10** |
| Blog / topical authority    |    **8/10** |
| Merchant trust consistency  |    **6/10** |
| **Tổng thể hiện tại**       | **~6.7/10** |

Điểm quan trọng nhất là: **WRYDECO không thiếu keyword. Ngược lại, site đang có rất nhiều keyword tốt nhưng chưa phân quyền URL rõ ràng.**

Vấn đề SEO lớn nhất hiện tại không phải kiểu “keyword xuất hiện ít quá”, mà là:

> **Google chưa được cung cấp đủ tín hiệu rõ ràng rằng URL nào phải sở hữu keyword nào.**

Đặc biệt ở cluster **Tree Bookshelf**.

---

# 1. Homepage: nền tảng khá tốt

Title hiện tại:

> **WRYDECO | Handcrafted Sculptural Solid Wood Furniture**

Đây là một title tốt cho thương hiệu furniture cao cấp vì nó gói được ba entity rất có giá trị:

**handcrafted → sculptural → solid wood furniture**

Homepage cũng liên kết rõ tới Coffee Tables, Wood Floor Sculptures, Floating Wood Shelves, Wood Wall Mirrors, Tree Bookshelves và nhiều subcategory bookshelf. Sau đó còn có các section về craftsmanship, wood species, custom design, artisans, solid wood care và Journal. ([Wrydeco][1])

Với góc nhìn merchant, mình thích cách homepage mới đang nói:

**WRYDECO = artisan-made sculptural solid wood furniture**

thay vì cố trở thành một website chung chung kiểu “furniture store”.

Đây là positioning có khả năng tạo brand authority rất tốt.

### Nhưng có một lỗi on-page đáng chú ý

Trong bản HTML/text crawler nhận được hôm nay, mình không thấy một **H1 rõ ràng ở hero** tương ứng với chủ đề chính của homepage. Nội dung đi từ trust block sang các H2 như:

- “From Nature to Artful Living”
- “Curated Collections”
- “Sculptural Furniture for Distinctive Interiors”

([Wrydeco][1])

Google nói rõ rằng ngoài `<title>`, hệ thống còn dùng **main visual title, H1, prominent text và anchor text** để hiểu tiêu đề/chủ đề chính của trang. ([Google Developers][2])

Mình sẽ để homepage có H1 kiểu:

**Handcrafted Sculptural Solid Wood Furniture**

hoặc:

**Sculptural Solid Wood Furniture, Handcrafted to Order**

Không cần nhồi thêm `wood furniture`, `handmade furniture`, `custom furniture`, `luxury furniture` vào cùng H1.

---

# 2. Collection page hiện là điểm yếu SEO lớn nhất

Đây là vấn đề mình ưu tiên sửa đầu tiên.

Ví dụ `/collections/tree-bookshelves` hiện title khá tốt:

> **Tree Bookshelves | Handcrafted Wood Designs | Wrydeco**

Nhưng khi crawler render page hôm nay, sau navigation nó đi thẳng vào:

> Category
> Bookcases & Standing Shelves
> Corner Bookcases & Shelves
> Floating Bookcases & Shelves
> ...
> Sort by
> 106 items

rồi lập tức tới product grid. Không có một đoạn category copy/H1 rõ ràng xuất hiện trước grid. ([Wrydeco][3])

Tình trạng tương tự xảy ra với Coffee Tables, Floating Wood Shelves, Beds & Headboards và các collection khác mình kiểm tra. ([Wrydeco][4])

Đây là chỗ WRYDECO đang **bỏ phí rất nhiều SEO potential**.

Title chỉ nói cho Google một phần. Collection page nên tự trả lời:

> Đây là loại furniture gì?
> Khác collection kia thế nào?
> Material là gì?
> Placement/use case là gì?
> Ai nên mua?
> Những subtype nào nằm bên trong?

### Không cần phá UI mới

Mình **không khuyên nhét 700 từ lên trên product grid**.

Đối với furniture ecommerce cao cấp, layout mình dùng sẽ là:

**trên grid:** H1 + khoảng 70–120 từ rất cô đọng.

**dưới grid:** buyer guide khoảng 300–600 từ + 3–5 FAQ nếu thực sự hữu ích.

Như vậy UI vẫn sạch mà Google có đủ semantic context.

---

# 3. Tree Bookshelf đang có nguy cơ keyword cannibalization cao nhất

Homepage hiện link tới cùng lúc:

Tree Bookshelves
Sculptural Bookshelves
Rustic Tree Bookshelves
Corner Tree Bookshelves
Standing Tree Bookshelves
Floating Bookshelves
Wall-Mounted Tree Bookshelves

và chúng còn xuất hiện ở cả Home Office & Library lẫn Nursery & Kids' Room. ([Wrydeco][1])

Việc tạo nhiều subcollection **không sai**. Thực ra về SEO nó rất tốt nếu mỗi page sở hữu một search intent.

Vấn đề là khi collection page gần như chỉ có product grid, Google phải suy luận chủ đề dựa rất nhiều vào:

**title + product names + anchor text + các sản phẩm trùng giữa collections.**

Main Tree Bookshelves hiện có **106 sản phẩm**, bao gồm corner, floating, wall shelf và nhiều kiểu khác nhau. ([Wrydeco][3])

Cho nên mình sẽ xây cluster như sau:

| URL / Collection                | Primary keyword nên sở hữu         | Secondary semantics                                                      |
| ------------------------------- | ---------------------------------- | ------------------------------------------------------------------------ |
| `/collections/tree-bookshelves` | **tree bookshelf**                 | tree shaped bookshelf, wooden tree bookshelf, handcrafted tree bookshelf |
| Corner Tree Bookshelves         | **corner tree bookshelf**          | corner tree shelf, corner bookshelf, solid wood corner shelf             |
| Standing Tree Bookshelves       | **freestanding tree bookshelf**    | standing tree bookshelf, tree bookcase                                   |
| Wall-Mounted Tree Bookshelves   | **wall mounted tree bookshelf**    | wall tree bookcase, tree bookshelf wall                                  |
| Floating Bookshelves            | **tree branch floating bookshelf** | floating tree bookshelf, tree branch wall shelf                          |
| Rustic Tree Bookshelves         | **rustic tree bookshelf**          | natural wood tree bookshelf, rustic tree bookcase                        |
| Sculptural Bookshelves          | **sculptural wood bookshelf**      | curved bookshelf, organic bookshelf, sculptural bookcase                 |

### Quan trọng

Parent `/tree-bookshelves` có thể **nhắc tới** corner, standing, wall-mounted, floating...

Nhưng nó phải nhắc như **subtypes và internal links**, không cố rank mạnh cho tất cả các modifier đó.

Ví dụ:

> Explore handcrafted tree bookshelves in solid wood, from freestanding designs to corner, wall-mounted and floating configurations.

Sau đó link:

`corner tree bookshelves` → Corner collection
`wall-mounted tree bookshelves` → Wall-mounted collection

Google khuyến nghị ecommerce structure theo kiểu **category → subcategory → product**, và Google còn dùng hệ thống internal links để suy ra mức quan trọng tương đối của từng page. ([Google Developers][5])

Đó chính xác là architecture phù hợp cho WRYDECO.

---

# 4. “Floating Bookshelf” và “Floating Wood Shelf” hiện bị lẫn intent

Đây là cluster mình đặc biệt chú ý.

`Floating Wood Shelves` hiện chứa đồng thời:

- Solid Wood Arched Floating Two Tier Wall Shelf
- Dense Branch Tree Wall Bookcase
- Open Canopy Tree Branch Wall Bookcase
- Tall Tree Branch Wall Shelf
- Fluted Wood Floating Shelves
- Tree Branch Bookshelf
- Rustic Driftwood Floating Shelf

([Wrydeco][6])

Về merchant taxonomy, có **hai product intent khác nhau** đang được trộn:

**Shelf intent**

> floating wood shelf
> solid wood floating shelf
> fluted wood shelf
> wall display shelf

và:

**Bookshelf / bookcase intent**

> tree branch bookshelf
> wall bookcase
> floating bookshelf
> tree wall bookshelf

Chúng có liên quan nhưng không hoàn toàn cùng transactional intent.

Mình sẽ giữ ranh giới:

**Floating Wood Shelves**
→ shelf / ledge / fluted / decorative wall shelf.

**Floating Tree Bookshelves**
→ book storage / larger branch structures / tree wall bookcase.

Nếu không tách semantic boundary rõ, collection pages sẽ tự ăn keyword của nhau.

---

# 5. Coffee Table collection có taxonomy leak

Collection hiện có 7 items, nhưng filter cho thấy:

> Coffee Tables (5)
> Console Tables (2)

Và hai sản phẩm thực sự mang tên:

> Rustic Tree Console Table Bookshelf Solid Wood Display
> Rustic Tree Console Table Bookshelf 3 Tier Display

([Wrydeco][4])

Đây không chỉ là UX.

Nó ảnh hưởng luôn đến semantic profile của `/collections/coffee-tables`.

Nếu Google crawl collection và thấy:

**coffee table → coffee table → coffee table → console bookshelf → console bookshelf → root coffee table**

thì topical concentration yếu hơn một collection thuần coffee table.

Mình khuyên đưa console table ra collection riêng hoặc một parent collection kiểu `Console & Accent Tables`.

Với Coffee Tables, cluster keyword nên tập trung quanh:

**Primary:** `solid wood coffee table` hoặc `sculptural wood coffee table`

**Secondary:**

organic wood coffee table
solid oak coffee table
live edge coffee table
root wood coffee table
handcrafted coffee table
sculptural coffee table

Title hiện tại **“Sculptural Solid Wood Coffee Tables | Wrydeco”** rất ổn. ([Wrydeco][4])

Cái thiếu là body content + taxonomy cleanliness.

---

# 6. Beds collection có một lỗi taxonomy còn rõ hơn

`Solid Wood Platform Beds & Headboards` hiện có 13 sản phẩm.

Giữa các bed frame và headboard lại có:

> **Solid Wood Vinyl Record Stand with Turntable Shelf**

([Wrydeco][7])

Cái này nên sửa ngay.

Không phải vì Google sẽ “phạt”, mà vì page entity sẽ trở nên:

> bed → platform bed → bed → headboard → **record player stand** → headboard...

Đối với một category page chỉ có 13 sản phẩm thì **1 sản phẩm sai taxonomy chiếm tỷ trọng semantic khá lớn**.

---

# 7. Product naming hiện tại lại là điểm mạnh

Ở product grid mới, naming nhìn chung tốt hơn ecommerce site furniture bình thường rất nhiều.

Ví dụ:

> Handcrafted Curved Oak Wood Coffee Table Centerpiece
> Elongated Organic Wave Oak Coffee Table
> Asymmetric Organic Wave Oak Coffee Table
> Handcrafted Live Edge Natural Wood Root Coffee Table

([Wrydeco][4])

Đây là cách đặt tên mình thích cho SEO furniture:

**design/form + material + product type + differentiator**

Thay vì:

> Coffee Table #12

Điều này giúp bắt cực nhiều long-tail query như:

`organic wave oak coffee table`

`curved oak wood coffee table`

`live edge root wood coffee table`

`sculptural oak coffee table`

Mình **không khuyên sửa toàn bộ product title chỉ để nhét keyword**. Phần này WRYDECO đang đi đúng hướng.

---

# 8. Blog/Journal hiện là tài sản SEO mạnh nhất của WRYDECO

Journal hiện đã có những article rất đúng search journey:

> How to Style a Tree Bookshelf With Books, Plants and Decor
> How a Tree Branch Bookshelf Is Made
> Tree Bookshelf Ideas for Every Room
> How to Create a Reading Nook With a Bookshelf
> Floating Shelf Ideas for an Empty Living Room Wall

([Wrydeco][8])

Đây là một content cluster rất tốt bởi nó không chỉ săn traffic informational mà còn hỗ trợ commercial page.

Nó tạo journey:

**Tree Bookshelf Ideas**

↓
**Tree Bookshelf Types**

↓
**Size / placement / material**

↓
**Tree Bookshelf collection**

↓
**specific product**

Đây chính là cách mình xây SEO cho high-ticket furniture.

### Nhưng `/blogs/news` + H1 `News` đang rất phí

Current page hiển thị:

> WRYDECO Journal
> **H1: News**

([Wrydeco][8])

`News` gần như không tạo topical relevance cho business.

Mình sẽ đổi H1 thành:

**Solid Wood Furniture Journal**

hoặc:

**Wood Furniture Design & Buying Guides**

URL `/blogs/news` không đẹp nhưng **không nên đổi URL chỉ vì SEO** nếu nó đã index và có backlinks.

H1/copy/title có thể sửa mà không cần migration URL.

---

# 9. Content hiện đang nghiêng quá mạnh về Tree Bookshelf

Đây vừa là ưu điểm vừa là nhược điểm.

Mình thực sự **ủng hộ WRYDECO tiếp tục dùng Tree Bookshelf làm hero category**. Đây là loại sản phẩm có silhouette khác biệt, visual mạnh, giá trị artisan cao và dễ xây brand association.

Nhưng topical authority sitewide nên mở rộng theo commercial inventory:

| Commercial cluster | Content cần bổ sung                                                                           |
| ------------------ | --------------------------------------------------------------------------------------------- |
| Coffee Tables      | coffee table size guide, coffee table vs room proportions, organic vs live-edge, wood species |
| Wood Wall Mirrors  | mirror size guide, mirror above console, organic wood mirror styling, solid wood mirror guide |
| Beds & Headboards  | platform bed size, headboard height, room clearance, installation                             |
| Floating Shelves   | load capacity, spacing, installation, shelf depth                                             |
| Wine Racks         | capacity, bottle orientation, mounting height, wine rack sizing                               |
| Floor Sculptures   | choosing scale, placement, lighting, styling sculptural wood                                  |

Tree bookshelf nên vẫn là cluster lớn nhất, nhưng **không nên là cluster duy nhất có chiều sâu**.

---

# 10. Không nên nghĩ keyword distribution theo “density”

Đây là điểm mình muốn nhấn mạnh.

Mình **không khuyên** đặt rule kiểu:

> Primary keyword 2%
> secondary keyword 1%
> keyword phải xuất hiện 8 lần.

Đối với WRYDECO, cách đúng là **keyword ownership theo URL**.

Mô hình mình đề xuất:

| Page type         | Keyword role                           |
| ----------------- | -------------------------------------- |
| Homepage          | broad brand/category entity            |
| Parent collection | head commercial keyword                |
| Subcollection     | commercial modifier                    |
| Product           | transactional long-tail                |
| Blog              | informational/problem/selection intent |
| About / Makers    | craftsmanship, brand/entity trust      |

Ví dụ:

**Homepage**

`handcrafted solid wood furniture`
`sculptural wood furniture`

↓

**Collection**

`tree bookshelf`

↓

**Subcollection**

`corner tree bookshelf`

↓

**Product**

`wide branch solid wood corner tree bookshelf`

↓

**Blog**

`how to choose a corner bookshelf`

Đó mới là một semantic architecture khỏe.

---

# 11. Internal linking: UI mới đang tạo nền tốt, nhưng cần “đẩy authority” có chủ đích

Homepage hiện link khá nhiều tới major collections, và Journal cũng đang gắn chủ đề vào furniture. Đây là hướng tốt. ([Wrydeco][1])

Google nói khá rõ rằng số và ngữ cảnh internal links giúp họ hiểu **mối quan hệ và relative importance giữa các pages**. Anchor text cũng nên rõ nghĩa. ([Google Developers][5])

Vì vậy blog không nên chỉ viết xong rồi tồn tại độc lập.

Ví dụ article:

**Tree Bookshelf Ideas for Every Room**

nên có contextual links kiểu:

> For unused corners, explore our **corner tree bookshelves**.

và:

> For rooms where floor space is limited, see our **wall-mounted tree bookshelves**.

Không phải CTA generic:

> Click here
> Shop now
> Learn more

---

# 12. Có một lỗi merchant/trust mình đánh giá nghiêm trọng hơn SEO

Homepage hiện ghi rất rõ:

> **1-Year Warranty**

và FAQ cũng nói WRYDECO cung cấp **1-year limited warranty**. ([Wrydeco][1])

Nhưng Journal hiện tại vẫn hiển thị:

> **5-Year Warranty — For structural integrity**

([Wrydeco][8])

### Cần sửa ngay.

Với sản phẩm furniture giá vài nghìn đến gần $20,000, đây không còn chỉ là một lỗi copy nhỏ.

Nó ảnh hưởng:

**trust → conversion → support disputes → Merchant consistency.**

Merchant selling $3,000–$19,000 furniture cần tuyệt đối nhất quán về:

warranty
shipping
custom order
returns
materials
lead time.

Đây là **P0** đối với mình.

---

# 13. Faceted navigation cần kiểm tra sau UI update

Collection hiện có các filter như Category, Price và Sort. ([Wrydeco][3])

Filter tự nó hoàn toàn bình thường.

Nhưng cần kiểm tra nó có tạo hàng loạt URL dạng:

`?filter...`

`?sort_by...`

và liệu Google có crawl/index chúng hay không.

Google cảnh báo faceted navigation có thể tạo gần như vô hạn URL, gây **overcrawl và làm chậm discovery của những URL quan trọng**. ([Google Developers][9])

Mình chưa xác minh live được behavior này, nên **không kết luận WRYDECO đang lỗi**.

Nhưng sau redesign đây là mục technical audit bắt buộc.

---

# 14. Structured data nên tận dụng rất mạnh cho loại hàng WRYDECO

Furniture của WRYDECO có:

size
finish/color
wood/material
custom options

nên rất phù hợp với `Product` + `ProductGroup`.

Google hiện khuyến nghị với products có variants như **furniture**, dùng `ProductGroup`, `variesBy`, `hasVariant`, `productGroupID` để Google hiểu các variants thuộc cùng một product. ([Google Developers][10])

Merchant listing còn hỗ trợ các thuộc tính rất phù hợp với WRYDECO như `material` và product variant data. ([Google Developers][11])

Đây là chỗ rất đáng đầu tư vì WRYDECO bán sản phẩm physical, high-ticket và có variants rõ ràng.

---

# Keyword map mình sẽ dùng cho WRYDECO

Đây là architecture mình đánh giá phù hợp nhất với inventory hiện tại:

| Landing page            | Primary                          | Secondary                                        |
| ----------------------- | -------------------------------- | ------------------------------------------------ |
| Homepage                | handcrafted solid wood furniture | sculptural wood furniture, custom wood furniture |
| Tree Bookshelves        | tree bookshelf                   | tree shaped bookshelf, wooden tree bookshelf     |
| Rustic Tree Bookshelves | rustic tree bookshelf            | natural wood tree bookshelf                      |
| Sculptural Bookshelves  | sculptural wood bookshelf        | curved bookshelf, organic bookshelf              |
| Corner                  | corner tree bookshelf            | corner tree shelf, corner bookcase               |
| Standing                | freestanding tree bookshelf      | standing tree bookshelf                          |
| Wall Mounted            | wall mounted tree bookshelf      | tree wall bookcase                               |
| Floating Bookshelves    | tree branch floating bookshelf   | tree branch wall bookcase                        |
| Floating Wood Shelves   | solid wood floating shelves      | fluted wood shelf, wood wall shelf               |
| Coffee Tables           | sculptural wood coffee table     | organic coffee table, solid wood coffee table    |
| Wall Mirrors            | wood wall mirror                 | solid wood mirror, organic wood mirror           |
| Wine Racks              | wood wine rack                   | solid wood wine rack                             |
| Wall Wine Racks         | wall mounted wood wine rack      | wine rack with glass holder                      |
| Beds & Headboards       | solid wood platform bed          | live edge headboard, wood bed frame              |
| Floor Sculptures        | wood floor sculpture             | sculptural wood decor                            |

**Một keyword head/commercial intent chính → một canonical landing page.**

Đó là nguyên tắc quan trọng nhất.

---

# Thứ tự mình sẽ sửa

1. **Sửa ngay 5-Year Warranty → 1-Year Warranty** trên Journal nếu policy hiện tại thực sự là 1 năm. ([Wrydeco][1])
2. **Thêm H1 + unique collection intro** cho tất cả money collections.
3. Xây **keyword ownership map** cho 7 Tree Bookshelf collections để giảm cannibalization.
4. Tách rõ `Floating Wood Shelves` và `Floating Tree Bookshelves`.
5. Remove `Vinyl Record Stand` khỏi Beds & Headboards. ([Wrydeco][7])
6. Remove/relocate console tables khỏi Coffee Tables hoặc tạo taxonomy parent phù hợp. ([Wrydeco][4])
7. Thêm contextual internal links từ từng blog → đúng commercial landing page.
8. Đổi Journal H1 từ **News** → một heading semantic hơn.
9. Mở rộng topical cluster cho Mirrors, Coffee Tables, Beds, Wine Racks và Floor Sculptures.
10. Audit faceted URLs, canonical, sitemap, indexability và Product/ProductGroup schema sau redesign.

---

## Nhận xét dưới góc nhìn merchant wood furniture

**Mình không nghĩ WRYDECO nên cố trở thành một site SEO cho “all wood furniture”.**

Điểm mạnh nhất của brand hiện tại là:

> **sculptural + organic + artisan-made + solid wood + highly distinctive furniture**

và đặc biệt là **Tree Bookshelf**.

Nếu làm đúng architecture, mình sẽ muốn Google dần hình thành association:

> `WRYDECO → Tree Bookshelf → Sculptural Solid Wood Furniture`

rồi mở authority ra:

> Coffee Tables → Wall Shelves → Mirrors → Beds → Wood Art.

Homepage mới hiện đã bắt đầu kể đúng câu chuyện đó: made-to-order, artisan craft, wood species, custom sizing, maker profiles và sculptural furniture đều xuất hiện rõ. ([Wrydeco][1])

**Vì vậy mình sẽ không làm một đợt “nhồi SEO keyword” lên toàn site.** WRYDECO đang cần **semantic architecture và category landing pages**, chứ không cần thêm keyword vô tội vạ.

Nếu chỉ được chọn **một việc SEO để làm ngay sau UI update**, mình sẽ chọn:

> **Lập lại keyword map cho toàn bộ Collections theo nguyên tắc “1 URL = 1 primary commercial intent”, sau đó viết H1 + category copy + internal anchor dựa trên map đó.**

Đây sẽ tạo impact lớn hơn nhiều so với sửa vài meta title hoặc tăng keyword density.

[1]: https://wrydeco.com/ "WRYDECO | Handcrafted Sculptural Solid Wood Furniture"
[2]: https://developers.google.com/search/docs/appearance/title-link?utm_source=chatgpt.com "Influencing Title Links in Google Search | Google Search Central  |  Documentation  |  Google for Developers"
[3]: https://wrydeco.com/collections/tree-bookshelves "Tree Bookshelves | Handcrafted Wood Designs | Wrydeco"
[4]: https://wrydeco.com/collections/coffee-tables "Sculptural Solid Wood Coffee Tables | Wrydeco"
[5]: https://developers.google.com/search/docs/specialty/ecommerce/help-google-understand-your-ecommerce-site-structure?utm_source=chatgpt.com "Ecommerce Website Navigation Structure | Google Search Central  |  Documentation  |  Google for Developers"
[6]: https://wrydeco.com/collections/floating-shelves "Floating Wood Shelves | Modern & Rustic Designs | Wrydeco"
[7]: https://wrydeco.com/collections/bed-frame-with-headboard "Solid Wood Platform Beds & Headboards | Wrydeco"
[8]: https://wrydeco.com/blogs/news "News – Wrydeco"
[9]: https://developers.google.com/search/blog/2024/12/crawling-december-faceted-nav?utm_source=chatgpt.com "Crawling December: Faceted navigation  |  Google Search Central Blog  |  Google for Developers"
[10]: https://developers.google.com/search/docs/appearance/structured-data/product-variants?hl=en&utm_source=chatgpt.com "Product Variant Structured Data (ProductGroup, Product) | Google Search Central  |  Documentation  |  Google for Developers"
[11]: https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?utm_source=chatgpt.com "How To Add Merchant Listing Structured Data | Google Search Central  |  Documentation  |  Google for Developers"
