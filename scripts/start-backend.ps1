$ErrorActionPreference = 'Stop'
$valenceRoot = Split-Path -Parent $PSScriptRoot
$valencePython = Join-Path $valenceRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $valencePython)) {
    throw 'Run the README setup commands first to create .venv and install dependencies.'
}
Set-Location -LiteralPath $valenceRoot
& $valencePython -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8010 --reload --reload-dir backend/app
exit $LASTEXITCODE
