$ErrorActionPreference = 'Stop'
$valenceRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $valenceRoot
& npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
exit $LASTEXITCODE
