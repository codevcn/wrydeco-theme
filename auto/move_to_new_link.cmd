@echo off
setlocal

REM Paste the new Amazon product URL here before running this script.
set "NEW_AMAZON_URL=https://www.amazon.com/dp/B0H7H3HCTJ"

pushd "%~dp0"
python "%~dp0move_to_new_link.py" "%NEW_AMAZON_URL%" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
