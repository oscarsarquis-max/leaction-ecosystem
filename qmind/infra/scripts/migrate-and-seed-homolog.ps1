<#
.SYNOPSIS
  Run Alembic migrations + catalog seeds using ADMIN identity (never qmind_app).

.PARAMETER AdminDatabaseUrl
  SQLAlchemy URL for admin role, e.g. postgresql+psycopg://qmind_admin:...@host:5432/qmind
#>
param(
  [Parameter(Mandatory = $true)]
  [string] $AdminDatabaseUrl,

  [string] $BackendDir = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "backend")
)

$ErrorActionPreference = "Stop"

if ($AdminDatabaseUrl -match "qmind_app") {
  throw "Refusing to migrate with qmind_app URL. Use DATABASE_URL_ADMIN."
}

Set-Location $BackendDir
$env:DATABASE_URL_ADMIN = $AdminDatabaseUrl
$env:DATABASE_URL = $AdminDatabaseUrl
$env:PYTHONPATH = $BackendDir

Write-Host "== alembic upgrade head =="
if (Test-Path ".\.venv\Scripts\python.exe") {
  .\.venv\Scripts\python.exe -m alembic upgrade head
} else {
  python -m alembic upgrade head
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== seeds (catalog only) =="
$seed1 = Join-Path $BackendDir "seeds\001_maturity_catalog_v0.sql"
$seed2 = Join-Path $BackendDir "seeds\002_assessment_model_stub.sql"

# Prefer psql if DATABASE_URL can be converted; else print manual step.
Write-Host "Apply seeds with admin psql against database 'qmind':"
Write-Host "  $seed1"
Write-Host "  $seed2"
Write-Host "Example (Docker local):"
Write-Host "  Get-Content `$seed1 -Raw | docker exec -i leaction_db psql -U admin -d qmind"

Write-Host "Done. Configure runtime with DATABASE_URL_APP (qmind_app) only."
