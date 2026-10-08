@echo off
setlocal
cd /d "%~dp0"
python -m scraper stop-servers
endlocal
