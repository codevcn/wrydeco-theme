@echo off
setlocal
cd /d "%~dp0"

set "TARGET_PORT=8765"
if not "%~1"=="" set "TARGET_PORT=%~1"

echo ====================================================================
echo   [Module 5] Dang tim va dung tat ca tien trinh chay Blog Tool...
echo ====================================================================

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$port = [int]'%TARGET_PORT%'; " ^
  "$toolDir = (Get-Location).Path; " ^
  "$pids = New-Object System.Collections.Generic.HashSet[int]; " ^
  "Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 } | ForEach-Object { [void]$pids.Add([int]$_.OwningProcess) }; " ^
  "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { " ^
  "  $_.Name -match '^(python|pythonw|py)\.exe$' -and $_.CommandLine -and ( " ^
  "    $_.CommandLine -like ('*' + $toolDir + '*') -or " ^
  "    $_.CommandLine -match 'module-5-blog|server_wrapper\.py|web_app\.py|cli\.py\s+serve' " ^
  "  ) " ^
  "} | ForEach-Object { [void]$pids.Add([int]$_.ProcessId) }; " ^
  "if ($pids.Count -eq 0) { " ^
  "  Write-Host '  -> Khong co tien trinh Blog Tool nao dang chay.' -ForegroundColor Yellow; " ^
  "  exit 0; " ^
  "} " ^
  "foreach ($id in $pids) { " ^
  "  $proc = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + $id) -ErrorAction SilentlyContinue; " ^
  "  if ($proc) { " ^
  "    Write-Host ('  -> Dang dung PID ' + $id + ' (' + $proc.Name + '): ' + $proc.CommandLine) -ForegroundColor Cyan; " ^
  "    & taskkill /F /T /PID $id >$null 2>&1; " ^
  "    Stop-Process -Id $id -Force -ErrorAction SilentlyContinue; " ^
  "  } " ^
  "} " ^
  "Write-Host ('  -> Da dung thanh cong ' + $pids.Count + ' tien trinh.') -ForegroundColor Green;"

echo ====================================================================
endlocal
