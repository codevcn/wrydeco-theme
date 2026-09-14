# Shopify Admin API Token (Context for AI Agent)

## 1. Config (dmin/.env)
- SHOPIFY_SHOP: Store domain (e.g. 6-theme-test.myshopify.com).
- SHOPIFY_ADMIN_TOKEN: Token Admin API hiện tại (shpat_... hoặc shpua_...).
- SHOPIFY_API_VERSION: API version (e.g. 2026-07).
- SHOPIFY_CLIENT_ID & SHOPIFY_CLIENT_SECRET: OAuth credentials dùng tự cấp mới token.

## 2. Lấy / Làm mới Access Token
Chạy lệnh từ root workspace:
`ash
python admin/get_access_token.py
`
*(hoặc dmin\\get_access_token.cmd trên Windows)*

**Cơ chế:**
- Tự động test SHOPIFY_ADMIN_TOKEN qua GET /admin/api/{version}/shop.json.
- Nếu token lỗi / hết hạn (401), tự fallback dùng CLIENT_ID + CLIENT_SECRET gọi POST /admin/oauth/access_token (grant_type: client_credentials) để cấp token mới.
- In token còn sống và danh sách Scope ra stdout.

## 3. Cách dùng trong API Requests
> **Bắt buộc/Ưu tiên: Dùng GraphQL Admin API** (chuẩn Shopify hiện đại, tối ưu rate limit và hỗ trợ đầy đủ Metafields / Products).

- **GraphQL Endpoint (Primary):** https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/graphql.json
- **Headers:**
  - X-Shopify-Access-Token: <token>
  - Content-Type: application/json
- **REST Base URL (Legacy / Fallback):** https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/

## 4. Dọn dẹp thư mục admin
`ash
python admin/clean.py
`
*(Xóa các file tạm phát sinh trong dmin/, giữ nguyên .env, ccess-token.md, các script gốc).*
