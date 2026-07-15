# Dưới đây là logic cho voucher WRYDECO10

```text
Mã giảm giá: WRYDECO10
Mức giảm: 10%
Giảm tối đa: $100 USD
Phạm vi: Toàn bộ sản phẩm
Không yêu cầu giá trị đơn tối thiểu
```

Shopify Function sẽ tính số tiền giảm theo từng giỏ hàng rồi trả về một `fixedAmount`. Discount được áp dụng lên toàn bộ `orderSubtotal`; để `excludedCartLineIds: []` nghĩa là không chủ động loại trừ cart line nào. ([Shopify][1])

## 1. Công thức

```text
discountAmount = min(orderSubtotal × 10%, $100)
```

Ví dụ:

| Giá trị sản phẩm |    10% | Giảm thực tế |
| ---------------: | -----: | -----------: |
|             $100 |    $10 |          $10 |
|             $500 |    $50 |          $50 |
|             $999 | $99.90 |       $99.90 |
|           $1,000 |   $100 |         $100 |
|           $1,500 |   $150 |         $100 |
|           $5,000 |   $500 |         $100 |

## 2. Logic flow

```text
Khách thêm bất kỳ sản phẩm nào vào giỏ hàng
                    ↓
Khách nhập mã WRYDECO10
                    ↓
Shopify gọi Discount Function
                    ↓
Function kiểm tra discount có class ORDER hay không
                    ↓
Đọc subtotal của toàn bộ sản phẩm trong giỏ hàng
                    ↓
Tính 10% × subtotal
                    ↓
So sánh kết quả với $100
                    ↓
Lấy giá trị nhỏ hơn:
min(subtotal × 10%, $100)
                    ↓
Trả về fixedAmount
                    ↓
Áp dụng discount lên toàn bộ order subtotal
```

Function target `cart.lines.discounts.generate.run` có thể tạo order discount, product discount và shipping discount. Trường hợp này chỉ cần tạo `orderDiscountsAdd`. ([Shopify][1])

---

# 3. Input query

Mở file:

```text
extensions/wrydeco-capped-discount/src/cart_lines_discounts_generate_run.graphql
```

Thay bằng:

```graphql
query CartInput {
  cart {
    cost {
      subtotalAmount {
        amount
        currencyCode
      }
    }
  }

  discount {
    discountClasses
  }
}
```

Query này đọc trực tiếp subtotal của toàn bộ giỏ hàng, không cần lấy collection, product ID, tag hoặc metafield vì voucher áp dụng cho tất cả sản phẩm.

---

# 4. Function JavaScript hoàn chỉnh

Mở file:

```text
extensions/wrydeco-capped-discount/src/cart_lines_discounts_generate_run.js
```

Thay bằng:

```javascript
import { DiscountClass, OrderDiscountSelectionStrategy } from "../generated/api";

/**
 * Voucher configuration
 */
const DISCOUNT_RATE = 0.1; // 10%
const MAX_DISCOUNT_USD = 100; // Tối đa $100 USD

/**
 * Công thức:
 * discountAmount = min(orderSubtotal * 10%, $100)
 *
 * Áp dụng cho toàn bộ order subtotal.
 *
 * @param {import("../generated/api").CartInput} input
 * @returns {import("../generated/api").CartLinesDiscountsGenerateRunResult}
 */
export function cartLinesDiscountsGenerateRun(input) {
  const supportsOrderDiscount = input.discount.discountClasses.includes(DiscountClass.Order);

  if (!supportsOrderDiscount) {
    return {
      operations: [],
    };
  }

  const subtotalMoney = input.cart?.cost?.subtotalAmount;

  if (!subtotalMoney) {
    return {
      operations: [],
    };
  }

  const subtotal = Number(subtotalMoney.amount);
  const currencyCode = subtotalMoney.currencyCode;

  if (!Number.isFinite(subtotal) || subtotal <= 0) {
    return {
      operations: [],
    };
  }

  /**
   * Vì mức trần được yêu cầu cụ thể là $100 USD,
   * không áp dụng Function này cho checkout dùng currency khác.
   */
  if (currencyCode !== "USD") {
    return {
      operations: [],
    };
  }

  const percentageDiscount = subtotal * DISCOUNT_RATE;

  const cappedDiscount = Math.min(percentageDiscount, MAX_DISCOUNT_USD);

  /**
   * Làm tròn tiền USD đến 2 chữ số thập phân.
   */
  const discountAmount = Math.round((cappedDiscount + Number.EPSILON) * 100) / 100;

  if (discountAmount <= 0) {
    return {
      operations: [],
    };
  }

  return {
    operations: [
      {
        orderDiscountsAdd: {
          candidates: [
            {
              message: "10% off, up to $100",
              targets: [
                {
                  orderSubtotal: {
                    /**
                     * Không loại trừ cart line nào:
                     * voucher áp dụng cho tất cả sản phẩm.
                     */
                    excludedCartLineIds: [],
                  },
                },
              ],
              value: {
                /**
                 * Function tự tính 10% rồi trả về số tiền
                 * cố định tương ứng với giỏ hàng hiện tại.
                 */
                fixedAmount: {
                  amount: discountAmount.toFixed(2),
                },
              },
            },
          ],
          selectionStrategy: OrderDiscountSelectionStrategy.First,
        },
      },
    ],
  };
}
```

