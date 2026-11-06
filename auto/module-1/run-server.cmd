@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
python -m scraper serve --host 127.0.0.1 --port 5000
exit /b %errorlevel%
