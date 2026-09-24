@echo off
setlocal

pushd "%~dp0"
python "%~dp0get_access_token.py"
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
