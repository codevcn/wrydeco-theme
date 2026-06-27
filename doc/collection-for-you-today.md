# Collection Brief: For you, today

## 1. Tổng quan

| Trường          | Giá trị                                 |
| --------------- | --------------------------------------- |
| **Title**       | For you, today                          |
| **Handle**      | `for-you-today`                         |
| **ID (GID)**    | `gid://shopify/Collection/475527905337` |
| **Numeric ID**  | `475527905337`                          |
| **Type**        | Smart Collection (Automated)            |
| **Description** | Products most searched for every day.   |
| **Updated At**  | 2026-06-27T12:04:59Z                    |

---

## 2. Cấu hình hiển thị

| Trường              | Giá trị         |
| ------------------- | --------------- |
| **Sort Order**      | `MOST_RELEVANT` |
| **Template Suffix** | _(mặc định)_    |
| **Image**           | _(chưa có)_     |

---

## 3. SEO

| Trường              | Giá trị      |
| ------------------- | ------------ |
| **SEO Title**       | _(chưa đặt)_ |
| **SEO Description** | _(chưa đặt)_ |

---

## 4. Smart Collection Rules

### Logic áp dụng

- **`appliedDisjunctively`**: `false`  
  → Các điều kiện kết hợp bằng **AND** (sản phẩm phải thỏa **tất cả** điều kiện).

### Danh sách điều kiện

| #   | Column | Relation | Condition |
| --- | ------ | -------- | --------- |
| 1   | `TAG`  | `EQUALS` | `Modern`  |

> **Giải thích:** Collection tự động bao gồm tất cả sản phẩm có tag chính xác là `Modern`.

---

## 5. Metafields

_(Hiện tại không có metafield nào được gán cho collection này.)_

---

## 6. GraphQL — Truy xuất collection

### 6.1. Query lấy thông tin collection theo handle

```graphql
query GetCollectionByHandle($handle: String!) {
  collectionByHandle(handle: $handle) {
    id
    title
    handle
    description
    descriptionHtml
    updatedAt
    sortOrder
    templateSuffix
    seo {
      title
      description
    }
    image {
      url
      altText
      width
      height
    }
    ruleSet {
      appliedDisjunctively
      rules {
        column
        relation
        condition
      }
    }
    metafields(first: 20) {
      edges {
        node {
          namespace
          key
          value
          type
        }
      }
    }
  }
}
```

**Variables:**

```json
{
  "handle": "for-you-today"
}
```

---

### 6.2. Query lấy thông tin collection theo ID

```graphql
query GetCollectionById($id: ID!) {
  collection(id: $id) {
    id
    title
    handle
    description
    descriptionHtml
    updatedAt
    sortOrder
    templateSuffix
    seo {
      title
      description
    }
    image {
      url
      altText
      width
      height
    }
    ruleSet {
      appliedDisjunctively
      rules {
        column
        relation
        condition
      }
    }
    metafields(first: 20) {
      edges {
        node {
          namespace
          key
          value
          type
        }
      }
    }
  }
}
```

**Variables:**

```json
{
  "id": "gid://shopify/Collection/475527905337"
}
```

---

### 6.3. REST API (nếu cần)

```
GET /admin/api/2024-01/collections/475527905337.json
```

---

## 7. Storefront API — Truy xuất collection (public)

```graphql
query GetCollectionStorefront($handle: String!) {
  collection(handle: $handle) {
    id
    title
    handle
    description
    updatedAt
    image {
      url
      altText
    }
    metafields(identifiers: []) {
      namespace
      key
      value
      type
    }
  }
}
```

**Variables:**

```json
{
  "handle": "for-you-today"
}
```

> ⚠️ Storefront API không trả về `ruleSet` — chỉ Admin API mới có.

---

## 8. Ghi chú kỹ thuật

- **Smart collection** được Shopify tự động cập nhật sản phẩm dựa trên rules — không cần thêm/xóa sản phẩm thủ công.
- Rule hiện tại dùng `TAG EQUALS Modern` — nếu tag thay đổi (viết hoa/thường), sản phẩm sẽ bị loại khỏi collection.
- `sortOrder: MOST_RELEVANT` là sort mặc định của Shopify, có thể override khi query Storefront API bằng `sortKey`.
- Không có metafield → không cần xử lý thêm logic metafield khi parse response.
- `appliedDisjunctively: false` → logic AND, chỉ cần 1 rule nên không ảnh hưởng thực tế.
