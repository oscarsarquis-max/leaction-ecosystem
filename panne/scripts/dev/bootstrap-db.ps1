#Requires -Version 5.1
# Alembic e venv da Panne exigem Python 3.12 ou superior.
$ErrorActionPreference = 'Stop'
$Container = 'leaction_db'
$DbUser = 'admin'
$Database = 'panne'

$running = docker inspect -f '{{.State.Running}}' $Container 2>$null
if ($running -ne 'true') {
    throw "Container $Container nao esta no ar. Suba o Postgres do workspace (leaction-platform compose db)."
}

$exists = docker exec $Container psql -U $DbUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$Database'"
if (-not $exists) {
    Write-Host "==> CREATE DATABASE $Database" -ForegroundColor Cyan
    docker exec $Container psql -U $DbUser -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $Database ENCODING 'UTF8' TEMPLATE template0;"
} else {
    Write-Host "==> Banco $Database ja existe" -ForegroundColor Green
}

$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Backend = Join-Path $Root 'backend'
$Alembic = Join-Path $Backend '.venv\Scripts\alembic.exe'
if (-not (Test-Path $Alembic)) {
    throw "Alembic nao encontrado. Instale o backend (.venv) antes."
}
Set-Location $Backend
& $Alembic upgrade head
Write-Host "Alembic em head." -ForegroundColor Green
Write-Host "Para o papel de runtime, execute bootstrap-runtime-role.ps1 com PANNE_RUNTIME_PASSWORD local." -ForegroundColor Yellow
