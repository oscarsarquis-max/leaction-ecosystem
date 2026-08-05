# Reset dados transacionais do QMind (dev). Preserva users/orgs/catálogos ISO.
# Uso: .\scripts\reset-transactional-dev.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$sql = Join-Path $root "sql\reset_transactional_dev.sql"
if (-not (Test-Path $sql)) { throw "SQL não encontrado: $sql" }

Write-Host "Truncando dados transacionais em qmind_dev @ leaction_db ..." -ForegroundColor Yellow
Get-Content $sql -Raw -Encoding UTF8 |
  docker exec -i leaction_db psql -U admin -d qmind_dev -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw "psql falhou (exit $LASTEXITCODE)" }
Write-Host "OK — dados transacionais limpos." -ForegroundColor Green
