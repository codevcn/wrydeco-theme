@echo off
setlocal

pushd "%~dp0"
python "%~dp0delete_files_content.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
