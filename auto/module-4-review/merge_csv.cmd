@echo off
chcp 65001 >nul
echo [INFO] Running merge_csv.py...
python "%~dp0merge_csv.py"
echo.
pause
