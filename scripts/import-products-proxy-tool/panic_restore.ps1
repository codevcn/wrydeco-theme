$ErrorActionPreference = "Continue"

$ToolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$StateDir = Join-Path $ToolRoot "state"
$RuntimeFile = Join-Path $StateDir "runtime.json"

Write-Host "== WRYDECO Proxy Gate Panic Restore =="

function Stop-OnlyOurProcess {
    param(
        [int]$PidValue,
        [string]$Signature
    )

    if ($PidValue -le 0) {
        return
    }

    $Process = Get-CimInstance Win32_Process `
        -Filter "ProcessId=$PidValue" `
        -ErrorAction SilentlyContinue

    if (-not $Process) {
        return
    }

    if ($Process.CommandLine -notlike "*$Signature*") {
        Write-Warning "PID $PidValue does not match expected tool signature; not terminating it."
        return
    }

    Write-Host "Stopping tool process PID $PidValue ($Signature)..."

    Stop-Process `
        -Id $PidValue `
        -Force `
        -ErrorAction Stop
}

if (Test-Path $RuntimeFile) {
    try {
        $Runtime = Get-Content $RuntimeFile -Raw |
            ConvertFrom-Json

        # Watchdog owns WinDivert handles.
        # Killing it first immediately releases network lockdown.
        Stop-OnlyOurProcess `
            -PidValue ([int]$Runtime.watchdog_pid) `
            -Signature "proxy_tool.watchdog"

        Start-Sleep -Milliseconds 500

        Stop-OnlyOurProcess `
            -PidValue ([int]$Runtime.gate_pid) `
            -Signature "proxy_tool.gate_worker"
    }
    catch {
        Write-Warning $_
    }
}

# The tool verifies no prior pktmon session exists before using it,
# therefore stale pktmon here belongs to a crashed tool run.
& pktmon.exe stop *> $null
& pktmon.exe filter remove *> $null

Remove-Item `
    (Join-Path $StateDir "stop.requested") `
    -Force `
    -ErrorAction SilentlyContinue

Remove-Item `
    $RuntimeFile `
    -Force `
    -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Panic restore finished."
Write-Host "No persistent route, DNS, Windows proxy, or firewall configuration is used by this tool."