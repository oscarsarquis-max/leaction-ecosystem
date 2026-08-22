#Requires -Version 5.1
# Cria ou atualiza o papel PostgreSQL de runtime da Panne. Idempotente.
$ErrorActionPreference = 'Stop'
$Container = 'leaction_db'
$DbUser = 'admin'
$Database = 'panne'

if (-not $env:PANNE_RUNTIME_PASSWORD) {
    throw "Defina PANNE_RUNTIME_PASSWORD no ambiente local (nao versionado)."
}

$running = docker inspect -f '{{.State.Running}}' $Container 2>$null
if ($running -ne 'true') {
    throw "Container $Container nao esta no ar."
}

$exists = docker exec $Container psql -U $DbUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$Database'"
if (-not $exists) {
    throw "Banco $Database nao existe. Execute bootstrap-db.ps1 antes."
}

$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$SqlPath = Join-Path $PSScriptRoot 'sql\bootstrap-runtime-role.sql'
if (-not (Test-Path $SqlPath)) {
    throw "SQL de bootstrap nao encontrado."
}

$escaped = $env:PANNE_RUNTIME_PASSWORD.Replace("'", "''")
$payload = "SELECT set_config('panne.runtime_password', '$escaped', false);`n" + (Get-Content -Raw $SqlPath)
$payload | docker exec -i $Container psql -U $DbUser -d $Database -v ON_ERROR_STOP=1 | Out-Null
Write-Host "Papel panne_runtime regularizado." -ForegroundColor Green
