@echo off
setlocal

if "%~1"=="" (
  echo Usage: python todo\SEO\copy_handles_from_csv.py "path\to\file.csv"
  exit /b 1
)

python "%~dp0todo\SEO\copy_handles_from_csv.py" "%~1"
