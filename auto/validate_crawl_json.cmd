@echo off
setlocal

pushd "%~dp0"
python "%~dp0validate_crawl_json.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
