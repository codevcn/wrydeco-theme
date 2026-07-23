@echo off
echo Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b %ERRORLEVEL%
)

echo Starting FastAPI server...
uvicorn main:app --reload
