@echo off
setlocal

pushd "%~dp0"
python "%~dp0import_csv_to_store.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
