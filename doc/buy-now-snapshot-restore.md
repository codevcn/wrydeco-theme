# Buy Now — Cart Snapshot & Restore

Thiết kế cho phương án khôi phục giỏ hàng sau khi khách dùng "Buy it now".
**Chưa triển khai** — tài liệu này mô tả logic và các case cần guard để quyết định
sau.

## 1. Vấn đề

Shopify **xoá sạch giỏ hàng của khách khi một đơn hàng hoàn tất** trong cùng
session, bất kể checkout đến từ đâu.

Đã đo thực nghiệm trên `wrydeco.myshopify.com` (2026-07-25), cả ba đường đều mất giỏ:

| Cách checkout | Tới trang checkout | Sau khi thanh toán xong |
| --- | --- | --- |
| Add to cart → `/checkout` | giỏ còn | **giỏ mất** |
| Dynamic checkout button (`payment_button`) | giỏ còn | **giỏ mất** |
| Storefront API `cartCreate` (cart token riêng) | giỏ còn | **giỏ mất** |

Kết luận: không có route checkout nào ở phía theme tránh được. Nếu muốn giữ giỏ,
phải **dựng lại** nó sau đơn hàng.

> Lưu ý: PDP (`snippets/product-buy-buttons.liquid`) đã có sẵn hành vi này từ
> trước. Nếu triển khai, nên đặt ở nơi dùng chung để sửa cho cả PDP lẫn popup
> Quick Customize, chứ không chỉ popup.

## 2. Ý tưởng

Ngay trước khi rời trang đi checkout, chụp lại nội dung giỏ vào `localStorage`.
Khi khách quay lại storefront và thấy giỏ trống, dựng lại từ snapshot.

Điểm mấu chốt khiến nó an toàn: món đang "Buy now" **chưa bao giờ nằm trong giỏ**
tại thời điểm chụp, nên snapshot không chứa nó. Khôi phục sẽ không nhân đôi món
vừa mua.

## 3. Luồng

### 3.1 Chụp (trước khi điều hướng)

```
onBuy()
  → GET /cart.js
  → nếu cart.item_count > 0:
      lưu localStorage['wd:cart-snapshot'] = {
        v: 1,                      // schema version
        savedAt: Date.now(),
        cartToken: cart.token,     // để nhận biết giỏ đã bị thay
        lines: cart.items.map(i => ({
          id: i.variant_id,
          quantity: i.quantity,
          properties: i.properties || null,
          sellingPlanId: i.selling_plan_allocation?.selling_plan?.id || null
        }))
      }
  → POST /cart/add.js (món đang mua)
  → location.href = /checkout
```

Chụp **trước** khi add món mới, nếu không snapshot sẽ chứa cả món vừa mua và khôi
phục sẽ nhân đôi nó.

### 3.2 Khôi phục (mọi lần tải trang)

```
on page load
  → đọc snapshot; không có → dừng
  → hết hạn (> TTL) → xoá, dừng
  → GET /cart.js
  → cart.item_count > 0 → xoá snapshot, dừng   // giỏ đã có hàng, không đụng vào
  → cart.token === snapshot.cartToken → dừng   // vẫn đúng giỏ cũ, chưa có đơn nào
  → POST /cart/add.js với snapshot.lines
  → xoá snapshot
  → phát event cart:updated (KHÔNG mở drawer)
```

Điều kiện `cart.item_count === 0` là guard quan trọng nhất: chỉ dựng lại khi giỏ
thực sự trống.

## 4. Các case cần guard

### 4.1 Khách bỏ ngang checkout rồi quay lại

Giỏ vẫn còn nguyên → `item_count > 0` → **không khôi phục**, xoá snapshot.
Nếu bỏ guard này sẽ nhân đôi toàn bộ giỏ.

### 4.2 Khách checkout bình thường từ giỏ (không qua Buy now)

Không có snapshot nào được tạo → không có gì xảy ra. Chỉ chụp trong `onBuy()`,
không chụp ở luồng checkout thường. **Quan trọng**: nếu chụp ở mọi checkout thì
sau khi khách mua hết giỏ, ta sẽ dựng lại đúng những món họ vừa mua.

