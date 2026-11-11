$ErrorActionPreference = "Stop"

$ToolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $ToolRoot ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

$WinDivertVersion = "2.2.2"
$ArchiveName = "WinDivert-2.2.2-A.zip"
$WinDivertUrl = "https://github.com/basil00/WinDivert/releases/download/v2.2.2/WinDivert-2.2.2-A.zip"

# Pinned exact artifact hash.
$ExpectedSha256 = "63cb41763bb4b20f600b6de04e991a9c2be73279e317d4d82f237b150c5f3f15"

$CacheDir = Join-Path $ToolRoot ".cache"
$ArchivePath = Join-Path $CacheDir $ArchiveName
$ExtractDir = Join-Path $CacheDir "windivert-$WinDivertVersion"
$VendorDir = Join-Path $ToolRoot "vendor\windivert"

Write-Host "== Shopify Import Proxy Tool bootstrap =="

if (-not [Environment]::Is64BitOperatingSystem) {
    throw "64-bit Windows is required."
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found in PATH."
}

if (-not (Test-Path $Venv)) {
    Write-Host "Creating Python virtual environment..."
    python -m venv $Venv
}

& $Python -c "import sys; assert sys.version_info >= (3, 12), sys.version"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12+ is required."
}

Write-Host "Installing Python dependencies..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $ToolRoot "requirements.txt")

New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null

if (-not (Test-Path $ArchivePath)) {
    Write-Host "Downloading official WinDivert $WinDivertVersion..."
    Invoke-WebRequest `
        -Uri $WinDivertUrl `
        -OutFile $ArchivePath `
        -UseBasicParsing
}

$ActualHash = (Get-FileHash -Algorithm SHA256 $ArchivePath).Hash.ToLowerInvariant()

if ($ActualHash -ne $ExpectedSha256) {
    Remove-Item $ArchivePath -Force -ErrorAction SilentlyContinue
    throw "WinDivert archive SHA256 mismatch. Expected $ExpectedSha256; got $ActualHash. Archive deleted."
}

Write-Host "WinDivert archive hash verified."

Remove-Item $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path $ArchivePath -DestinationPath $ExtractDir -Force

$Dll = Get-ChildItem -Path $ExtractDir -Recurse -File -Filter "WinDivert.dll" |
    Where-Object { $_.FullName -match "\\x64\\WinDivert\.dll$" } |
    Select-Object -First 1

$Sys = Get-ChildItem -Path $ExtractDir -Recurse -File -Filter "WinDivert64.sys" |
    Where-Object { $_.FullName -match "\\x64\\WinDivert64\.sys$" } |
    Select-Object -First 1

if (-not $Dll -or -not $Sys) {
    throw "Expected x64 WinDivert binaries were not found in the verified archive."
}

Copy-Item $Dll.FullName (Join-Path $VendorDir "WinDivert.dll") -Force
Copy-Item $Sys.FullName (Join-Path $VendorDir "WinDivert64.sys") -Force

$License = Get-ChildItem -Path $ExtractDir -Recurse -File |
    Where-Object { $_.Name -match "^LICENSE" } |
    Select-Object -First 1

if ($License) {
    Copy-Item $License.FullName (Join-Path $VendorDir "LICENSE") -Force
}

$DriverPath = Join-Path $VendorDir "WinDivert64.sys"
$Signature = Get-AuthenticodeSignature $DriverPath

if ($Signature.Status -ne "Valid") {
    throw "WinDivert64.sys Authenticode signature is not valid. Status: $($Signature.Status). Do NOT disable Windows security controls automatically."
}

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "WinDivert: $WinDivertVersion"
Write-Host "Driver signature: Valid"
Write-Host ""
Write-Host "Run network-enforcement commands from an Administrator PowerShell."