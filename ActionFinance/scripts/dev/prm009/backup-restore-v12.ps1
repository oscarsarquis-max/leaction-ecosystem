# Restore local V12 com tenant/empresa, FKs e grants. Sem RDS.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\_lib.ps1")
$root = Get-ActionFinanceRoot
$secrets = Read-ActionFinanceEnvFile (Join-Path $root ".local\secrets.env")
$evidence = Join-Path $root "documents\reviews\evidence\prm-009-cor-001"
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
$dump = Join-Path $evidence "pay-receipt-v12-with-parents.dump"
$migrations = Join-Path $root "database\migrations"
$name = "prm009-af-restore"
$port = 55433
$env:PGPASSWORD = $secrets.ACTIONFINANCE_BOOTSTRAP_PASSWORD

docker exec -e PGPASSWORD=$env:PGPASSWORD actionfinance-postgres-17 pg_dump `
  -U actionfinance_bootstrap -d actionfinance -Fc --no-owner --no-privileges `
  -t actionfinance.tenant -t actionfinance.company `
  -t actionfinance.pay_receipt_sync_run -t actionfinance.pay_receipt_sync_page `
  -t actionfinance.pay_receipt_checkpoint -t actionfinance.pay_receipt_transaction `
  -t actionfinance.pay_receipt_transaction_revision `
  -f /tmp/prm009-v12-parents.dump
docker cp actionfinance-postgres-17:/tmp/prm009-v12-parents.dump $dump

$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
$existing = docker ps -a --filter "name=^/${name}$" --format "{{.Names}}"
if ($listener -and $existing -ne $name) { throw "Porta $port ocupada e não é $name" }
if ($existing -eq $name) { docker rm -f $name | Out-Null }
docker run -d --name $name --label prm009=1 `
  -e POSTGRES_USER=prm009 -e POSTGRES_PASSWORD=prm009 -e POSTGRES_DB=af_restore `
  -p 127.0.0.1:${port}:5432 postgres:17.6 | Out-Null

$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    docker exec $name pg_isready -U prm009 -d af_restore | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { throw "restore db not ready" }

$bootstrap = Join-Path $evidence "restore-bootstrap.sql"
Set-Content -Path $bootstrap -Encoding ascii -Value @"
CREATE ROLE actionfinance_migrator LOGIN PASSWORD 'verify-migrator';
CREATE ROLE actionfinance_runtime LOGIN PASSWORD 'verify-runtime';
GRANT CONNECT ON DATABASE af_restore TO actionfinance_migrator;
GRANT CONNECT ON DATABASE af_restore TO actionfinance_runtime;
CREATE SCHEMA IF NOT EXISTS actionfinance AUTHORIZATION actionfinance_migrator;
GRANT USAGE ON SCHEMA actionfinance TO actionfinance_runtime;
"@
docker cp $bootstrap "${name}:/tmp/restore-bootstrap.sql"
docker exec $name psql -U prm009 -d af_restore -v ON_ERROR_STOP=1 -f /tmp/restore-bootstrap.sql

docker run --rm --name prm009-flyway --network container:$name `
  -v "${migrations}:/flyway/sql:ro" `
  flyway/flyway:11.10.1 `
  -url=jdbc:postgresql://127.0.0.1:5432/af_restore `
  -user=actionfinance_migrator `
  -password=verify-migrator `
  -schemas=actionfinance `
  -locations=filesystem:/flyway/sql `
  migrate

docker cp $dump "${name}:/tmp/prm009-v12-parents.dump"
docker exec $name pg_restore -U prm009 -d af_restore --data-only --no-owner --no-privileges --disable-triggers /tmp/prm009-v12-parents.dump

$probe = Join-Path $evidence "restore-probe.sql"
Set-Content -Path $probe -Encoding ascii -Value @"
SELECT 'flyway='||string_agg(version, ',' ORDER BY installed_rank) FROM actionfinance.flyway_schema_history WHERE success
UNION ALL SELECT 'tenant='||count(*)::text FROM actionfinance.tenant
UNION ALL SELECT 'company='||count(*)::text FROM actionfinance.company
UNION ALL SELECT 'run='||count(*)::text FROM actionfinance.pay_receipt_sync_run
UNION ALL SELECT 'txn='||count(*)::text FROM actionfinance.pay_receipt_transaction
UNION ALL SELECT 'rev='||count(*)::text FROM actionfinance.pay_receipt_transaction_revision
UNION ALL SELECT 'chk='||count(*)::text FROM actionfinance.pay_receipt_checkpoint
UNION ALL SELECT 'fk_ok='||(
  SELECT count(*)::text FROM actionfinance.pay_receipt_sync_run r
  JOIN actionfinance.company c ON c.tenant_id = r.tenant_id AND c.id = r.company_id
)
UNION ALL SELECT 'orphans='||(
  SELECT count(*)::text FROM actionfinance.pay_receipt_sync_run r
  LEFT JOIN actionfinance.company c ON c.tenant_id = r.tenant_id AND c.id = r.company_id
  WHERE c.id IS NULL
);
SELECT relname||':'||privilege_type
FROM information_schema.role_table_grants g
JOIN pg_class c ON c.relname = g.table_name
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = g.table_schema
WHERE g.grantee = 'actionfinance_runtime'
  AND g.table_schema = 'actionfinance'
  AND g.table_name LIKE 'pay_receipt%'
ORDER BY 1;
"@
docker cp $probe "${name}:/tmp/restore-probe.sql"
$counts = docker exec $name psql -U prm009 -d af_restore -t -A -f /tmp/restore-probe.sql
$orphans = ($counts | Where-Object { $_ -like 'orphans=*' } | ForEach-Object { $_.Split('=')[1] } | Select-Object -First 1)

$previous = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker exec -e PGPASSWORD=verify-runtime $name psql -v ON_ERROR_STOP=1 -U actionfinance_runtime -d af_restore -c "DELETE FROM actionfinance.pay_receipt_transaction WHERE false" 2>$null | Out-Null
$deleteExit = $LASTEXITCODE
$ErrorActionPreference = $previous
if ($deleteExit -eq 0) { throw "Runtime conseguiu DELETE em pay_receipt_transaction" }
if ([int]$orphans -ne 0) { throw "Restore deixou órfãos de company: $orphans" }

$report = @(
    $counts
    "delete_denied=$deleteExit"
    $grants
)
$report | Set-Content (Join-Path $evidence "restore-v12-fk-grants.txt")
Write-Output $report
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
