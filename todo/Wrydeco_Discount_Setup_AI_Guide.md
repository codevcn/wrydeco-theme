# Wrydeco — AI Runbook: Tạo bộ 10 Discount Code theo mức chi tiêu

## 1. Mục tiêu

Thực hiện trực tiếp trên Shopify store **Wrydeco** bằng thông tin truy cập được lưu cục bộ tại:

```text
doc\alias\access-token.md
```

Trên môi trường POSIX/Linux, path tương đương có thể là:

```text
doc/alias/access-token.md
```

Nhiệm vụ là tạo hoặc đồng bộ 10 discount code cố định sau:

| Code | Discount | Minimum order subtotal |
|---|---:|---:|
| `WRY100` | $100 | $900 |
| `WRY200` | $200 | $1,900 |
| `WRY300` | $300 | $2,900 |
| `WRY400` | $400 | $3,900 |
| `WRY500` | $500 | $4,900 |
| `WRY600` | $600 | $5,900 |
| `WRY700` | $700 | $6,900 |
| `WRY800` | $800 | $7,900 |
| `WRY900` | $900 | $8,900 |
| `WRY1000` | $1,000 | $9,900 |

Ví dụ kỳ vọng:

- Cart `$5,300` đủ điều kiện cho `WRY500`, nhưng chưa đủ `WRY600`.
- Cart `$8,500` đủ điều kiện cho `WRY800`, nhưng chưa đủ `WRY900`.
- Cart `$900` dùng được `WRY100`.
- Cart `$899.99` không dùng được `WRY100`.

---

## 2. Cấu hình bắt buộc cho cả 10 mã

Tất cả các mã phải dùng cùng một cấu hình, chỉ khác **discount amount** và **minimum subtotal**.

### Discount method

- Loại: **Discount code**.
- Không tạo Automatic Discount.
- Khách hàng nhập code tại cart/checkout để nhận ưu đãi.

### Discount type

- **Amount off order**.
- Giá trị giảm: **Fixed amount**.
- Fixed amount chỉ trừ **một lần trên toàn đơn**, không trừ lặp lại trên từng sản phẩm.

### Applies to

- Áp dụng cho **tất cả sản phẩm** trong Wrydeco.
- Áp dụng cho **tất cả khách hàng**.

### Minimum purchase requirement

- Dùng **minimum purchase amount / minimum subtotal** theo bảng ở mục 1.
- Không dùng minimum quantity.

### Discount combinations

Cấu hình hiện tại phải là **không cộng dồn với discount khác**:

```text
Order discounts:    false
Product discounts:  false
Shipping discounts: false
```

Mục tiêu quan trọng nhất là 10 mã `WRY100` → `WRY1000` **không thể stack với nhau**. Việc tắt toàn bộ ba loại combination cũng ngăn việc cộng thêm promotion khác ngoài bộ mã này, tránh giảm giá vượt mức dự kiến.

### Usage / customer limits

Leader chưa yêu cầu giới hạn số lần sử dụng, vì vậy:

- Không đặt global usage limit.
- Không bật “limit to one use per customer”.

### Thời gian hiệu lực

- Bắt đầu: **ngay khi tạo/cập nhật**.
- Không đặt ngày hết hạn, trừ khi user đưa yêu cầu mới.

---

## 3. Bảo mật access token

`doc\alias\access-token.md` là nguồn credential cục bộ cho task này.

AI phải tuân thủ các nguyên tắc sau:

1. Đọc file ở local runtime để lấy shop domain và Shopify Admin API access token.
2. **Không in access token ra terminal, response, log, markdown report hoặc commit.**
3. Không copy token sang file mới.
4. Không commit `access-token.md` vào Git nếu file chưa được ignore.
5. Khi hiển thị request để debug, phải redact header thành:

```text
X-Shopify-Access-Token: [REDACTED]
```

6. Nếu file credential không tồn tại, thiếu token hoặc token không hợp lệ: **STOP**, không đoán credential.

---

## 4. Shopify API cần dùng

Ưu tiên **Shopify Admin GraphQL API**.

API version cho task này:

```text
2026-07
```

Endpoint mẫu:

```text
https://{SHOP_MYSHOPIFY_DOMAIN}/admin/api/2026-07/graphql.json
```

Headers runtime:

```text
Content-Type: application/json
X-Shopify-Access-Token: <TOKEN_ĐỌC_TỪ_access-token.md>
```

Token cần có quyền phù hợp để đọc/ghi discount. Nếu API trả lỗi permission/scope đối với discount, dừng task và báo rõ thiếu quyền thay vì thử bypass.

---

## 5. Preflight — bắt buộc làm trước khi ghi dữ liệu

### Step 5.1 — Đọc credential

Đọc `doc\alias\access-token.md` và xác định tối thiểu:

- Shopify store domain, ưu tiên domain dạng `*.myshopify.com`.
- Admin API access token.

Không log token.

### Step 5.2 — Xác minh đúng store

Gửi một GraphQL query read-only để lấy thông tin shop.

Ví dụ:

```graphql
query VerifyShop {
  shop {
    name
    myshopifyDomain
    currencyCode
  }
}
```

