#Requires -Version 5.1
# Disposable V5 → current upgrade + backup/restore covering V6/V7.
# Does not touch development volumes or product databases.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_lib.ps1")

$root = Get-ActionFinanceRoot
$runId = "af-upgrade-" + [guid]::NewGuid().ToString("N").Substring(0, 12)
$work = Join-Path $root ".local\verify-runs\$runId"
New-Item -ItemType Directory -Force -Path $work | Out-Null
$created = New-Object System.Collections.Generic.List[string]
$okPrinted = $false
$evidence = Join-Path $root "documents\reviews\screenshots\prm-006-cor-001\upgrade-restore-log.json"

function Invoke-Docker {
  param([string[]]$ArgumentList)
  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $output = & docker @ArgumentList 2>&1
  $code = $LASTEXITCODE
  $ErrorActionPreference = $previous
  if ($code -ne 0) {
    throw "docker $($ArgumentList -join ' ') failed: $output"
  }
  return $output
}

function Wait-RestoreReady([string]$name) {
  $deadline = (Get-Date).AddSeconds(90)
  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    do {
      docker exec $name pg_isready -U postgres -d actionfinance 2>$null | Out-Null
      if ($LASTEXITCODE -eq 0) {
        docker exec $name psql -v ON_ERROR_STOP=1 -U postgres -d actionfinance -tAc "select 1" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return }
      }
      Start-Sleep -Milliseconds 400
    } while ((Get-Date) -lt $deadline)
  } finally {
    $ErrorActionPreference = $previous
  }
  throw "Disposable $name did not become ready."
}

function New-OwnedRestoreContainer([string]$suffix) {
  $name = "$runId-$suffix"
  Invoke-Docker @(
    "run", "-d",
    "--name", $name,
    "--label", "com.actionfinance.project=actionfinance",
    "--label", "com.actionfinance.role=upgrade-restore-verify",
    "--label", "com.actionfinance.run=$runId",
    "-e", "POSTGRES_PASSWORD=verify-only",
    "-e", "POSTGRES_DB=actionfinance",
    "postgres:17.6"
  ) | Out-Null
  $created.Add($name) | Out-Null
  Wait-RestoreReady $name
  return $name
}

function Invoke-PsqlFile([string]$name, [string]$sqlFile) {
  Get-Content -Path $sqlFile -Raw | docker exec -i $name psql -v ON_ERROR_STOP=1 -U postgres -d actionfinance | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "psql failed on $name for $sqlFile exit=$LASTEXITCODE"
  }
}

function Invoke-Psql {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Sql,
    [string]$User = "postgres",
    [string]$Password = ""
  )
  $dockerArgs = @("exec")
  if ($Password) { $dockerArgs += @("-e", "PGPASSWORD=$Password") }
  $dockerArgs += @($Name, "psql", "-v", "ON_ERROR_STOP=1", "-U", $User, "-d", "actionfinance", "-tAc", $Sql)
  $output = & docker @dockerArgs
  if ($LASTEXITCODE -ne 0) {
    throw "psql query failed on $Name as $User exit=$LASTEXITCODE"
  }
  return $output
}

function Invoke-Flyway {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string[]]$FlywayArgs
  )
  $migrations = Join-Path $root "database\migrations"
  $dockerArgs = @(
    "run", "--rm",
    "--name", "$runId-flyway",
    "--network", "container:$Name",
    "--label", "com.actionfinance.project=actionfinance",
    "--label", "com.actionfinance.role=upgrade-restore-verify",
    "--label", "com.actionfinance.run=$runId",
    "-v", "${migrations}:/flyway/sql:ro",
    "flyway/flyway:11.10.1",
    "-url=jdbc:postgresql://127.0.0.1:5432/actionfinance",
    "-user=actionfinance_migrator",
    "-password=verify-migrator",
    "-schemas=actionfinance",
    "-locations=filesystem:/flyway/sql"
  ) + $FlywayArgs
  Invoke-Docker $dockerArgs | Out-Null
}

