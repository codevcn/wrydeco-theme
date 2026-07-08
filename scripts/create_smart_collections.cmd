@echo off
setlocal

echo This will create enabled smart collections on the real Shopify store.
echo Type CREATE to continue.
set /p CONFIRM=Confirm: 

if /I not "%CONFIRM%"=="CREATE" (
  echo Cancelled.
  exit /b 1
)

pushd "%~dp0"
python "%~dp0create_smart_collections.py" --run %*
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
