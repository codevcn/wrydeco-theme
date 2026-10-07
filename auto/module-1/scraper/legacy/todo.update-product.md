> Nếu có bất cứ mâu thuẫn dữ liệu hay lỗi nào xảy ra trong quá trình update sản phẩm, hãy dừng toàn bộ quá trình cập nhật và thông báo cho tôi.

- Đọc file `./config.update-product.json` để biết chính xác các thông tin cần update lên sản phẩm.
- Dùng access token được mô tả trong file `./access-token.md` để truy cập store và cập nhật sản phẩm trong store theo thông tin đã đọc được trong file json.
- Chạy file `./clean.cmd` để dọn dẹp.
- Cuối cùng, hãy chạy file `./toast.cmd` để hiển thị thông báo hoàn tất.
