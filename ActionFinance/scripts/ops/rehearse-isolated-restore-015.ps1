#Requires -Version 5.1
# Executable restored-copy rehearsal on a disposable destination.
# Synthetic data only in this prompt. Refuses public RDS, tunnels to it, and the developer volume.
[CmdletBinding()]
param(
  [switch]$Synthetic,
  [string]$JdbcUrl = $env:AF_REHEARSAL_JDBC_URL,
  [string]$ExpectedInstanceId = $env:AF_REHEARSAL_INSTANCE_ID
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$evidenceDir = Join-Path $root "documents\reviews\evidence\pre-publicacao-cadastros-015"
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

$publicMarkers = @(
  "actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com",
  "rds.amazonaws.com"
)
$devVolume = "actionfinance_pgdata_17"
$devContainer = "actionfinance-postgres-17"

function Get-JdbcHost([string]$url) {
  if ($url -match "jdbc:postgresql://([^:/]+)") { return $Matches[1] }
  throw "Cannot parse host from JDBC URL."
}

function Test-PublicOrTunnel([string]$hostName) {
  $lower = $hostName.ToLowerInvariant()
  foreach ($marker in $publicMarkers) {
    if ($lower.Contains($marker.ToLowerInvariant())) { return "hostname:$marker" }
  }
  try {
    $addresses = [System.Net.Dns]::GetHostAddresses($hostName)
    foreach ($addr in $addresses) {
      $entry = [System.Net.Dns]::GetHostEntry($addr)
      $names = @($entry.HostName) + @($entry.Aliases)
      foreach ($name in $names) {
        $n = [string]$name
        if ($n.ToLowerInvariant().Contains("rds.amazonaws.com")) {
          return "resolved:$n"
        }
      }
    }
  } catch {
    return "dns-error:$($_.Exception.Message)"
  }
  return $null
}

function Assert-IsolatedDestination {
  param(
    [string]$Url,
    [string]$DataDirectory,
    [string]$ContainerName,
    [string]$VolumeName,
    [string]$InstanceId,
    [string]$ExpectedId
  )
  $hostName = Get-JdbcHost $Url
  if ($hostName -ne "127.0.0.1" -and $hostName -ne "localhost" -and $hostName -ne $ContainerName) {
    $tunnel = Test-PublicOrTunnel $hostName
    if ($tunnel -and $tunnel.StartsWith("hostname:")) {
      throw "Refused: JDBC host is the public destination ($tunnel)."
    }
    if ($tunnel -and $tunnel.StartsWith("resolved:")) {
      throw "Refused: host $hostName resolves to RDS ($tunnel). A URL without rds.amazonaws.com is not enough."
    }
  }
  if ($DataDirectory -match "rdsdbdata") {
    throw "Refused: data_directory looks like RDS ($DataDirectory)."
  }
  if ($ContainerName -eq $devContainer -or $VolumeName -eq $devVolume) {
    throw "Refused: developer volume/container $devContainer / $devVolume."
  }
  if (-not $ExpectedId -or $InstanceId -ne $ExpectedId) {
    throw "Refused: destination instance id '$InstanceId' does not match expected '$ExpectedId'."
  }
}

if (-not $Synthetic -and -not $JdbcUrl) {
  Write-Host "No dump/restore of origin in this prompt."
  Write-Host "Run with -Synthetic to execute the disposable procedure on local artifacts."
  Write-Host "A JDBC URL without rds.amazonaws.com is not accepted by itself."
  exit 2
}

if ($Synthetic) {
  $net = "actionfinance-restore-015"
  $pgName = "actionfinance-restore-015-pg"
  $vol = "actionfinance_restore_015"
  $instanceId = "af-restore-015-synthetic"
  $hostPort = 55440
  $initSql = Join-Path $root "backend\src\test\resources\test-init.sql"
  $migrations = Join-Path $root "database\migrations"
  $result = [ordered]@{
    recordedAt = (Get-Date).ToUniversalTime().ToString("o")
    mode       = "synthetic"
    dumpUsed   = $false
    originTouched = $false
  }

  function Remove-Restore {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    docker rm -f $pgName 2>$null | Out-Null
    docker network rm $net 2>$null | Out-Null
    docker volume rm $vol 2>$null | Out-Null
    $ErrorActionPreference = $prev
  }

  function Invoke-Psql([string]$Sql, [string]$User = "actionfinance_migrator", [string]$Password = "migrator-test") {
    $out = & docker exec -e "PGPASSWORD=$Password" $pgName psql -U $User -d actionfinance -v ON_ERROR_STOP=1 -t -A -c $Sql
    if ($LASTEXITCODE -ne 0) { throw "psql failed: $Sql" }
    return ($out | Out-String).Trim()
  }

  function Invoke-Flyway([string]$Target) {
    $args = @(
      "run", "--rm", "--network", $net,
      "-v", "${migrations}:/flyway/sql:ro",
      "flyway/flyway:11.10.1",
      "-url=jdbc:postgresql://${pgName}:5432/actionfinance",
      "-user=actionfinance_migrator",
      "-password=migrator-test",
      "-schemas=actionfinance",
      "-defaultSchema=actionfinance",
      "-connectRetries=20",
      "-target=$Target",
      "migrate"
    )
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "flyway target=$Target exit=$LASTEXITCODE" }
  }

  try {
    Remove-Restore
    docker volume create $vol | Out-Null
    docker network create --internal $net | Out-Null
    docker run -d --name $pgName --network $net --network-alias $pgName `
      -p "127.0.0.1:${hostPort}:5432" `
      -e POSTGRES_DB=actionfinance -e POSTGRES_USER=actionfinance_bootstrap -e POSTGRES_PASSWORD=bootstrap-test `
      -v "${vol}:/var/lib/postgresql/data" `
      -v "${initSql}:/docker-entrypoint-initdb.d/01-roles.sql:ro" `
      --label "com.actionfinance.role=restore-015" `
      --label "com.actionfinance.instance=$instanceId" `
      postgres:17.6 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "postgres start failed" }

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
      docker exec $pgName pg_isready -U actionfinance_bootstrap -d actionfinance 2>$null | Out-Null
      if ($LASTEXITCODE -eq 0) { $ready = $true; break }
      Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw "restore postgres not ready" }

    $dataDir = Invoke-Psql "show data_directory;" "actionfinance_bootstrap" "bootstrap-test"
    $jdbc = "jdbc:postgresql://127.0.0.1:${hostPort}/actionfinance"
    Assert-IsolatedDestination -Url $jdbc -DataDirectory $dataDir -ContainerName $pgName -VolumeName $vol -InstanceId $instanceId -ExpectedId $instanceId
    $result.destination = [ordered]@{
      jdbc       = $jdbc
      container  = $pgName
      volume     = $vol
      dataDir    = $dataDir
      instanceId = $instanceId
      verifiedBeforeWrite = $true
    }

    Invoke-Flyway "13"
    $tenant = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0151"
    $company = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0152"
    $actor = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0153"
    $party = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0154"
    $category = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0155"
    $title = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa0156"
    Invoke-Psql @"
insert into actionfinance.tenant (id, code, name, active, created_at, updated_at, version)
values ('$tenant','T015','Tenant 015',true,now(),now(),1);
insert into actionfinance.company (id, tenant_id, code, name, active, is_demo, business_timezone, created_at, updated_at, version)
values ('$company','$tenant','C015','Empresa 015',true,false,'America/Sao_Paulo',now(),now(),1);
insert into actionfinance.counterparty (
  id, tenant_id, company_id, code, name, role, active, version, created_at, updated_at, created_by, updated_by)
values ('$party','$tenant','$company','CTP-$party','Fornecedor sintetico 015','SUPPLIER',true,1,now(),now(),'$actor','$actor');
insert into actionfinance.financial_category (
  id, tenant_id, company_id, code, name, direction, active, version, created_at, updated_at, created_by, updated_by)
values ('$category','$tenant','$company','CAT-015','Insumos 015','PAYABLE',true,1,now(),now(),'$actor','$actor');
insert into actionfinance.financial_title (
  id, tenant_id, company_id, reference, direction, status, description,
  counterparty_id, category_id, amount_minor, currency, competence_date, due_date,
  origin_kind, version, created_at, updated_at, created_by, updated_by)
values ('$title','$tenant','$company','REF-015','PAYABLE','DRAFT','Compra 015',
  '$party','$category',2500,'BRL','2026-10-01','2026-10-10','MANUAL',1,now(),now(),'$actor','$actor');
"@

    $before = [ordered]@{
      flyway     = Invoke-Psql "select string_agg(version, ',' order by installed_rank) from actionfinance.flyway_schema_history where success;"
      parties    = Invoke-Psql "select count(*) from actionfinance.counterparty;"
      titles     = Invoke-Psql "select count(*) from actionfinance.financial_title;"
      titleLink  = Invoke-Psql "select id||'|'||counterparty_id||'|'||amount_minor from actionfinance.financial_title where id='$title';"
      partyName  = Invoke-Psql "select id||'|'||name||'|'||role from actionfinance.counterparty where id='$party';"
    }
    $result.before = $before

    Invoke-Flyway "19"

    $after = [ordered]@{
      flyway          = Invoke-Psql "select string_agg(version, ',' order by installed_rank) from actionfinance.flyway_schema_history where success;"
      v13checksum     = Invoke-Psql "select checksum from actionfinance.flyway_schema_history where version='13';"
      parties         = Invoke-Psql "select count(*) from actionfinance.counterparty;"
      titles          = Invoke-Psql "select count(*) from actionfinance.financial_title;"
      titleLink       = Invoke-Psql "select id||'|'||counterparty_id||'|'||amount_minor from actionfinance.financial_title where id='$title';"
      partyName       = Invoke-Psql "select id||'|'||name||'|'||role||'|'||document_pending from actionfinance.counterparty where id='$party';"
      claims          = Invoke-Psql "select count(*) from actionfinance.counterparty_document_claim;"
      connectionNulls = Invoke-Psql "select count(*) from actionfinance.counterparty_external_identity where connection_key is null;"
      grantDelete     = Invoke-Psql "select count(*) from information_schema.role_table_grants where table_schema='actionfinance' and table_name='counterparty' and privilege_type='DELETE' and grantee='actionfinance_runtime';"
    }
    $result.after = $after
    $result.invariants = [ordered]@{
      idsPreserved          = ($before.titleLink -eq $after.titleLink -and $before.partyName.StartsWith("$party|Fornecedor sintetico 015|SUPPLIER"))
      countsPreserved       = ($before.parties -eq $after.parties -and $before.titles -eq $after.titles)
      schemaV19             = ($after.flyway -match "(^|,)19(,|$)")
      v13ChecksumUnchanged  = ($after.v13checksum -ne "")
      legacyDocumentPending = ($after.partyName -match "t$" -or $after.partyName -match "true$")
      noRuntimeDelete       = ($after.grantDelete -eq "0")
      connectionKeyNotNull  = ($after.connectionNulls -eq "0")
    }
    $allOk = $true
    foreach ($key in $result.invariants.Keys) {
      if (-not $result.invariants[$key]) { $allOk = $false }
    }
    $result.syntheticRehearsal = $(if ($allOk) { "approved-in-rehearsal" } else { "failed" })
    $result.restoredOriginCopy = "not-executed"
    $result.note = "014 printed instructions only. This run migrated synthetic V13 data with the candidate V14-V19 files. It is not a restored origin dump."
  }
  catch {
    $result.error = $_.Exception.Message
    $result.syntheticRehearsal = "failed"
    $result.restoredOriginCopy = "not-executed"
  }
  finally {
    Remove-Restore
  }

  $out = Join-Path $evidenceDir "restore-sintetico.json"
  $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding utf8
  Write-Host "Wrote $out"
  $result | ConvertTo-Json -Depth 6
  if ($result.syntheticRehearsal -ne "approved-in-rehearsal") { exit 1 }
  exit 0
}

Assert-IsolatedDestination -Url $JdbcUrl -DataDirectory "unknown" -ContainerName "unknown" -VolumeName "unknown" -InstanceId $ExpectedInstanceId -ExpectedId $ExpectedInstanceId
Write-Host "URL parsed. Refusing to dump or restore origin in this prompt."
exit 2