Chỉ tiếp tục khi xác định đây là store **Wrydeco**.

Đồng thời xác minh currency của store là **USD** vì toàn bộ amount trong tài liệu này là USD.

Nếu domain/store không khớp Wrydeco hoặc currency không phải USD: **STOP ngay**, không tạo discount.

### Step 5.3 — Kiểm tra quyền discount

Task cần tối thiểu khả năng:

- đọc discount hiện có để tránh duplicate/collision;
- tạo/cập nhật discount.

Nếu query discount bị từ chối do scope, báo lỗi permission và dừng.

---

## 6. Phải chạy theo kiểu idempotent

AI **không được tạo mù 10 mã mới**.

Trước mỗi code, dùng query `codeDiscountNodeByCode` để kiểm tra code đã tồn tại hay chưa.

Logic bắt buộc:

```text
Nếu code chưa tồn tại:
    CREATE bằng discountCodeBasicCreate

Nếu code đã tồn tại và là DiscountCodeBasic:
    UPDATE về đúng cấu hình trong tài liệu này bằng discountCodeBasicUpdate

Nếu code đã tồn tại nhưng là loại khác
(BXGY, Free Shipping, App discount, ...):
    KHÔNG xóa
    KHÔNG overwrite mù
    STOP code đó và báo collision
```

Việc rerun tài liệu này phải an toàn: lần chạy sau chỉ đồng bộ lại cấu hình, không tạo duplicate.

---

## 7. GraphQL mutation để tạo discount

Dùng mutation:

```graphql
mutation CreateWrydecoDiscount($input: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $input) {
    codeDiscountNode {
      id
      codeDiscount {
        ... on DiscountCodeBasic {
          title
          startsAt
          endsAt
          appliesOncePerCustomer
          combinesWith {
            orderDiscounts
            productDiscounts
            shippingDiscounts
          }
          minimumRequirement {
            ... on DiscountMinimumSubtotal {
              greaterThanOrEqualToSubtotal {
                amount
                currencyCode
              }
            }
          }
          customerGets {
            value {
              ... on DiscountAmount {
                amount {
                  amount
                  currencyCode
                }
                appliesOnEachItem
              }
            }
          }
          codes(first: 10) {
            nodes {
              code
            }
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

### Input template

Với mỗi item trong bảng discount, build input theo template sau:

```json
{
  "title": "Wrydeco $100 Off $900+",
  "code": "WRY100",
  "startsAt": "<CURRENT_ISO_8601_TIME>",
  "endsAt": null,
  "context": {
    "all": true
  },
  "customerGets": {
    "value": {
      "discountAmount": {
        "amount": "100.00",
        "appliesOnEachItem": false
      }
    },
    "items": {
      "all": true
    }
  },
  "minimumRequirement": {
    "subtotal": {
      "greaterThanOrEqualToSubtotal": "900.00"
    }
  },
  "combinesWith": {
    "orderDiscounts": false,
    "productDiscounts": false,
    "shippingDiscounts": false
  },
  "appliesOncePerCustomer": false,
  "usageLimit": null
}
```

Thay `title`, `code`, fixed amount và minimum subtotal theo bảng ở mục 1.

**Quan trọng:** `appliesOnEachItem` phải là `false`. Nếu đặt `true`, fixed amount có thể bị áp dụng theo từng item và không còn đúng mục tiêu “Amount off order”.

---

## 8. GraphQL mutation để cập nhật code đã tồn tại

Nếu code đã tồn tại và đúng loại `DiscountCodeBasic`, dùng:

```graphql
mutation UpdateWrydecoDiscount($id: ID!, $input: DiscountCodeBasicInput!) {
  discountCodeBasicUpdate(id: $id, basicCodeDiscount: $input) {
    codeDiscountNode {
      id
    }
    userErrors {
      field
      message
    }
  }
}
```

Input phải đồng bộ về đúng cấu hình mục 2 và đúng tier mục 1.

Không xóa code chỉ để tạo lại nếu update được.

---

## 9. Dataset chuẩn để AI dùng khi loop

Có thể biểu diễn cấu hình như sau:

```json
[
  {"code":"WRY100",  "discount":"100.00",  "minimum":"900.00",  "title":"Wrydeco $100 Off $900+"},
  {"code":"WRY200",  "discount":"200.00",  "minimum":"1900.00", "title":"Wrydeco $200 Off $1,900+"},
  {"code":"WRY300",  "discount":"300.00",  "minimum":"2900.00", "title":"Wrydeco $300 Off $2,900+"},
  {"code":"WRY400",  "discount":"400.00",  "minimum":"3900.00", "title":"Wrydeco $400 Off $3,900+"},
  {"code":"WRY500",  "discount":"500.00",  "minimum":"4900.00", "title":"Wrydeco $500 Off $4,900+"},
  {"code":"WRY600",  "discount":"600.00",  "minimum":"5900.00", "title":"Wrydeco $600 Off $5,900+"},
  {"code":"WRY700",  "discount":"700.00",  "minimum":"6900.00", "title":"Wrydeco $700 Off $6,900+"},
  {"code":"WRY800",  "discount":"800.00",  "minimum":"7900.00", "title":"Wrydeco $800 Off $7,900+"},
  {"code":"WRY900",  "discount":"900.00",  "minimum":"8900.00", "title":"Wrydeco $900 Off $8,900+"},
  {"code":"WRY1000", "discount":"1000.00", "minimum":"9900.00", "title":"Wrydeco $1,000 Off $9,900+"}
]
```

Không tự thay đổi các threshold trên.

---

## 10. Trình tự thực thi bắt buộc

Thực hiện theo đúng thứ tự:

1. Đọc credential từ `doc\alias\access-token.md`.
2. Verify domain/store name và USD currency.
3. Verify API access tới discount.
4. Load dataset 10 tiers.
5. Với từng code:
   - query code hiện tại;
   - create nếu chưa tồn tại;
   - update nếu tồn tại và là `DiscountCodeBasic`;
   - check `userErrors` ngay sau mutation.
6. Không tiếp tục im lặng nếu mutation có lỗi.
7. Sau khi xử lý xong, query lại cả 10 code để verify server state.
8. Chỉ báo “hoàn tất” khi verify đủ 10/10 mã đúng cấu hình.

---

## 11. Verification checklist cho từng code

Mỗi code chỉ được đánh dấu PASS khi tất cả điều kiện sau đúng:

- Code chính xác, không typo.
- Discount là fixed amount.
- Fixed amount đúng tier.
- `appliesOnEachItem = false`.
- Applies to all items/products.
- Customer context = all customers.
- Minimum requirement là subtotal.
- Minimum subtotal đúng tier.
- `orderDiscounts = false`.
- `productDiscounts = false`.
- `shippingDiscounts = false`.
- Không có end date.
- Không có global usage limit.
- Không bật one-use-per-customer.
- Discount đang active hoặc bắt đầu hiệu lực ngay.

Expected count:

```text
PASS: 10
FAIL: 0
```

---

## 12. Kiểm tra logic tier sau khi setup

Ít nhất xác minh bằng cấu hình/API rằng các boundary sau đúng:

| Cart subtotal | Code kỳ vọng cao nhất đủ điều kiện |
|---:|---|
| $899.99 | Không có code nào |
| $900.00 | `WRY100` |
| $1,900.00 | `WRY200` |
| $2,900.00 | `WRY300` |
| $4,900.00 | `WRY500` |
| $5,300.00 | `WRY500` |
| $7,900.00 | `WRY800` |
| $8,500.00 | `WRY800` |
| $9,900.00 | `WRY1000` |

Không cần tạo order thật chỉ để test nếu việc đó có thể phát sinh giao dịch. Verification bằng API/config là đủ, trừ khi user yêu cầu checkout test riêng.

---

## 13. Xử lý lỗi và an toàn dữ liệu

### Nếu một mutation lỗi

- Đọc `userErrors.field` và `userErrors.message`.
- Không báo thành công cho code đó.
- Không đoán field/value mới rồi tiếp tục ghi bừa.
- Sửa request nếu lỗi rõ ràng và không làm thay đổi business rule.
- Nếu lỗi liên quan scope, credential, store identity hoặc schema không chắc chắn: STOP và báo user.

### Nếu task dừng giữa chừng

Không rollback bằng cách xóa những code đã tạo thành công.

Thay vào đó:

- báo rõ code nào `CREATED`, `UPDATED`, `UNCHANGED`, `FAILED`;
- sau khi lỗi được sửa, rerun runbook;
- vì workflow là idempotent, lần chạy tiếp theo phải hoàn thiện phần còn thiếu mà không duplicate.

### Không được sửa các discount ngoài phạm vi

AI chỉ được phép tạo/cập nhật chính xác 10 code:

```text
WRY100
WRY200
WRY300
WRY400
WRY500
WRY600
WRY700
WRY800
WRY900
WRY1000
```

Không xóa, deactivate, rename hoặc chỉnh sửa discount khác của store.

---

## 14. Báo cáo cuối cùng

Sau khi chạy xong, trả về bảng ngắn gọn dạng:

```text
Store: Wrydeco
Currency: USD
API version: 2026-07

CODE          STATUS     DISCOUNT   MINIMUM
WRY100    CREATED    $100       $900
WRY200    UPDATED    $200       $1,900
...
WRY1000   CREATED    $1,000     $9,900

Verification: 10/10 PASS
Combination: disabled for order/product/shipping discounts
Applies to: all products / all customers
Expiry: none
```

Không bao giờ đưa access token vào report.

---

## 15. Definition of Done

Task chỉ hoàn thành khi:

1. Đúng store Wrydeco.
2. Đủ chính xác 10 code theo bảng.
3. Mỗi code là fixed amount off order.
4. Minimum subtotal đúng từng tier.
5. Applies to all products và all customers.
6. Không cộng dồn với discount khác.
7. Không expiry.
8. Không thay đổi discount ngoài 10 code mục tiêu.
9. API verification cuối cùng trả về **10/10 PASS**.
10. Credential không bị lộ trong output/log/report.
