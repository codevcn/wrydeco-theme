# Discount Brief: Khai trương cửa hàng Sale Off

## 1. Tổng quan

| Trường                | Giá trị                                   |
| --------------------- | ----------------------------------------- |
| **Tên chương trình**  | Khai trương cửa hàng Sale Off             |
| **Trạng thái**        | ACTIVE                                    |
| **Loại discount**     | Automatic (tự động áp dụng, không cần mã) |
| **Kiểu discount**     | `DiscountAutomaticBasic`                  |
| **Đối tượng áp dụng** | Tất cả khách hàng                         |

---

## 2. Giá trị giảm giá

| Trường                | Giá trị                        |
| --------------------- | ------------------------------ |
| **Mức giảm**          | 50%                            |
| **Dạng giảm**         | Percentage (`percentage: 0.5`) |
| **Áp dụng cho**       | Collection cụ thể              |
| **One-time purchase** | ✅ Có                          |
| **Subscription**      | ❌ Không                       |

---

## 3. Điều kiện tối thiểu

| Trường                | Giá trị          |
| --------------------- | ---------------- |
| **Loại điều kiện**    | Minimum subtotal |
| **Giá trị tối thiểu** | $100.00 USD      |

---

## 4. Thời gian hiệu lực

| Trường            | Giá trị (UTC)        |
| ----------------- | -------------------- |
| **Bắt đầu**       | 2026-06-27T14:02:06Z |
| **Kết thúc**      | 2026-07-09T03:59:59Z |
| **Ngày tạo**      | 2026-06-27T14:20:03Z |
| **Ngày cập nhật** | 2026-06-27T14:20:03Z |

---

## 5. Giới hạn sử dụng

| Trường                    | Giá trị                            |
| ------------------------- | ---------------------------------- |
| **Tổng lượt dùng**        | 0 (chưa có đơn nào áp dụng)        |
| **Recurring cycle limit** | 1 (mỗi đơn hàng chỉ áp dụng 1 lần) |

---

## 6. Quy tắc kết hợp (Combining)

| Loại discount      | Kết hợp được? |
| ------------------ | ------------- |
| Order discounts    | ❌ Không      |
| Product discounts  | ❌ Không      |
| Shipping discounts | ✅ Có         |

---

## 7. Target Collection

| Trường                      | Giá trị                                 |
| --------------------------- | --------------------------------------- |
| **Tên collection**          | A Home Shared with Life                 |
| **Collection GID**          | `gid://shopify/Collection/475413217337` |
| **Collection ID (numeric)** | `475413217337`                          |

---

## 8. GraphQL API — Thông tin truy xuất

### Node IDs

```
DiscountNode GID:         gid://shopify/DiscountAutomaticNode/1258939416633
DiscountNode ID (numeric): 1258939416633
Target Collection GID:    gid://shopify/Collection/475413217337
```

### Query lấy thông tin discount

```graphql
query GetDiscount {
  discountNode(id: "gid://shopify/DiscountAutomaticNode/1258939416633") {
    id
    discount {
      ... on DiscountAutomaticBasic {
        title
        status
        startsAt
        endsAt
        usageCount
        recurringCycleLimit
        customerGets {
          value {
            ... on DiscountPercentage {
              percentage
            }
          }
          items {
            ... on DiscountCollections {
              collections(first: 10) {
                nodes {
                  id
                  title
                  handle
                }
              }
            }
          }
        }
        minimumRequirement {
          ... on DiscountMinimumSubtotal {
            greaterThanOrEqualToSubtotal {
              amount
              currencyCode
            }
          }
        }
        combinesWith {
          orderDiscounts
          productDiscounts
          shippingDiscounts
        }
      }
    }
  }
}
```

### Query lấy thông tin collection target

```graphql
query GetTargetCollection {
  collection(id: "gid://shopify/Collection/475413217337") {
    id
    title
    handle
    productsCount {
      count
    }
    products(first: 50) {
      nodes {
        id
        title
        status
      }
    }
  }
}
```

### REST API endpoint (nếu dùng REST)

```
GET /admin/api/2024-01/collections/475413217337.json
```

---

## 9. Ghi chú cho AI / Developer

- Discount này là **automatic** → không cần `discountCodes`, dùng `discountAutomaticNodes` để list.
- Để list tất cả automatic discounts: dùng query `discountAutomaticNodes(first: 10)`.
- `recurringCycleLimit: 1` → mỗi subscription cycle chỉ áp dụng 1 lần (dù đây không áp dụng cho subscription).
- Discount chỉ kết hợp được với **shipping discounts**, cần lưu ý khi tính toán giỏ hàng.
- Thời gian kết thúc `2026-07-09T03:59:59Z` tương đương **23:59:59 ngày 8/7/2026 theo giờ EDT (UTC-4)**.