function Get-FactChecksums([string]$name) {
  $sql = @"
select
  (select checksum from actionfinance.flyway_schema_history where version = '1' and success) || '|' ||
  (select coalesce(md5(string_agg(id::text || '|' || description || '|' || coalesce(amount_minor::text,'') || '|' || status, ',' order by id)), 'empty') from actionfinance.financial_title) || '|' ||
  (select coalesce(md5(string_agg(id::text || '|' || title_version::text || '|' || action, ',' order by id)), 'empty') from actionfinance.financial_title_history) || '|' ||
  (select coalesce(md5(string_agg(id::text || '|' || amount_minor::text || '|' || method, ',' order by id)), 'empty') from actionfinance.settlement) || '|' ||
  (select coalesce(md5(string_agg(id::text || '|' || kind || '|' || signed_amount_minor::text, ',' order by id)), 'empty') from actionfinance.cash_movement) || '|' ||
  (select coalesce(md5(string_agg(id::text || '|' || action, ',' order by id)), 'empty') from actionfinance.financial_account_history)
"@
  return (Invoke-Psql -Name $name -Sql $sql).Trim()
}

function Assert-SafeVerifyWorkDir {
  $resolvedWork = [IO.Path]::GetFullPath($work)
  $allowedRoot = [IO.Path]::GetFullPath((Join-Path $root ".local\verify-runs"))
  if (-not (Test-ActionFinancePathInside $resolvedWork $allowedRoot)) {
    throw "Work path $resolvedWork is outside $allowedRoot"
  }
  $leaf = Split-Path $resolvedWork -Leaf
  if ($leaf -ne $runId) {
    throw "Work leaf $leaf does not match runId $runId"
  }
  return $resolvedWork
}

