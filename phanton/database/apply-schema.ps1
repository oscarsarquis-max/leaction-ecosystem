<#
.SYNOPSIS
  Aplica/atualiza o schema Phanton em um Postgres já existente (idempotente).

.DESCRIPTION
  Use quando o volume Docker já existe (01_init.sql só roda no 1º boot).
  Seguro reexecutar: CREATE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.

.EXAMPLE
  cd C:\Projetos\leaction-ecosystem\phanton\database
  .\apply-schema.ps1
#>
[CmdletBinding()]
param(
    [string]$Container = 'phanton_orquestrador_db',
    [string]$DbUser = 'postgres',
    [string]$Database = 'orquestrador',
    [string]$SqlFile = ''
)

$ErrorActionPreference = 'Stop'
$ComposeDir = $PSScriptRoot
if (-not $SqlFile) {
    $SqlFile = Join-Path $ComposeDir '01_init.sql'
}
if (-not (Test-Path $SqlFile)) {
    throw "SQL não encontrado: $SqlFile"
}

Write-Host "==> Garantindo container $Container ..." -ForegroundColor Cyan
Push-Location $ComposeDir
docker compose up -d | Out-Null
Pop-Location

$deadline = (Get-Date).AddSeconds(45)
do {
    docker exec $Container pg_isready -U $DbUser -d $Database 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)
if ($LASTEXITCODE -ne 0) {
    throw "Container $Container não ficou pronto"
}

$remote = '/tmp/phanton_01_init.sql'
docker cp $SqlFile "${Container}:${remote}"
Write-Host "==> Aplicando schema em $Database ..." -ForegroundColor Cyan
docker exec $Container psql -U $DbUser -d $Database -v ON_ERROR_STOP=1 -f $remote
docker exec $Container rm -f $remote | Out-Null

Write-Host "==> Tabelas:" -ForegroundColor Green
docker exec $Container psql -U $DbUser -d $Database -c `
    "SELECT relname AS table, n_live_tup AS rows_est FROM pg_stat_user_tables ORDER BY relname;"

Write-Host "`nSchema Phanton atualizado." -ForegroundColor Green
