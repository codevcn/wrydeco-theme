@echo off
setlocal

:: ==========================================
:: CẤU HÌNH ĐƯỜNG DẪN FILE
:: ==========================================
:: File cấu hình chứa thông tin version hiện tại (chuẩn Semantic Versioning)
set "SRC_FILE=%~dp0src-version.json"
:: Tạo một file script tạm (Powershell) trong thư mục Temp của máy tính
set "PS_SCRIPT=%TEMP%\bump_version.ps1"

:: ==========================================
:: TẠO FILE SCRIPT POWERSHELL (BUMP VERSION)
:: ==========================================
:: Đoạn code này sẽ tự sinh ra file bump_version.ps1. 
:: Mục đích: Đọc file src-version.json, tăng version theo logic max=10, rồi ghi đè lại file.
> "%PS_SCRIPT%" echo $srcFile = '%SRC_FILE%'
>> "%PS_SCRIPT%" echo $c = [IO.File]::ReadAllText($srcFile)
:: Tìm chuỗi version có định dạng: "version": "X.Y.Z"
>> "%PS_SCRIPT%" echo if($c -match '\"version\":\s*\"(\d+)\.(\d+)\.(\d+)\"') {
>> "%PS_SCRIPT%" echo     [int]$ma = $matches[1]; [int]$mi = $matches[2]; [int]$pa = $matches[3]
:: Logic tăng version: Tăng PATCH lên 1. Nếu PATCH vượt quá 10 -> Reset PATCH về 0 và tăng MINOR lên 1
:: Tương tự, nếu MINOR vượt quá 10 -> Reset MINOR về 0 và tăng MAJOR lên 1.
>> "%PS_SCRIPT%" echo     $pa++; if($pa -gt 10){ $pa=0; $mi++ }; if($mi -gt 10){ $mi=0; $ma++ }
>> "%PS_SCRIPT%" echo     $nv = "$ma.$mi.$pa"
:: Thay thế chuỗi version cũ bằng version mới trong nội dung text
>> "%PS_SCRIPT%" echo     $nc = $c -replace '\"version\":\s*\"\d+\.\d+\.\d+\"', "`"version`": `"$nv`""
:: Ghi đè lại nội dung vào file src-version.json bằng chuẩn UTF-8 (Không có BOM) để tránh lỗi với Shopify
>> "%PS_SCRIPT%" echo     $enc = New-Object System.Text.UTF8Encoding $false
>> "%PS_SCRIPT%" echo     [IO.File]::WriteAllText($srcFile, $nc, $enc)
:: In ra version mới để CMD có thể lấy được
>> "%PS_SCRIPT%" echo     Write-Output $nv
>> "%PS_SCRIPT%" echo }

:: ==========================================
:: THỰC THI SCRIPT VÀ LẤY KẾT QUẢ
:: ==========================================
:: Chạy file PowerShell vừa tạo ở trên, đọc output trả về (version mới) và lưu vào biến VERSION
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"`) do set "VERSION=%%i"

:: Xóa file PowerShell tạm để dọn dẹp
del "%PS_SCRIPT%"

:: Kiểm tra lỗi: Nếu không lấy được VERSION (có thể do sai định dạng file json hoặc file không tồn tại)
if "%VERSION%"=="" (
    echo Error: Could not read or update version in %SRC_FILE%
    exit /b 1
)

echo Updated version to %VERSION%

:: ==========================================
:: NÉN SOURCE THEME ĐỂ UPLOAD LÊN SHOPIFY
:: ==========================================
:: Định nghĩa tên file zip cuối cùng dựa trên version mới
set "ZIP_NAME=Skeleton-%VERSION%-upload.zip"

:: Xóa tất cả các file zip cũ (phiên bản cũ) có cùng định dạng tên để tránh rác
if exist "Skeleton-*-upload.zip" del /f /q "Skeleton-*-upload.zip"

:: Sử dụng lệnh tar (có sẵn trên Windows 10+) để nén các thư mục quan trọng của Shopify Theme
tar -a -cf "%ZIP_NAME%" assets blocks config layout locales sections snippets templates

echo Created archive: %ZIP_NAME%
endlocal