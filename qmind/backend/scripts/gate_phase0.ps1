#Requires -Version 5.1
<#
.SYNOPSIS
  Gate tecnico Fase 0 - QMind DDL (pre-API).
.NOTES
  Database logico: qmind | Cluster: leaction_db (localhost:5433)
#>
$ErrorActionPreference = "Stop"
$Backend = Split-Path -Parent $PSScriptRoot
Set-Location $Backend

function Invoke-Native([scriptblock]$Cmd) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $output = & $Cmd 2>&1 | ForEach-Object { "$_" }
    return @{ Code = $LASTEXITCODE; Output = ($output -join "`n") }
  } finally {
    $ErrorActionPreference = $prev
  }
}

$AdminUrl = $env:DATABASE_URL
if (-not $AdminUrl) {
  $AdminUrl = "postgresql+psycopg://admin:password123@localhost:5433/qmind"
}
$env:DATABASE_URL = $AdminUrl
$env:QMIND_DB_ADMIN_URL = $AdminUrl
$env:DATABASE_URL_APP = "postgresql+psycopg://qmind_app:qmind_app_dev@localhost:5433/qmind"

$results = [ordered]@{}
function Pass([string]$k, [string]$msg) {
  $results[$k] = "PASS - $msg"
  Write-Host "PASS $k - $msg" -ForegroundColor Green
}
function Fail([string]$k, [string]$msg) {
  $results[$k] = "FAIL - $msg"
  Write-Host "FAIL $k - $msg" -ForegroundColor Red
}

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -q

Write-Host "`n=== G1 empty migrate ===" -ForegroundColor Cyan
docker exec leaction_db psql -U admin -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'qmind' AND pid <> pg_backend_pid();" | Out-Null
docker exec leaction_db psql -U admin -d postgres -c "DROP DATABASE IF EXISTS qmind;"
docker exec leaction_db psql -U admin -d postgres -c "CREATE DATABASE qmind;"
$r1 = Invoke-Native { alembic upgrade head }
Write-Host $r1.Output
$rCur = Invoke-Native { alembic current }
if ($r1.Code -eq 0 -and $rCur.Output -match "20260803_0001") { Pass "G1" "upgrade head on empty DB -> 20260803_0001" }
else { Fail "G1" "code=$($r1.Code) rev=$($rCur.Output)" }

Write-Host "`n=== G2 idempotent upgrade ===" -ForegroundColor Cyan
$r2 = Invoke-Native { alembic upgrade head }
Write-Host $r2.Output
if ($r2.Code -eq 0) { Pass "G2" "second upgrade head OK (no-op)" }
else { Fail "G2" "second upgrade failed code=$($r2.Code)" }

Write-Host "`n=== G8 seeds ===" -ForegroundColor Cyan
Get-Content .\seeds\001_maturity_catalog_v0.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind -v ON_ERROR_STOP=1 | Out-Null
Get-Content .\seeds\002_assessment_model_stub.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind -v ON_ERROR_STOP=1 | Out-Null
Get-Content .\seeds\001_maturity_catalog_v0.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind -v ON_ERROR_STOP=1 | Out-Null
Get-Content .\seeds\002_assessment_model_stub.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind -v ON_ERROR_STOP=1 | Out-Null
$mc = docker exec leaction_db psql -U admin -d qmind -tAc "SELECT count(*) FROM maturity_criteria"
$am = docker exec leaction_db psql -U admin -d qmind -tAc "SELECT count(*) FROM assessment_models"
if ([int]$mc -ge 18 -and [int]$am -ge 1) { Pass "G8" "seeds clean+reapply OK (criteria=$mc models=$am)" }
else { Fail "G8" "criteria=$mc models=$am" }

Write-Host "`n=== G4/G5 roles RLS ===" -ForegroundColor Cyan
$role = (docker exec leaction_db psql -U admin -d qmind -tAc "SELECT rolsuper::text||','||rolbypassrls::text FROM pg_roles WHERE rolname='qmind_app'").Trim()
$own = (docker exec leaction_db psql -U admin -d qmind -tAc "SELECT r.rolname FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner WHERE c.relname='organizations'").Trim()
$force = (docker exec leaction_db psql -U admin -d qmind -tAc "SELECT relforcerowsecurity::text FROM pg_class WHERE relname='assessments'").Trim()
if ($role -eq "false,false" -and $own -ne "qmind_app" -and $force -eq "true") {
  Pass "G4" "qmind_app no super/bypass; owner=$own"
  Pass "G5" "FORCE RLS on assessments"
} else {
  Fail "G4" "role=$role owner=$own"
  Fail "G5" "force=$force"
}

