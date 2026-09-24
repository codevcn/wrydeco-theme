@echo off
setlocal

REM ==================================================
REM CONFIG
REM ==================================================
set "SOURCE=D:\D-Jobs\ae-B6\Shopify\stores\main\wrydeco\wrydeco-app\auto\module-1\extension"
set "DEST=D:\D-Documents\Browser-Extensions\codevoicainay\wrydeco-amazon-scraper"

REM ==================================================
REM CHECK
REM ==================================================
if not exist "%SOURCE%\" (
    echo.
    echo ERROR: Folder nguon khong ton tai:
    echo %SOURCE%
    pause
    exit /b 1
)

if not exist "%DEST%\" (
    mkdir "%DEST%"
)

echo.
echo ========================================
echo SOURCE: %SOURCE%
echo DEST:   %DEST%
echo ========================================
echo.

REM ==================================================
REM 1. MOVE ALL CURRENT DEST CONTENT TO RECYCLE BIN
REM ==================================================
echo [1/2] Dang dua noi dung folder dich vao Recycle Bin...

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName Microsoft.VisualBasic; $items = Get-ChildItem -LiteralPath $env:DEST -Force; foreach ($item in $items) { if ($item.PSIsContainer) { [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($item.FullName, [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs, [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin) } else { [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($item.FullName, [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs, [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin) } }"

if errorlevel 1 (
    echo.
    echo ERROR: Khong the dua mot so file vao Recycle Bin.
    pause
    exit /b 1
)

REM ==================================================
REM 2. COPY SOURCE TO DEST
REM ==================================================
echo.
echo [2/2] Dang copy SOURCE sang DEST...

robocopy "%SOURCE%" "%DEST%" /E /COPY:DAT /DCOPY:DAT /R:2 /W:1

set "ROBOCODE=%ERRORLEVEL%"

REM Robocopy: errorlevel 0-7 = success
REM 8+ = actual error
if %ROBOCODE% GEQ 8 (
    echo.
    echo ERROR: Copy that bai.
    echo Robocopy error code: %ROBOCODE%
    pause
    exit /b %ROBOCODE%
)

echo.
echo ========================================
echo DONE
echo ========================================
echo Noi dung cu cua DEST:
echo   ^> Da dua vao Recycle Bin
echo.
echo SOURCE:
echo   ^> Van con nguyen
echo.
echo DEST:
echo   ^> Da copy noi dung moi tu SOURCE
echo ========================================
echo.