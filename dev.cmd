@echo off
echo.
echo ===================================================
echo CHU Y: Shopify CLI dang yeu cau mat khau cua hang.
echo Ban co the lay mat khau nay trong trang quan tri Shopify:
echo Online Store -^> Preferences -^> Password protection.
echo ===================================================
echo.
REM Thay doi mat khau mac dinh o bien DEFAULT_STORE_PASSWORD
set DEFAULT_STORE_PASSWORD=123456

echo Tu dong su dung mat khau: %DEFAULT_STORE_PASSWORD%
set STORE_PASSWORD=%DEFAULT_STORE_PASSWORD%
python dev_wrapper.py --store-password=%STORE_PASSWORD% %*