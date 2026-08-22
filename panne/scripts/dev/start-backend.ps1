#Requires -Version 5.1
# Python minimo oficial da Panne: 3.12. Sem fallback para 3.11.
$ErrorActionPreference = 'Stop'
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Backend = Join-Path $Root 'backend'
$Py = Join-Path $Backend '.venv\Scripts\python.exe'
if (-not (Test-Path $Py)) {
    throw "Crie o ambiente: cd $Backend; python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e `".[dev]`""
}
Set-Location $Backend
& $Py -m uvicorn app.main:app --host 127.0.0.1 --port 5080