try {
  $source = New-OwnedRestoreContainer "v5"
  $sourceBootstrap = @"
CREATE ROLE actionfinance_migrator LOGIN PASSWORD 'verify-migrator';
CREATE ROLE actionfinance_runtime LOGIN PASSWORD 'verify-runtime';
CREATE SCHEMA actionfinance AUTHORIZATION actionfinance_migrator;
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_migrator;
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_runtime;
GRANT USAGE ON SCHEMA actionfinance TO actionfinance_runtime;
REVOKE CREATE ON SCHEMA actionfinance FROM PUBLIC;
REVOKE CREATE ON SCHEMA actionfinance FROM actionfinance_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
"@
  $restoreBootstrap = @"
CREATE ROLE actionfinance_migrator LOGIN PASSWORD 'verify-migrator';
CREATE ROLE actionfinance_runtime LOGIN PASSWORD 'verify-runtime';
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_migrator;
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
"@
  $bootstrapFile = Join-Path $work "bootstrap.sql"
  $restoreBootstrapFile = Join-Path $work "restore-bootstrap.sql"
  Set-Content -Path $bootstrapFile -Value $sourceBootstrap -Encoding ascii
  Set-Content -Path $restoreBootstrapFile -Value $restoreBootstrap -Encoding ascii
  Invoke-PsqlFile $source $bootstrapFile
  Invoke-Flyway -Name $source -FlywayArgs @("migrate", "-target=5")

  $v5Versions = (Invoke-Psql -Name $source -Sql "select string_agg(version, ',' order by installed_rank) from actionfinance.flyway_schema_history where success").Trim()
  if ($v5Versions -ne "1,2,3,4,5") {
    throw "V5 baseline versions are '$v5Versions', expected 1,2,3,4,5."
  }

  $facts = @"
INSERT INTO actionfinance.tenant (id, code, name, active, created_at, updated_at, version)
VALUES ('11111111-1111-1111-1111-111111111111', 'UPG-T', 'Tenant upgrade', true, '2026-09-01T12:00:00Z', '2026-09-01T12:00:00Z', 0);
INSERT INTO actionfinance.company (id, tenant_id, code, name, active, is_demo, business_timezone, created_at, updated_at, version)
VALUES ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'UPG-C', 'Empresa upgrade', true, false, 'America/Sao_Paulo', '2026-09-01T12:00:00Z', '2026-09-01T12:00:00Z', 0);
INSERT INTO actionfinance.counterparty (id, tenant_id, company_id, code, name, role, active, version, created_at, updated_at, created_by, updated_by)
VALUES ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'UPG-CP', 'Cliente upgrade', 'CUSTOMER', true, 0, '2026-09-01T12:00:00Z', '2026-09-01T12:00:00Z', '33333333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-333333333333');
INSERT INTO actionfinance.financial_category (id, tenant_id, company_id, code, name, direction, active, version, created_at, updated_at, created_by, updated_by)
VALUES ('55555555-5555-5555-5555-555555555555', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'UPG-CAT', 'Categoria upgrade', 'RECEIVABLE', true, 0, '2026-09-01T12:00:00Z', '2026-09-01T12:00:00Z', '33333333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-333333333333');
INSERT INTO actionfinance.financial_title (id, tenant_id, company_id, reference, direction, status, description, counterparty_id, category_id, amount_minor, currency, competence_date, due_date, origin_kind, source_reference, version, created_at, updated_at, created_by, updated_by, confirmed_at)
VALUES ('66666666-6666-6666-6666-666666666666', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'REC-UPG-1', 'RECEIVABLE', 'OPEN', 'Titulo upgrade 150', '44444444-4444-4444-4444-444444444444', '55555555-5555-5555-5555-555555555555', 15000, 'BRL', '2026-09-15', '2026-09-30', 'MANUAL', 'SRC-UPG', 1, '2026-09-01T12:00:00Z', '2026-09-01T12:00:00Z', '33333333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-333333333333', '2026-09-01T12:00:00Z');
INSERT INTO actionfinance.financial_title_history (id, tenant_id, company_id, title_id, title_version, action, actor_id, actor_display_name, occurred_at, reason, changes)
VALUES ('cccccccc-cccc-cccc-cccc-cccccccccccc', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '66666666-6666-6666-6666-666666666666', 1, 'CONFIRMED', '33333333-3333-3333-3333-333333333333', 'Operador upgrade', '2026-09-01T12:00:00Z', 'registro', '{"description":"Titulo upgrade 150"}'::jsonb);
INSERT INTO actionfinance.financial_account (id, tenant_id, company_id, code, name, type, currency, active, opened_on, version, created_at, updated_at, created_by, updated_by)
VALUES ('77777777-7777-7777-7777-777777777777', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'UPG-CTA', 'Conta upgrade', 'CASH', 'BRL', true, '2026-09-01', 0, '2026-09-01T12:00:00Z', '2026-09-01T12:00:00Z', '33333333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-333333333333');
INSERT INTO actionfinance.financial_account_history (id, tenant_id, company_id, account_id, account_version, action, actor_id, occurred_at, changes)
VALUES ('dddddddd-dddd-dddd-dddd-dddddddddddd', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '77777777-7777-7777-7777-777777777777', 0, 'CREATED', '33333333-3333-3333-3333-333333333333', '2026-09-01T12:00:00Z', '{"name":"Conta upgrade"}'::jsonb);
INSERT INTO actionfinance.settlement (id, tenant_id, company_id, account_id, direction, amount_minor, currency, effective_date, method, note, origin_kind, recorded_at, recorded_by, actor_display_name)
VALUES ('88888888-8888-8888-8888-888888888888', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '77777777-7777-7777-7777-777777777777', 'RECEIVABLE', 5000, 'BRL', '2026-09-16', 'PIX', 'baixa parcial upgrade', 'MANUAL', '2026-09-16T12:00:00Z', '33333333-3333-3333-3333-333333333333', 'Operador upgrade');
INSERT INTO actionfinance.settlement_allocation (id, tenant_id, company_id, settlement_id, title_id, amount_minor)
VALUES ('99999999-9999-9999-9999-999999999999', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '88888888-8888-8888-8888-888888888888', '66666666-6666-6666-6666-666666666666', 5000);
INSERT INTO actionfinance.cash_movement (id, tenant_id, company_id, account_id, kind, signed_amount_minor, currency, effective_date, recorded_at, recorded_by, settlement_id, reversal_id, description)
VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '77777777-7777-7777-7777-777777777777', 'OPENING', 20000, 'BRL', '2026-09-01', '2026-09-01T12:00:00Z', '33333333-3333-3333-3333-333333333333', NULL, NULL, 'Abertura upgrade'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', '77777777-7777-7777-7777-777777777777', 'SETTLEMENT', 5000, 'BRL', '2026-09-16', '2026-09-16T12:00:00Z', '33333333-3333-3333-3333-333333333333', '88888888-8888-8888-8888-888888888888', NULL, 'Baixa upgrade');
"@
  $factsFile = Join-Path $work "v5-facts.sql"
  Set-Content -Path $factsFile -Value $facts -Encoding utf8
  Invoke-PsqlFile $source $factsFile

  $beforeUpgrade = Get-FactChecksums $source
  $titleValue = (Invoke-Psql -Name $source -Sql "select description || '|' || amount_minor::text from actionfinance.financial_title where id = '66666666-6666-6666-6666-666666666666'").Trim()
  if ($titleValue -ne "Titulo upgrade 150|15000") {
    throw "V5 title fixture mismatch: $titleValue"
  }

  Invoke-Flyway -Name $source -FlywayArgs @("migrate")
  $afterUpgrade = Get-FactChecksums $source
  if ($beforeUpgrade -ne $afterUpgrade) {
    throw "Financial checksums changed during V5→current upgrade. before=$beforeUpgrade after=$afterUpgrade"
  }
  $upgradedVersions = (Invoke-Psql -Name $source -Sql "select string_agg(version, ',' order by installed_rank) from actionfinance.flyway_schema_history where success").Trim()
  if ($upgradedVersions -ne "1,2,3,4,5,6,7") {
    throw "Upgrade versions are '$upgradedVersions', expected 1,2,3,4,5,6,7."
  }
  $v1 = (Invoke-Psql -Name $source -Sql "select checksum from actionfinance.flyway_schema_history where version = '1' and success").Trim()
  if ($v1 -ne "1488219560") {
    throw "V1 checksum changed: $v1"
  }

  $identity = @"
