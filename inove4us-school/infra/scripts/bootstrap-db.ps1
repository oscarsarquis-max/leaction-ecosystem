#Requires -Version 5.1
<#
.SYNOPSIS
  Cria o banco `inove4us_school` no Postgres do ecossistema e aplica migrations numeradas.

.DESCRIPTION
  Aplica, em ordem, todos os arquivos `NNN_*.sql` em infra/db/migrations
  (exceto `*.down.sql`). Idempotente via CREATE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.

.EXAMPLE
  cd C:\Projetos\leaction-ecosystem\inove4us-school\infra\scripts
  .\bootstrap-db.ps1
#>
param(
  [string]$Container = 'leaction_db',
  [string]$DbUser = 'admin',
  [string]$Database = 'inove4us_school'
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$MigDir = Join-Path $Root 'infra\db\migrations'
if (-not (Test-Path $MigDir)) { throw "Pasta de migrations nao encontrada: $MigDir" }

$running = docker ps --filter "name=^/${Container}$" --format '{{.Names}}'
if (-not $running) { throw "Container $Container nao esta rodando." }

Write-Host "==> CREATE DATABASE $Database (se necessario)" -ForegroundColor Cyan
$exists = docker exec $Container psql -U $DbUser -d postgres -tAc `
  "SELECT 1 FROM pg_database WHERE datname = '$Database';"
if (-not ($exists -match '1')) {
  docker exec $Container psql -U $DbUser -d postgres -v ON_ERROR_STOP=1 -c `
    "CREATE DATABASE $Database ENCODING 'UTF8' TEMPLATE template0;"
}

$migs = Get-ChildItem -Path $MigDir -Filter '*.sql' |
  Where-Object { $_.Name -notmatch '\.down\.sql$' -and $_.Name -match '^\d{3}_' } |
  Sort-Object Name

if (-not $migs) { throw "Nenhuma migration numerada encontrada em $MigDir" }

foreach ($mig in $migs) {
  Write-Host "==> Aplicando $($mig.Name)" -ForegroundColor Cyan
  # docker cp preserva UTF-8; pipe via stdin no Windows corrompe acentos.
  $remote = "/tmp/$($mig.Name)"
  docker cp $mig.FullName "${Container}:${remote}"
  if ($LASTEXITCODE -ne 0) { throw "Falha ao copiar $($mig.Name) para o container" }
  # NOTICE do psql vai para stderr; no PowerShell isso nao e falha real.
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  docker exec $Container psql -U $DbUser -d $Database -v ON_ERROR_STOP=1 -f $remote
  $psqlExit = $LASTEXITCODE
  $ErrorActionPreference = $prevEap
  if ($psqlExit -ne 0) { throw "Falha ao aplicar $($mig.Name)" }
  docker exec $Container rm -f $remote | Out-Null
}

Write-Host "==> Tabelas school_*" -ForegroundColor Green
docker exec $Container psql -U $DbUser -d $Database -c `
  "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'school_%' ORDER BY 1;"

Write-Host "OK: banco $Database pronto." -ForegroundColor Green
