@echo off
cd /d "%~dp0"
if "%1"=="" (
    python server_wrapper.py --host 127.0.0.1 --port 8765
) else (
    python cli.py %*
)