INSERT INTO actionfinance.app_user (id, display_name, status, created_at, updated_at, version)
VALUES ('33333333-3333-3333-3333-333333333333', 'Operador upgrade', 'ACTIVE', '2026-09-29T12:00:00Z', '2026-09-29T12:00:00Z', 0);
INSERT INTO actionfinance.external_identity (id, user_id, issuer, subject, created_at, updated_at)
VALUES ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', '33333333-3333-3333-3333-333333333333', 'https://idp.trial.localhost:18444/default', 'upgrade-subject', '2026-09-29T12:00:00Z', '2026-09-29T12:00:00Z');
INSERT INTO actionfinance.company_membership (id, user_id, tenant_id, company_id, role, status, created_at, updated_at, version)
VALUES ('ffffffff-ffff-ffff-ffff-ffffffffffff', '33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222', 'OPERATOR', 'ACTIVE', '2026-09-29T12:00:00Z', '2026-09-29T12:00:00Z', 0);
INSERT INTO actionfinance.access_admin_audit (id, occurred_at, executor_kind, executor_label, target_kind, target_id, action, reason, correlation_id, metadata)
VALUES ('12121212-1212-1212-1212-121212121212', '2026-09-29T12:00:00Z', 'ADMIN_CLI', 'upgrade-verify', 'USER', '33333333-3333-3333-3333-333333333333', 'PROVISION_USER', 'fixture de upgrade', 'upgrade-1', '{"kind":"UPGRADE_FIXTURE"}'::jsonb);
INSERT INTO actionfinance.SPRING_SESSION (PRIMARY_ID, SESSION_ID, CREATION_TIME, LAST_ACCESS_TIME, MAX_INACTIVE_INTERVAL, EXPIRY_TIME, PRINCIPAL_NAME)
VALUES ('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 1727611200000, 1727611200000, 1800, 1727613000000, '33333333-3333-3333-3333-333333333333');
INSERT INTO actionfinance.SPRING_SESSION_ATTRIBUTES (SESSION_PRIMARY_ID, ATTRIBUTE_NAME, ATTRIBUTE_BYTES)
VALUES ('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'SPRING_SECURITY_CONTEXT', decode('00', 'hex'));
"@
  $identityFile = Join-Path $work "identity.sql"
  Set-Content -Path $identityFile -Value $identity -Encoding utf8
  Invoke-PsqlFile $source $identityFile

  $dump = Join-Path $work "schema.dump.sql"
  docker exec $source pg_dump -U postgres -d actionfinance --schema=actionfinance --no-owner --no-acl | Set-Content -Path $dump -Encoding utf8
  if ($LASTEXITCODE -ne 0) {
    throw "pg_dump failed exit=$LASTEXITCODE"
  }
  if (-not (Select-String -Path $dump -Pattern "app_user|SPRING_SESSION|access_admin_audit|financial_title" -Quiet)) {
    throw "Dump missing identity/session/financial tables."
  }

  $sourceFacts = Get-FactChecksums $source
  $sourceUsers = (Invoke-Psql -Name $source -Sql "select count(*) || '|' || (select count(*) from actionfinance.external_identity) || '|' || (select count(*) from actionfinance.company_membership) || '|' || (select count(*) from actionfinance.access_admin_audit) || '|' || (select count(*) from actionfinance.SPRING_SESSION) from actionfinance.app_user").Trim()

  $restore = New-OwnedRestoreContainer "restored"
  Invoke-PsqlFile $restore $restoreBootstrapFile
  Invoke-PsqlFile $restore $dump
  Invoke-PsqlFile $restore (Join-Path $root "scripts\dev\restore-runtime-privileges.sql")

  $restoredFacts = Get-FactChecksums $restore
  if ($sourceFacts -ne $restoredFacts) {
    throw "Restored financial checksums differ. source=$sourceFacts restored=$restoredFacts"
  }
  $restoredUsers = (Invoke-Psql -Name $restore -Sql "select count(*) || '|' || (select count(*) from actionfinance.external_identity) || '|' || (select count(*) from actionfinance.company_membership) || '|' || (select count(*) from actionfinance.access_admin_audit) || '|' || (select count(*) from actionfinance.SPRING_SESSION) from actionfinance.app_user").Trim()
  if ($sourceUsers -ne $restoredUsers) {
    throw "Restored identity/session counts differ. source=$sourceUsers restored=$restoredUsers"
  }

  $ownerRows = @(Invoke-Psql -Name $restore -Sql "select n.nspname || '.' || c.relname || '=' || pg_get_userbyid(c.relowner) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'actionfinance' and c.relkind in ('r','p','v','m','S') order by 1")
  $badOwners = @($ownerRows | Where-Object { $_ -and $_.Trim() -notmatch '=actionfinance_migrator$' })
  if ($badOwners.Count -gt 0) {
    throw "Restored objects not owned by migrator: $($badOwners -join ', ')"
  }
  $requiredOwners = @("app_user", "external_identity", "company_membership", "access_admin_audit", "spring_session", "spring_session_attributes", "financial_title")
  foreach ($rel in $requiredOwners) {
    if (-not ($ownerRows | Where-Object { $_ -match "$rel=actionfinance_migrator" })) {
      throw "Missing migrator owner for $rel"
    }
  }

  Invoke-Flyway -Name $restore -FlywayArgs @("validate")

  $runtimeTitle = (Invoke-Psql -Name $restore -Sql "select description from actionfinance.financial_title where id = '66666666-6666-6666-6666-666666666666'" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $runtimeUser = (Invoke-Psql -Name $restore -Sql "select display_name from actionfinance.app_user where id = '33333333-3333-3333-3333-333333333333'" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $runtimeAudit = (Invoke-Psql -Name $restore -Sql "select reason from actionfinance.access_admin_audit where id = '12121212-1212-1212-1212-121212121212'" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  if ($runtimeTitle -ne "Titulo upgrade 150" -or $runtimeUser -ne "Operador upgrade" -or $runtimeAudit -ne "fixture de upgrade") {
    throw "Runtime could not read restored title/user/audit."
  }

  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  docker exec -e PGPASSWORD=verify-runtime $restore psql -v ON_ERROR_STOP=1 -U actionfinance_runtime -d actionfinance -c "create table actionfinance.forbidden(id int)" 2>$null | Out-Null
  $createExit = $LASTEXITCODE
  docker exec -e PGPASSWORD=verify-runtime $restore psql -v ON_ERROR_STOP=1 -U actionfinance_runtime -d actionfinance -c "delete from actionfinance.financial_title where false" 2>$null | Out-Null
  $titleDeleteExit = $LASTEXITCODE
  docker exec -e PGPASSWORD=verify-runtime $restore psql -v ON_ERROR_STOP=1 -U actionfinance_runtime -d actionfinance -c "delete from actionfinance.access_admin_audit where false" 2>$null | Out-Null
  $auditDeleteExit = $LASTEXITCODE
  $ErrorActionPreference = $previous
  if ($createExit -eq 0) { throw "Runtime DDL succeeded after restore." }
  if ($titleDeleteExit -eq 0) { throw "Runtime DELETE on financial_title succeeded." }
  if ($auditDeleteExit -eq 0) { throw "Runtime DELETE on access_admin_audit succeeded." }

  $sessionsBefore = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.SPRING_SESSION" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  if ($sessionsBefore -ne "1") {
    throw "Expected one restored session row, got $sessionsBefore"
  }
  & (Join-Path $root "scripts\ops\invalidate-sessions.ps1") -ContainerName $restore -ContainerUser "actionfinance_runtime" -ContainerPassword "verify-runtime"
  if ($LASTEXITCODE -ne 0) {
    throw "invalidate-sessions.ps1 failed"
  }
  $sessionsAfter = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.SPRING_SESSION" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $factsAfterInvalidate = Get-FactChecksums $restore
  $usersAfterInvalidate = (Invoke-Psql -Name $restore -Sql "select count(*) || '|' || (select count(*) from actionfinance.access_admin_audit) from actionfinance.app_user").Trim()
  if ($sessionsAfter -ne "0") {
    throw "Session rows remained after invalidate: $sessionsAfter"
  }
  if ($factsAfterInvalidate -ne $sourceFacts) {
    throw "Invalidate-sessions changed financial facts."
  }
  if ($usersAfterInvalidate -notmatch '^1\|1$') {
    throw "Invalidate-sessions changed identity/audit: $usersAfterInvalidate"
  }

  $payload = [ordered]@{
    ok = $true
    runId = $runId
    v5Versions = $v5Versions
    upgradedVersions = $upgradedVersions
    v1Checksum = $v1
    financialChecksum = $sourceFacts
    identityCounts = $sourceUsers
    titleValue = $titleValue
    flywayValidate = "ok"
    runtimeRead = "ok"
    runtimeNoDdl = $true
    runtimeNoFactOrAuditDelete = $true
    sessionInvalidate = "SPRING_SESSION 1→0; facts/audit preserved"
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $evidence) | Out-Null
  $payload | ConvertTo-Json | Set-Content -Path $evidence -Encoding utf8

  $okPrinted = $true
  Write-Output "UPGRADE_RESTORE_OK v5=$v5Versions current=$upgradedVersions v1=$v1 facts=$sourceFacts identity=$sourceUsers session_invalidated=1->0 flyway_validate=ok"
} finally {
  foreach ($name in $created) {
    $labels = Get-ActionFinanceContainerLabels $name
    if ($labels -and $labels.'com.actionfinance.project' -eq "actionfinance" -and $labels.'com.actionfinance.role' -eq "upgrade-restore-verify" -and $labels.'com.actionfinance.run' -eq $runId) {
      docker rm -f $name | Out-Null
    }
  }
  $resolvedWork = Assert-SafeVerifyWorkDir
  Remove-Item $resolvedWork -Recurse -Force
}

if (-not $okPrinted) { exit 1 }
