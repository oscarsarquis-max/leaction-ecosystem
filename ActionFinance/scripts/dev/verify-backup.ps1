$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_lib.ps1")

$root = Get-ActionFinanceRoot
$secrets = Read-ActionFinanceEnvFile (Join-Path $root ".local\secrets.env")
$runId = "af-restore-" + [guid]::NewGuid().ToString("N").Substring(0, 12)
$work = Join-Path $root ".local\verify-runs\$runId"
New-Item -ItemType Directory -Force -Path $work | Out-Null
$dump = Join-Path $work "schema.dump.sql"
$created = New-Object System.Collections.Generic.List[string]
$okPrinted = $false

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
  throw "Disposable restore $name did not become ready."
}

function New-OwnedRestoreContainer([string]$suffix) {
  $name = "$runId-$suffix"
  Invoke-Docker @(
    "run", "-d",
    "--name", $name,
    "--label", "com.actionfinance.project=actionfinance",
    "--label", "com.actionfinance.role=restore-verify",
    "--label", "com.actionfinance.run=$runId",
    "-e", "POSTGRES_PASSWORD=verify-only",
    "-e", "POSTGRES_DB=actionfinance",
    "postgres:17.6"
  )
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
  $args = @("exec")
  if ($Password) { $args += @("-e", "PGPASSWORD=$Password") }
  $args += @($Name, "psql", "-v", "ON_ERROR_STOP=1", "-U", $User, "-d", "actionfinance", "-tAc", $Sql)
  $output = & docker @args
  if ($LASTEXITCODE -ne 0) {
    throw "psql query failed on $Name as $User exit=$LASTEXITCODE"
  }
  return $output
}