### 4.3 Snapshot cũ từ phiên trước

TTL đề xuất **2 giờ**. Quá hạn thì xoá không khôi phục. Tránh trường hợp khách
quay lại sau 3 ngày và đột nhiên giỏ tự đầy hàng.

### 4.4 Sản phẩm hết hàng / bị xoá / đổi variant

`/cart/add.js` trả 422 cho dòng lỗi. Phải add **từng dòng một** và bỏ qua dòng
lỗi, không để một dòng hỏng làm hỏng cả lần khôi phục. Không toast lỗi cho từng
dòng — khách không yêu cầu hành động này.

### 4.5 Line-item properties

Phải giữ nguyên `properties`, đặc biệt `added_url_image` (ảnh màu tuỳ chỉnh).
Mất nó thì đơn thiếu thông tin sản xuất. Lọc bỏ các key bắt đầu bằng `_`
(private properties do app sinh ra) vì chúng có thể không add lại được.

### 4.6 Subscription / selling plan

Nếu dòng hàng có `selling_plan_allocation`, phải truyền lại `selling_plan` khi
add. Nếu không, dòng đó sẽ thành mua đứt thay vì đăng ký định kỳ. Hiện store chưa
dùng, nhưng để trong schema snapshot cho an toàn.

### 4.7 Discount code / cart attributes / cart note

`/cart/add.js` **không** khôi phục được các thứ này. Discount code đã áp cho giỏ
cũ sẽ mất. Nếu cần, phải lưu thêm `cart.attributes`, `cart.note` và gọi
`/cart/update.js` sau khi add xong. Discount code thì không có Ajax API — chấp
nhận mất, hoặc lưu và điều hướng qua `/discount/CODE`.

### 4.8 Nhiều tab

Khách mở 2 tab, bấm Buy now ở tab A, tab B vẫn thấy giỏ cũ. Sau khi đơn hoàn tất,
tab B tải lại sẽ khôi phục. Không có xung đột nghiêm trọng, nhưng nếu cả 2 tab
cùng khôi phục đồng thời sẽ nhân đôi. Guard bằng cách **xoá snapshot trước khi
add** (claim), không phải sau.

### 4.9 localStorage bị chặn

Safari private mode / trình duyệt chặn storage → `setItem` ném lỗi. Bọc try/catch
và bỏ qua im lặng: tính năng này là bonus, không được phép làm vỡ luồng mua hàng.

### 4.10 Khách đăng nhập

Shopify tự merge giỏ theo customer ở một số trường hợp. Nếu khách đăng nhập giữa
chừng và giỏ được server khôi phục, guard `item_count > 0` sẽ tự bỏ qua.

### 4.11 Khách đổi thiết bị

Không khôi phục được — `localStorage` gắn với trình duyệt. Đây là giới hạn cứng,
phải chấp nhận.

### 4.12 Không mở cart drawer khi khôi phục

Event `cart:updated` hiện đang được phát kèm `{ open: true }` ở nhiều nơi và sẽ
bật drawer. Khi khôi phục phải phát **không kèm** `open`, nếu không khách vừa vào
trang đã bị đập drawer vào mặt mà không hiểu vì sao.

## 5. Điểm đặt code

- Logic chụp: `snippets/quick-customize.liquid` (`onBuy`) và
  `snippets/product-buy-buttons.liquid` (nút Buy It Now của PDP).
- Logic khôi phục: một snippet mới dùng chung, render trong `layout/theme.liquid`
  để chạy trên mọi trang.

## 6. Đánh giá

**Được:** giải quyết đúng phàn nàn, không cần token hay app, sửa cho cả PDP.

**Mất:** thêm 1 request `/cart.js` mỗi lần tải trang (có thể hoãn tới `idle`),
code thao tác giỏ hàng chạy toàn site nên bug ở đây ảnh hưởng rộng, và không bao
giờ đúng 100% (đổi thiết bị, discount code, storage bị chặn).

**Chưa quyết.** Hiện tại Buy Now đang chạy hành vi phổ biến: add vào giỏ rồi
checkout cả giỏ, có chú thích nói rõ điều đó ngay trên nút.