Shopify định nghĩa `fixedAmount.amount` bằng currency của cart. Vì yêu cầu là tối đa **$100 USD**, đoạn code trên chỉ kích hoạt khi checkout đang dùng USD. ([Shopify][1])

## Điểm xác định “all products”

Phần này là quan trọng nhất:

```javascript
targets: [
  {
    orderSubtotal: {
      excludedCartLineIds: [],
    },
  },
],
```

Có nghĩa là:

```text
Target: toàn bộ order subtotal
Excluded cart lines: không có
Collection filter: không có
Product filter: không có
Product tag filter: không có
```

---

# 5. Tạo mã voucher `WRYDECO10`

Sau khi Function hoạt động trong `shopify app dev` hoặc đã deploy, chạy mutation sau trong GraphiQL của app:

```graphql
mutation CreateWrydeco10Discount {
  discountCodeAppCreate(
    codeAppDiscount: {
      title: "WRYDECO10 — 10% off up to $100"
      code: "WRYDECO10"
      functionHandle: "wrydeco-capped-discount"
      discountClasses: [ORDER]
      context: { all: ALL }
      appliesOncePerCustomer: false
      combinesWith: { orderDiscounts: false, productDiscounts: false, shippingDiscounts: true }
      startsAt: "2026-07-15T00:00:00Z"
    }
  ) {
    codeAppDiscount {
      discountId
      title
      status

      codes(first: 10) {
        nodes {
          code
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

`discountCodeAppCreate` là mutation dành cho discount code có logic được cung cấp bởi Shopify Function và yêu cầu scope `write_discounts`. ([Shopify][2])

## Ý nghĩa cấu hình

```graphql
discountClasses: [ORDER]
```

Voucher giảm trên subtotal của đơn hàng.

```graphql
context: {
  all: ALL
}
```

Mọi khách hàng đều có thể sử dụng.

```graphql
appliesOncePerCustomer: false
```

Một khách hàng có thể sử dụng nhiều lần.

```graphql
combinesWith: {
  orderDiscounts: false
  productDiscounts: false
  shippingDiscounts: true
}
```

Kết quả:

```text
Không kết hợp với order discount khác
Không kết hợp với product discount khác
Có thể kết hợp với free shipping hoặc shipping discount
```

---

# 6. Test voucher

Sau khi tạo mã, kiểm tra ít nhất các trường hợp sau:

```text
Cart $200
10% = $20
Discount = $20
```

```text
Cart $750
10% = $75
Discount = $75
```

```text
Cart $1,000
10% = $100
Discount = $100
```

```text
Cart $1,200
10% = $120
Discount = $100
```

```text
Cart $3,000
10% = $300
Discount = $100
```

Kiểm tra với nhiều sản phẩm và nhiều collection khác nhau để xác nhận tổng subtotal vẫn được tính chung:

```text
Bookshelf: $600
Wall Shelf: $250
Wooden Lamp: $150
──────────────────
Subtotal: $1,000
10%: $100
Discount thực tế: $100
```

Lưu ý về triển khai production vẫn giữ nguyên: mọi Shopify plan có thể dùng public app chứa Functions, nhưng custom app chứa Shopify Functions chỉ dùng được trên Shopify Plus.
