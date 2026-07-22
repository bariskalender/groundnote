[CmdletBinding()]
param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Write-Step([string]$Message) {
    Write-Host "[GroundNote setup] $Message"
}

try {
    if ($env:OS -ne "Windows_NT") {
        throw "This setup script supports Windows only. See README.md for other platforms."
    }

    $Uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -eq $Uv) {
        throw "uv is required and was not installed automatically. Install it with 'winget install --id=astral-sh.uv -e', reopen PowerShell, and retry."
    }

    $Foundry = Get-Command foundry -ErrorAction SilentlyContinue
    if ($null -eq $Foundry) {
        throw "Microsoft Foundry Local is required. Install it first, then retry setup."
    }

    Write-Step "Project folder detected."
    Write-Step "uv: $(& $Uv.Source --version)"
    Write-Step "Foundry Local CLI: $(& $Foundry.Source --version)"
    if ($DryRun) {
        Write-Step "Dry run only; would run uv sync, initialize local directories/database, and run the environment doctor."
        exit 0
    }

    Push-Location $ProjectRoot
    try {
        Write-Step "Synchronizing the locked Python environment."
        & $Uv.Source sync
        if ($LASTEXITCODE -ne 0) {
            throw "uv sync failed. Review the dependency output above."
        }

        Write-Step "Preparing local directories and SQLite schema without replacing user data."
        & $Uv.Source run python -m groundnote prepare
        if ($LASTEXITCODE -ne 0) {
            throw "GroundNote local preparation failed. Review .env.example and retry."
        }

        Write-Step "Running the environment doctor. No models will be downloaded or loaded."
        & $Uv.Source run python -m groundnote doctor --port 8501
        if ($LASTEXITCODE -ne 0) {
            throw "Setup completed dependency synchronization, but the environment doctor found a blocking issue."
        }
    }
    finally {
        Pop-Location
    }

    Write-Step "Success. Start GroundNote with scripts/start_groundnote.ps1."
    exit 0
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
