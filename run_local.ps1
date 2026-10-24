param([ValidateRange(1,65535)][int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Chua co .venv. Hay tao moi truong va cai requirements.txt theo README.'
}
& $projectPython -m uvicorn api.main:app --host 127.0.0.1 --port $Port
