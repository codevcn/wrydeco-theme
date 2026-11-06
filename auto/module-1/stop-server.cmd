@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
echo Requesting server shutdown and waiting for cleanup...
python -m scraper stop-servers
exit /b %errorlevel%
