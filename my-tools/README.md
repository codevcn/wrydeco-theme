# Outside MCP

Thư mục này chứa các Model Context Protocol (MCP) servers nội bộ của dự án.

## 1. Iconify MCP (`/iconify`)
- **Mục đích**: Cung cấp công cụ lấy code SVG từ thư viện Iconify.
- **Quy tắc**: AI Agent **bắt buộc** dùng MCP này để tạo/chèn icon SVG (không tự viết code SVG). 
- **Lỗi**: Nếu MCP gặp lỗi, Agent phải tìm cách xử lý và **báo cáo ngay** cho user.
