@echo off
setlocal

pushd "%~dp0"
python "%~dp0update_product_photos.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
