[CmdletBinding()]
param(
    [string]$OutputDirectory = "dist"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    $Uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -eq $Uv) {
        Write-Error "uv is not available. Run scripts/setup_windows.ps1 first."
        exit 1
    }
    & $Uv.Source run --no-dev python -m groundnote build-archive --output-directory $OutputDirectory
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