Write-Host "`n=== G7 isolation tests ===" -ForegroundColor Cyan
$r7 = Invoke-Native { pytest -q }
Write-Host $r7.Output
if ($r7.Code -eq 0) { Pass "G7" "pytest isolation CRUD OK" }
else { Fail "G7" "pytest failed code=$($r7.Code)" }

Write-Host "`n=== G6 backup restore ===" -ForegroundColor Cyan
$dump = Join-Path $env:TEMP "qmind_schema_gate.sql"
docker exec leaction_db pg_dump -U admin -d qmind --schema-only --no-owner --no-privileges | Set-Content -Path $dump -Encoding utf8
docker exec leaction_db psql -U admin -d postgres -c "DROP DATABASE IF EXISTS qmind_gate_restore;"
docker exec leaction_db psql -U admin -d postgres -c "CREATE DATABASE qmind_gate_restore;"
Get-Content $dump -Raw | docker exec -i leaction_db psql -U admin -d qmind_gate_restore -v ON_ERROR_STOP=1 | Out-Null
$tbl = (docker exec leaction_db psql -U admin -d qmind_gate_restore -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='assessments'").Trim()
docker exec leaction_db psql -U admin -d postgres -c "DROP DATABASE IF EXISTS qmind_gate_restore;" | Out-Null
if ([int]$tbl -eq 1) { Pass "G6" "pg_dump -s restore OK" }
else { Fail "G6" "assessments missing after restore" }

Write-Host "`n=== G3 downgrade ===" -ForegroundColor Cyan
$rDown = Invoke-Native { alembic downgrade base }
Write-Host $rDown.Output
$afterDown = (docker exec leaction_db psql -U admin -d qmind -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='organizations'").Trim()
$rUp = Invoke-Native { alembic upgrade head }
Write-Host $rUp.Output
Get-Content .\seeds\001_maturity_catalog_v0.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind -v ON_ERROR_STOP=1 | Out-Null
Get-Content .\seeds\002_assessment_model_stub.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind -v ON_ERROR_STOP=1 | Out-Null
$afterUp = (docker exec leaction_db psql -U admin -d qmind -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='organizations'").Trim()
if ($rDown.Code -eq 0 -and $rUp.Code -eq 0 -and [int]$afterDown -eq 0 -and [int]$afterUp -eq 1) {
  Pass "G3" "downgrade base removed tables; re-upgrade OK"
} else {
  Fail "G3" "down=$($rDown.Code) up=$($rUp.Code) afterDown=$afterDown afterUp=$afterUp"
}

Write-Host "`n=== GATE SUMMARY ===" -ForegroundColor Cyan
$failCount = 0
foreach ($kv in $results.GetEnumerator()) {
  Write-Host "$($kv.Key): $($kv.Value)"
  if ($kv.Value -like "FAIL*") { $failCount++ }
}
$verdict = if ($failCount -eq 0) { "APROVADO" } else { "REPROVADO" }
Write-Host "`nVEREDITO: $verdict" -ForegroundColor $(if ($verdict -eq "APROVADO") { "Green" } else { "Red" })

$reportPath = Join-Path $Backend "..\architecture\04_Docs\008_Phase0_Technical_Gate.md"
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
$lines = @()
$lines += ""
$lines += "## 4. Resultado do gate (ultima execucao)"
$lines += ""
$lines += "- Data/hora: $stamp"
$lines += "- Executor: gate_phase0.ps1"
$lines += "- **Veredito:** ``$verdict``"
$lines += "- Notas:"
foreach ($kv in $results.GetEnumerator()) {
  $lines += "  - $($kv.Key): $($kv.Value)"
}
$lines += ""
$block = ($lines -join "`n") + "`n"

$md = Get-Content $reportPath -Raw -Encoding utf8
if ($md -match '(?s)## 4\. Resultado do gate.*?(?=## 5\.|\z)') {
  $md = [regex]::Replace($md, '(?s)## 4\. Resultado do gate.*?(?=## 5\.|\z)', $block)
} else {
  $md = $md.TrimEnd() + "`n" + $block
}
Set-Content -Path $reportPath -Value $md -Encoding utf8

if ($verdict -ne "APROVADO") { exit 1 }
exit 0