function Assert-SafeVerifyWorkDir {
  $resolvedWork = [IO.Path]::GetFullPath($work)
  $allowedRoot = [IO.Path]::GetFullPath((Join-Path $root ".local\verify-runs"))
  if ((Get-ActionFinanceNormalizedPath $resolvedWork) -eq (Get-ActionFinanceNormalizedPath $allowedRoot)) {
    throw "Refusing to delete verify-runs root $resolvedWork"
  }
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
  $source = Get-ActionFinancePostgresName
  if (-not (Test-ActionFinanceOwnedContainer $source)) {
    throw "Source container $source is missing or not owned by ActionFinance."
  }

  $sourceVersions = (Invoke-Psql -Name $source -Sql "select string_agg(version || ':' || checksum, ',' order by installed_rank) from actionfinance.flyway_schema_history where success" -User "actionfinance_bootstrap").Trim()
  $sourceChecksum = (Invoke-Psql -Name $source -Sql "select checksum from actionfinance.flyway_schema_history where version = '1' and success" -User "actionfinance_bootstrap").Trim()
  if ($sourceVersions -notmatch '^1:1488219560') {
    throw "Source Flyway set is '$sourceVersions', expected V1 checksum 1488219560."
  }
  if ($sourceVersions -notmatch ',2:' -or $sourceVersions -notmatch ',3:' -or $sourceVersions -notmatch ',4:' -or $sourceVersions -notmatch ',5:' -or $sourceVersions -notmatch ',6:' -or $sourceVersions -notmatch ',7:') {
    throw "Source Flyway set is incomplete (need V1-V7): $sourceVersions"
  }
  if ([string]::IsNullOrWhiteSpace($sourceChecksum) -or $sourceChecksum -ne "1488219560") {
    throw "Source Flyway V1 checksum is '$sourceChecksum', expected 1488219560."
  }
  $sourceVersion = $sourceVersions

  docker exec $source pg_dump -U actionfinance_bootstrap -d actionfinance --schema=actionfinance --no-owner --no-acl | Set-Content -Path $dump -Encoding utf8
  if ($LASTEXITCODE -ne 0) {
    throw "pg_dump failed exit=$LASTEXITCODE"
  }
  if (-not (Select-String -Path $dump -Pattern "flyway_schema_history" -Quiet)) {
    throw "Dump does not contain flyway_schema_history."
  }

  $restore = New-OwnedRestoreContainer "ok"
  $bootstrap = @"
CREATE ROLE actionfinance_migrator LOGIN PASSWORD 'verify-migrator';
CREATE ROLE actionfinance_runtime LOGIN PASSWORD 'verify-runtime';
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_migrator;
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
"@
  $bootstrapFile = Join-Path $work "bootstrap.sql"
  Set-Content -Path $bootstrapFile -Value $bootstrap -Encoding ascii
  Invoke-PsqlFile $restore $bootstrapFile
  Invoke-PsqlFile $restore $dump

  $privFile = Join-Path $root "scripts\dev\restore-runtime-privileges.sql"
  if (-not (Test-Path -LiteralPath $privFile)) {
    throw "Missing complete restore ACL script $privFile"
  }
  Invoke-PsqlFile $restore $privFile

  $restoredVersion = (Invoke-Psql -Name $restore -Sql "select string_agg(version || ':' || checksum, ',' order by installed_rank) from actionfinance.flyway_schema_history where success").Trim()
  $restoredChecksum = (Invoke-Psql -Name $restore -Sql "select checksum from actionfinance.flyway_schema_history where version = '1' and success").Trim()
  if ($restoredVersion -ne $sourceVersion -or $restoredChecksum -ne $sourceChecksum) {
    throw "Restored Flyway version/checksum $restoredVersion/$restoredChecksum does not match source $sourceVersion/$sourceChecksum."
  }

  $ownerRows = @(Invoke-Psql -Name $restore -Sql "select n.nspname || '.' || c.relname || '=' || pg_get_userbyid(c.relowner) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'actionfinance' and c.relkind in ('r','p','v','m','S') order by 1")
  $badOwners = @($ownerRows | Where-Object { $_ -and $_.Trim() -notmatch '=actionfinance_migrator$' })
  if ($badOwners.Count -gt 0) {
    throw "Restored objects not owned by migrator: $($badOwners -join ', ')"
  }
  if (-not ($ownerRows | Where-Object { $_ -match 'flyway_schema_history=actionfinance_migrator' })) {
    throw "flyway_schema_history owner was not reassigned to actionfinance_migrator."
  }
  $schemaOwner = (Invoke-Psql -Name $restore -Sql "select nspowner::regrole from pg_namespace where nspname='actionfinance'").Trim()
  if ($schemaOwner -ne "actionfinance_migrator") {
    throw "Restored schema owner is $schemaOwner, expected actionfinance_migrator."
  }

  $runtimeHistory = (Invoke-Psql -Name $restore -Sql "select checksum from actionfinance.flyway_schema_history where version = '1' and success" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  if ($runtimeHistory -ne $sourceChecksum) {
    throw "Runtime SELECT on flyway_schema_history failed or mismatched: '$runtimeHistory'"
  }
  $titleCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.financial_title" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $historyCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.financial_title_history" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $accountCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.financial_account" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $settlementCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.settlement" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $movementCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.cash_movement" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $userCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.app_user" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $identityCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.external_identity" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $membershipCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.company_membership" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $auditCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.access_admin_audit" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  $sessionCount = (Invoke-Psql -Name $restore -Sql "select count(*) from actionfinance.SPRING_SESSION" -User "actionfinance_runtime" -Password "verify-runtime").Trim()
  if (-not ($titleCount -as [int] -ge 0) -or -not ($historyCount -as [int] -ge 0) -or -not ($accountCount -as [int] -ge 0) -or -not ($settlementCount -as [int] -ge 0) -or -not ($movementCount -as [int] -ge 0) -or -not ($userCount -as [int] -ge 0) -or -not ($identityCount -as [int] -ge 0) -or -not ($membershipCount -as [int] -ge 0) -or -not ($auditCount -as [int] -ge 0) -or -not ($sessionCount -as [int] -ge 0)) {
    throw "Runtime could not read titles/history/accounts/settlements/identity/session after restore."
  }

  $runtimeFlags = (Invoke-Psql -Name $restore -Sql "select rolsuper::text || ',' || rolcreatedb::text || ',' || rolcreaterole::text from pg_roles where rolname='actionfinance_runtime'").Trim()
  if ($runtimeFlags -notmatch '^(f|false),(f|false),(f|false)$') {
    throw "Runtime role is privileged: $runtimeFlags"
  }
  $runtimeOwns = (Invoke-Psql -Name $restore -Sql "select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname='actionfinance' and pg_get_userbyid(c.relowner)='actionfinance_runtime'").Trim()
  if ($runtimeOwns -ne "0") {
    throw "Runtime owns $runtimeOwns objects after restore."
  }
  $runtimeCreate = (Invoke-Psql -Name $restore -Sql "select has_schema_privilege('actionfinance_runtime','actionfinance','CREATE')").Trim()
  if ($runtimeCreate -notmatch '^(f|false)$') {
    throw "Runtime still has CREATE on schema: $runtimeCreate"
  }

  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  docker exec $restore psql -v ON_ERROR_STOP=1 -U actionfinance_runtime -d actionfinance -c "create table actionfinance.forbidden(id int)" 2>$null | Out-Null
  $createExit = $LASTEXITCODE
  $ErrorActionPreference = $previous
  if ($createExit -eq 0) {
    throw "Runtime was able to create a table in the restored schema."
  }

  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  docker exec -e PGPASSWORD=verify-runtime $restore psql -v ON_ERROR_STOP=1 -U actionfinance_runtime -d actionfinance -c "delete from actionfinance.access_admin_audit where false" 2>$null | Out-Null
  $auditDeleteExit = $LASTEXITCODE
  docker exec -e PGPASSWORD=verify-runtime $restore psql -v ON_ERROR_STOP=1 -U actionfinance_runtime -d actionfinance -c "delete from actionfinance.SPRING_SESSION where false" 2>$null | Out-Null
  $sessionDeleteExit = $LASTEXITCODE
  $ErrorActionPreference = $previous
  if ($auditDeleteExit -eq 0) {
    throw "Runtime was able to DELETE access_admin_audit after restore."
  }
  if ($sessionDeleteExit -ne 0) {
    throw "Runtime could not DELETE SPRING_SESSION after restore (session cleanup policy)."
  }

  $probeSql = "BEGIN; CREATE TABLE actionfinance.__af_restore_probe(id int); INSERT INTO actionfinance.__af_restore_probe VALUES (1); ROLLBACK;"
  $null = Invoke-Psql -Name $restore -Sql $probeSql -User "actionfinance_migrator" -Password "verify-migrator"
  $probeLeft = (Invoke-Psql -Name $restore -Sql "select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname='actionfinance' and c.relname='__af_restore_probe'").Trim()
  if ($probeLeft -ne "0") {
    throw "Migrator DDL probe table was not rolled back."
  }

  $migrations = Join-Path $root "database\migrations"
  $flywayName = "$runId-flyway"
  Invoke-Docker @(
    "run", "--rm",
    "--name", $flywayName,
    "--network", "container:$restore",
    "--label", "com.actionfinance.project=actionfinance",
    "--label", "com.actionfinance.role=restore-verify",
    "--label", "com.actionfinance.run=$runId",
    "-v", "${migrations}:/flyway/sql:ro",
    "flyway/flyway:11.10.1",
    "-url=jdbc:postgresql://127.0.0.1:5432/actionfinance",
    "-user=actionfinance_migrator",
    "-password=verify-migrator",
    "-schemas=actionfinance",
    "-locations=filesystem:/flyway/sql",
    "validate"
  )

  $probe = New-OwnedRestoreContainer "fail"
  $bad = Join-Path $work "deliberate-fail.sql"
  Set-Content -Path $bad -Value "do `$`$ begin raise exception 'deliberate restore failure'; end `$`$;" -Encoding ascii
  $failedAsExpected = $false
  try {
    Invoke-PsqlFile $probe $bad
  } catch {
    $failedAsExpected = $true
  }
  if (-not $failedAsExpected) {
    throw "Deliberate restore failure did not produce a non-zero path."
  }

  $okPrinted = $true
  Write-Output "BACKUP_VERIFY_OK source_versions=$sourceVersion source_v1_checksum=$sourceChecksum restored_version=$restoredVersion restored_checksum=$restoredChecksum titles=$titleCount history=$historyCount accounts=$accountCount settlements=$settlementCount movements=$movementCount users=$userCount identities=$identityCount memberships=$membershipCount audit=$auditCount sessions=$sessionCount schema_owner=actionfinance_migrator runtime_select=ok flyway_validate=ok runtime_unprivileged=true deliberate_failure=exit-nonzero"
} finally {
  foreach ($name in $created) {
    $labels = Get-ActionFinanceContainerLabels $name
    if ($labels -and $labels.'com.actionfinance.project' -eq "actionfinance" -and $labels.'com.actionfinance.role' -eq "restore-verify" -and $labels.'com.actionfinance.run' -eq $runId) {
      docker rm -f $name | Out-Null
    }
  }
  $resolvedWork = Assert-SafeVerifyWorkDir
  Remove-Item $resolvedWork -Recurse -Force
}

if (-not $okPrinted) { exit 1 }
