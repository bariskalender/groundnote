[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8501,
    [switch]$NoBrowser,
    [switch]$Background,
    [string]$RuntimeDirectoryOverride = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDirectory = if ([string]::IsNullOrWhiteSpace($RuntimeDirectoryOverride)) {
    Join-Path $env:LOCALAPPDATA "GroundNote\runtime"
} else {
    $RuntimeDirectoryOverride
}
$SessionFile = Join-Path $RuntimeDirectory "groundnote-session.json"
$FoundryStarted = $false
$Launcher = $null
$OwnedListenerPid = $null
$Token = $null
$SessionMetadataWritten = $false
$SessionTempFile = $null

function Get-Listener([int]$CandidatePort) {
    return Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort $CandidatePort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Get-VerifiedSession {
    if (-not (Test-Path -LiteralPath $SessionFile -PathType Leaf)) {
        return $null
    }
    try {
        $Session = Get-Content -Raw -LiteralPath $SessionFile | ConvertFrom-Json
        if ($Session.token -notmatch '^[a-f0-9]{32}$') {
            return $null
        }
        $Process = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$Session.pid)" -ErrorAction SilentlyContinue
        $Listener = Get-Listener -CandidatePort ([int]$Session.port)
        if ($null -ne $Process -and $null -ne $Listener -and $Listener.OwningProcess -eq [int]$Session.pid -and $Process.CommandLine -like "*$($Session.token)*") {
            return $Session
        }
    }
    catch {
        return $null
    }
    return $null
}

function Stop-OwnedLaunchProcess([Nullable[int]]$ListenerPid, [Nullable[int]]$LauncherPid, [string]$SessionToken) {
    if ([string]::IsNullOrWhiteSpace($SessionToken)) {
        return
    }
    $TokenProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $null -ne $_.CommandLine -and $_.CommandLine -like "*$SessionToken*"
    } | Select-Object -ExpandProperty ProcessId
    $Candidates = @($ListenerPid, $LauncherPid) + @($TokenProcesses) |
        Where-Object { $null -ne $_ } |
        Select-Object -Unique
    foreach ($Candidate in $Candidates) {
        $Process = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$Candidate)" -ErrorAction SilentlyContinue
        if ($null -eq $Process -or $Process.CommandLine -notlike "*$SessionToken*") {
            continue
        }
        Stop-Process -Id ([int]$Candidate) -ErrorAction SilentlyContinue
        try {
            Wait-Process -Id ([int]$Candidate) -Timeout 5 -ErrorAction Stop
        }
        catch {
            $StillOwned = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$Candidate)" -ErrorAction SilentlyContinue
            if ($null -ne $StillOwned -and $StillOwned.CommandLine -like "*$SessionToken*") {
                Stop-Process -Id ([int]$Candidate) -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

try {
    $Existing = Get-VerifiedSession
    if ($null -ne $Existing) {
        Write-Host "GroundNote is already running at http://127.0.0.1:$($Existing.port)/"
        exit 0
    }
    if (Test-Path -LiteralPath $SessionFile) {
        Remove-Item -LiteralPath $SessionFile -Force
    }

    $Uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -eq $Uv) {
        throw "uv is not available. Run scripts/setup_windows.ps1 first."
    }
    $Foundry = Get-Command foundry -ErrorAction SilentlyContinue
    if ($null -eq $Foundry) {
        throw "Microsoft Foundry Local is not available. Run scripts/doctor.ps1 for guidance."
    }

    if ($null -ne (Get-Listener -CandidatePort $Port)) {
        $Fallback = $null
        foreach ($Candidate in (($Port + 1)..([Math]::Min($Port + 9, 65535)))) {
            if ($null -eq (Get-Listener -CandidatePort $Candidate)) {
                $Fallback = $Candidate
                break
            }
        }
        if ($null -eq $Fallback) {
            throw "Port $Port and the next nine local ports are occupied. Stop the conflicting application and retry."
        }
        Write-Warning "Port $Port is occupied by another application. Using local port $Fallback."
        $Port = $Fallback
    }

    $ServerStatus = & $Foundry.Source server status -o json | ConvertFrom-Json
    if (-not $ServerStatus.running) {
        Write-Host "Starting Microsoft Foundry Local..."
        & $Foundry.Source server start
        if ($LASTEXITCODE -ne 0) {
            throw "Foundry Local could not be started. Run 'foundry server status' for details."
        }
        $FoundryStarted = $true
    }

    Push-Location $ProjectRoot
    try {
        & $Uv.Source run --no-dev python -m groundnote doctor --port $Port
        if ($LASTEXITCODE -ne 0) {
            throw "GroundNote is not ready. Fix the doctor errors before starting the app."
        }

        $Token = [Guid]::NewGuid().ToString("N")
        $Arguments = @(
            "run", "--no-dev", "python", "-m", "streamlit", "run", "src/groundnote/app.py",
            "--server.address", "127.0.0.1",
            "--server.port", $Port,
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--", "--groundnote-session-token", $Token
        )
        $PreviousEnvironment = [Environment]::GetEnvironmentVariable("GROUNDNOTE_ENV", "Process")
        [Environment]::SetEnvironmentVariable("GROUNDNOTE_ENV", "production", "Process")
        try {
            $Launcher = Start-Process -FilePath $Uv.Source -ArgumentList $Arguments -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
        }
        finally {
            [Environment]::SetEnvironmentVariable("GROUNDNOTE_ENV", $PreviousEnvironment, "Process")
        }

        $Deadline = (Get-Date).AddSeconds(30)
        $Listener = $null
        do {
            Start-Sleep -Milliseconds 300
            $Listener = Get-Listener -CandidatePort $Port
        } while ($null -eq $Listener -and -not $Launcher.HasExited -and (Get-Date) -lt $Deadline)
        if ($null -eq $Listener) {
            throw "Streamlit did not start within 30 seconds. Run scripts/doctor.ps1 for guidance."
        }
        $OwnedListenerPid = [int]$Listener.OwningProcess

        $Healthy = $false
        do {
            try {
                $Health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/_stcore/health" -TimeoutSec 2
                $Healthy = $Health.StatusCode -eq 200
            }
            catch {
                $Healthy = $false
            }
            if (-not $Healthy) {
                Start-Sleep -Milliseconds 300
            }
        } while (-not $Healthy -and -not $Launcher.HasExited -and (Get-Date) -lt $Deadline)
        if (-not $Healthy) {
            throw "Streamlit did not pass its local health check. Run scripts/doctor.ps1 for guidance."
        }

        try {
            New-Item -ItemType Directory -Path $RuntimeDirectory -Force | Out-Null
            $SessionTempFile = Join-Path $RuntimeDirectory "groundnote-session.$Token.tmp"
            [ordered]@{
                pid = $OwnedListenerPid
                launcherPid = [int]$Launcher.Id
                port = [int]$Port
                token = $Token
                startedAtUtc = [DateTime]::UtcNow.ToString("o")
                foundryStartedByLauncher = $FoundryStarted
            } | ConvertTo-Json | Set-Content -LiteralPath $SessionTempFile -Encoding UTF8
            Move-Item -LiteralPath $SessionTempFile -Destination $SessionFile -Force
            $SessionMetadataWritten = $true
        }
        catch {
            throw "GroundNote runtime metadata could not be written. The launched process was stopped safely."
        }

        $Url = "http://127.0.0.1:$Port/"
        Write-Host "GroundNote is running locally at $Url"
        Write-Host "Stop it with scripts/stop_groundnote.ps1."
        if (-not $NoBrowser) {
            Start-Process $Url | Out-Null
        }
        if ($Background) {
            exit 0
        }

        try {
            Wait-Process -Id ([int]$Listener.OwningProcess)
        }
        finally {
            & (Join-Path $PSScriptRoot "stop_groundnote.ps1")
        }
    }
    finally {
        Pop-Location
    }
}
catch {
    if (-not $SessionMetadataWritten) {
        $LauncherPid = if ($null -ne $Launcher) { [Nullable[int]]$Launcher.Id } else { $null }
        Stop-OwnedLaunchProcess -ListenerPid $OwnedListenerPid -LauncherPid $LauncherPid -SessionToken $Token
        if ($null -ne $SessionTempFile -and (Test-Path -LiteralPath $SessionTempFile)) {
            Remove-Item -LiteralPath $SessionTempFile -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path -LiteralPath $SessionFile) {
            Remove-Item -LiteralPath $SessionFile -Force -ErrorAction SilentlyContinue
        }
    }
    if ($FoundryStarted) {
        & foundry server stop | Out-Null
    }
    Write-Error $_.Exception.Message
    exit 1
}
