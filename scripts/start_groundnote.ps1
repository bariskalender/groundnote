[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8501,
    [switch]$NoBrowser,
    [switch]$Background
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDirectory = Join-Path $env:LOCALAPPDATA "GroundNote\runtime"
$SessionFile = Join-Path $RuntimeDirectory "groundnote-session.json"
$FoundryStarted = $false

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
        & $Uv.Source run python -m groundnote doctor --port $Port
        if ($LASTEXITCODE -ne 0) {
            throw "GroundNote is not ready. Fix the doctor errors before starting the app."
        }

        $Token = [Guid]::NewGuid().ToString("N")
        $Arguments = @(
            "run", "python", "-m", "streamlit", "run", "src/groundnote/app.py",
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
            if (-not $Launcher.HasExited) {
                Stop-Process -Id $Launcher.Id -Force -ErrorAction SilentlyContinue
            }
            throw "Streamlit did not start within 30 seconds. Run scripts/doctor.ps1 for guidance."
        }

        New-Item -ItemType Directory -Path $RuntimeDirectory -Force | Out-Null
        [ordered]@{
            pid = [int]$Listener.OwningProcess
            launcherPid = [int]$Launcher.Id
            port = [int]$Port
            token = $Token
            startedAtUtc = [DateTime]::UtcNow.ToString("o")
            foundryStartedByLauncher = $FoundryStarted
        } | ConvertTo-Json | Set-Content -LiteralPath $SessionFile -Encoding UTF8

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
    if ($FoundryStarted) {
        & foundry server stop | Out-Null
    }
    Write-Error $_.Exception.Message
    exit 1
}
