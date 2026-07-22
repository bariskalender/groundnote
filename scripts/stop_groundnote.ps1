[CmdletBinding()]
param(
    [switch]$StopFoundry
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$RuntimeDirectory = Join-Path $env:LOCALAPPDATA "GroundNote\runtime"
$SessionFile = Join-Path $RuntimeDirectory "groundnote-session.json"

function Stop-VerifiedProcess([int]$ProcessId, [string]$Token) {
    $Process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $Process) {
        return
    }
    if ($Process.CommandLine -notlike "*$Token*") {
        throw "Saved process metadata does not match the running process. No process was stopped."
    }
    Stop-Process -Id $ProcessId -ErrorAction SilentlyContinue
    try {
        Wait-Process -Id $ProcessId -Timeout 5 -ErrorAction Stop
    }
    catch {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

try {
    if (-not (Test-Path -LiteralPath $SessionFile -PathType Leaf)) {
        Write-Host "No GroundNote launcher session is recorded. No process was stopped."
    }
    else {
        $Session = Get-Content -Raw -LiteralPath $SessionFile | ConvertFrom-Json
        if ($Session.token -notmatch '^[a-f0-9]{32}$') {
            throw "GroundNote runtime metadata is invalid. No process was stopped."
        }
        $Listener = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort ([int]$Session.port) -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $Listener -and $Listener.OwningProcess -ne [int]$Session.pid) {
            throw "The saved port belongs to another process. No process was stopped."
        }
        Stop-VerifiedProcess -ProcessId ([int]$Session.pid) -Token ([string]$Session.token)
        Stop-VerifiedProcess -ProcessId ([int]$Session.launcherPid) -Token ([string]$Session.token)
        Remove-Item -LiteralPath $SessionFile -Force
        Write-Host "GroundNote Streamlit process stopped. Local user data was not changed."
    }

    if ($StopFoundry) {
        $Foundry = Get-Command foundry -ErrorAction SilentlyContinue
        if ($null -eq $Foundry) {
            Write-Warning "Foundry Local is not available, so its server was not changed."
        }
        else {
            & $Foundry.Source server stop
        }
    }
    else {
        Write-Host "Foundry Local was left unchanged because it may be shared by another application."
    }
    exit 0
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
