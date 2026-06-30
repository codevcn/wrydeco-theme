@echo off
echo.
echo ===================================================
echo CHU Y: Shopify CLI dang yeu cau mat khau cua hang.
echo Ban co the lay mat khau nay trong trang quan tri Shopify:
echo Online Store -^> Preferences -^> Password protection.
echo ===================================================
echo.
set /p STORE_PASSWORD="Vui long nhap mat khau cua hang (Store password): "
python dev_wrapper.py --store-password=%STORE_PASSWORD% %*