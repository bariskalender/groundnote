[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    $Uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -eq $Uv) {
        Write-Error "uv is not available. Install it with 'winget install --id=astral-sh.uv -e'."
        exit 1
    }
    & $Uv.Source run --no-dev python -m groundnote doctor --port $Port
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
