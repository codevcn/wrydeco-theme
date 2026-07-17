@echo off
setlocal

set "VERSION=2.1.0"
set "ZIP_NAME=Skeleton-%VERSION%-upload.zip"

if exist "%ZIP_NAME%" del /f /q "%ZIP_NAME%"

tar -a -cf "%ZIP_NAME%" assets blocks config layout locales sections snippets templates

endlocal