#Requires -Version 5.1
# Isolated rollback of the published previous image against disposable V19.
# Does not touch the public service, the developer volume, or production credentials.
[CmdletBinding()]
param(
  [string]$PreviousImage = "actionfinance:sair-cognito-010-4e556ecd",
  [string]$ExpectedDigest = "sha256:06e067e772f65d37a0cf43c53022e32d9e0a76eb9841cfebaf75d684b28f953c"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$evidenceDir = Join-Path $root "documents\reviews\evidence\pre-publicacao-cadastros-015"
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null

$net = "actionfinance-rehearsal-015"
$pgName = "actionfinance-rehearsal-015-pg"
$appWeb = "actionfinance-rehearsal-015-web"
$appFly = "actionfinance-rehearsal-015-flyway"
$vol = "actionfinance_rehearsal_015"
$hostPort = 55439
$appPort = 18091
$companyId = "11111111-1111-4111-a111-111111111111"
$supplierId = "11111111-aaaa-4111-a111-111111111102"
$token = "operator-demo-token-aaaaaaaaaaaaaaaaaaaa"
$viewerA = "viewer-a-demo-token-bbbbbbbbbbbbbbbbbbbb"
$viewerB = "viewer-b-demo-token-cccccccccccccccccccc"
$initSql = Join-Path $root "backend\src\test\resources\test-init.sql"
$migrations = Join-Path $root "database\migrations"

function Invoke-Docker {
  param([string[]]$DockerArgs)
  & docker @DockerArgs
  if ($LASTEXITCODE -ne 0) { throw "docker $($DockerArgs -join ' ') exit=$LASTEXITCODE" }
}

function Remove-Rehearsal {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  foreach ($name in @($appWeb, $appFly, $pgName)) {
    docker rm -f $name 2>$null | Out-Null
  }
  docker network rm $net 2>$null | Out-Null
  docker volume rm $vol 2>$null | Out-Null
  $ErrorActionPreference = $prev
}

function Invoke-AppHttp {
  param(
    [string]$Container,
    [string]$Method = "GET",
    [string]$Url,
    [string]$Body = "",
    [string]$Auth = ""
  )
  $curl = @(
    "run", "--rm", "--network", "container:$Container"
  )
  $bodyFile = $null
  if ($Body) {
    $bodyFile = Join-Path $evidenceDir ("curl-body-" + [guid]::NewGuid().ToString("n") + ".json")
    [System.IO.File]::WriteAllText($bodyFile, $Body, (New-Object System.Text.UTF8Encoding $false))
    $curl += @("-v", "${bodyFile}:/tmp/body.json:ro")
  }
  $curl += @(
    "curlimages/curl:8.10.1",
    "-sS", "-w", "`nHTTP_CODE:%{http_code}",
    "-X", $Method, $Url
  )
  if ($Auth) {
    $curl += @("-H", "Authorization: Bearer $Auth")
  }
  if ($Body) {
    $curl += @("-H", "Content-Type: application/json", "--data-binary", "@/tmp/body.json")
  }
  $out = & docker @curl
  $code = $LASTEXITCODE
  if ($bodyFile -and (Test-Path $bodyFile)) { Remove-Item -LiteralPath $bodyFile -Force }
  if ($code -ne 0) { throw "curl $Method $Url exit=$code" }
  return ($out | Out-String)
}

function Wait-AppLive([string]$Container, [int]$Seconds) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    try {
      $raw = Invoke-AppHttp -Container $Container -Url "http://127.0.0.1:8091/actuator/health/liveness"
      if ($raw -match "HTTP_CODE:200") { return $true }
    } catch { }
    Start-Sleep -Seconds 2
  } while ((Get-Date) -lt $deadline)
  return $false
}

function Invoke-Psql([string]$Sql, [string]$User = "actionfinance_runtime", [string]$Password = "runtime-test") {
  $env:PGPASSWORD = $Password
  $out = & docker exec -e "PGPASSWORD=$Password" $pgName psql -U $User -d actionfinance -v ON_ERROR_STOP=1 -t -A -c $Sql
  if ($LASTEXITCODE -ne 0) { throw "psql failed: $Sql" }
  return ($out | Out-String).Trim()
}

function Invoke-Flyway([string]$Target = "") {
  $flyArgs = @(
    "run", "--rm",
    "--network", $net,
    "-v", "${migrations}:/flyway/sql:ro",
    "flyway/flyway:11.10.1",
    "-url=jdbc:postgresql://${pgName}:5432/actionfinance",
    "-user=actionfinance_migrator",
    "-password=migrator-test",
    "-schemas=actionfinance",
    "-defaultSchema=actionfinance",
    "-connectRetries=20"
  )
  if ($Target) { $flyArgs += "-target=$Target" }
  $flyArgs += "migrate"
  & docker @flyArgs
  if ($LASTEXITCODE -ne 0) { throw "flyway migrate target=$Target exit=$LASTEXITCODE" }
}

$result = [ordered]@{
  recordedAt = (Get-Date).ToUniversalTime().ToString("o")
  prompt     = "ACTIONFINANCE_PROMPT_PRE_PUBLICACAO_CADASTROS_015"
  previousImage = $PreviousImage
  expectedDigest = $ExpectedDigest
  publicServiceAltered = $false
}

try {
  $inspect = docker image inspect $PreviousImage --format "{{.Id}}|{{json .RepoDigests}}"
  if ($LASTEXITCODE -ne 0) { throw "Previous image missing: $PreviousImage" }
  $parts = $inspect.Split("|", 2)
  $result.localImageId = $parts[0]
  $result.localRepoDigests = $parts[1]
  $digestOk = $parts[0].Contains("06e067e772f65d37a0cf43c53022e32d9e0a76eb9841cfebaf75d684b28f953c") -or $parts[1].Contains($ExpectedDigest)
  $result.digestMatchesPublished = [bool]$digestOk
  if (-not $digestOk) {
    throw "Local image is not the published digest $ExpectedDigest. Equivalence not proven."
  }

  Remove-Rehearsal
  Invoke-Docker @("volume", "create", $vol)
  Invoke-Docker @("network", "create", "--internal", $net)
  Invoke-Docker @(
    "run", "-d", "--name", $pgName,
    "--network", $net,
    "--network-alias", $pgName,
    "-p", "127.0.0.1:${hostPort}:5432",
    "-e", "POSTGRES_DB=actionfinance",
    "-e", "POSTGRES_USER=actionfinance_bootstrap",
    "-e", "POSTGRES_PASSWORD=bootstrap-test",
    "-e", "TZ=UTC",
    "-v", "${vol}:/var/lib/postgresql/data",
    "-v", "${initSql}:/docker-entrypoint-initdb.d/01-roles.sql:ro",
    "--label", "com.actionfinance.role=rehearsal-015",
    "--label", "com.actionfinance.project=actionfinance",
    "postgres:17.6"
  )

  $ready = $false
  for ($i = 0; $i -lt 30; $i++) {
    docker exec $pgName pg_isready -U actionfinance_bootstrap -d actionfinance 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 2
  }
  if (-not $ready) { throw "Disposable postgres did not become ready." }

  $dataDir = Invoke-Psql "show data_directory;" "actionfinance_bootstrap" "bootstrap-test"
  $result.destination = [ordered]@{
    container = $pgName
    volume    = $vol
    dataDir   = $dataDir
    hostPort  = $hostPort
    refusedPublicRds = $true
    refusedDevVolume = $true
  }
  if ($dataDir -match "rdsdbdata" -or $vol -eq "actionfinance_pgdata_17") {
    throw "Destination identity refused."
  }

  Invoke-Flyway "19"
  $schema = Invoke-Psql "select string_agg(version, ',' order by installed_rank) from actionfinance.flyway_schema_history where success;" "actionfinance_migrator" "migrator-test"
  $result.schemaAfterCandidateMigrate = $schema
  if ($schema -notmatch "(^|,)19(,|$)") { throw "Candidate migrate did not reach V19: $schema" }

  $webEnv = @(
    "-e", "SPRING_PROFILES_ACTIVE=local-demo",
    "-e", "SERVER_ADDRESS=127.0.0.1",
    "-e", "ACTIONFINANCE_BIND_ADDRESS=127.0.0.1",
    "-e", "ACTIONFINANCE_BACKEND_PORT=8091",
    "-e", "ACTIONFINANCE_DATASOURCE_URL=jdbc:postgresql://${pgName}:5432/actionfinance",
    "-e", "ACTIONFINANCE_RUNTIME_USERNAME=actionfinance_runtime",
    "-e", "ACTIONFINANCE_RUNTIME_PASSWORD=runtime-test",
    "-e", "ACTIONFINANCE_MIGRATOR_USERNAME=actionfinance_migrator",
    "-e", "ACTIONFINANCE_MIGRATOR_PASSWORD=migrator-test",
    "-e", "ACTIONFINANCE_DEMO_AUTH_ENABLED=true",
    "-e", "ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A=$token",
    "-e", "ACTIONFINANCE_DEMO_TOKEN_VIEWER_A=$viewerA",
    "-e", "ACTIONFINANCE_DEMO_TOKEN_VIEWER_B=$viewerB",
    "-e", "ACTIONFINANCE_OIDC_ENABLED=false",
    "-e", "ACTIONFINANCE_RECEIPT_SYNC_ENABLED=false",
    "-e", "ACTIONFINANCE_INTEGRATION_HOMOLOG=false",
    "-e", "ACTIONFINANCE_SPIDER_BASE_URL=",
    "-e", "ACTIONFINANCE_SPIDER_SECRET=",
    "-e", "ACTIONFINANCE_PUBLIC_ORIGIN=http://127.0.0.1:8091"
  )

  Invoke-Docker (@(
    "run", "-d", "--name", $appWeb,
    "--network", $net
  ) + $webEnv + @(
    "-e", "ACTIONFINANCE_FLYWAY_ENABLED=false",
    "-e", "ACTIONFINANCE_READINESS_INCLUDE=readinessState,db",
    $PreviousImage
  ))

  $webUp = Wait-AppLive $appWeb 90
  $webLogs = docker logs $appWeb 2>&1 | Out-String
  Set-Content -LiteralPath (Join-Path $evidenceDir "rollback-web-flyway-off.log") -Value $webLogs -Encoding utf8
  $result.webMode = [ordered]@{
    flywayEnabled = $false
    started       = $webUp
    note          = "Same switch as production web: ACTIONFINANCE_FLYWAY_ENABLED=false. Not a validation bypass invented for this essay."
  }
  if (-not $webUp) {
    $result.webMode.logsTail = ($webLogs -split "`n" | Select-Object -Last 40) -join "`n"
    throw "Previous image did not become live with Flyway disabled."
  }

  $listUrl = "http://127.0.0.1:8091/api/v1/catalogs/counterparties?companyId=$companyId"
  $listRaw = Invoke-AppHttp -Container $appWeb -Url $listUrl -Auth $token
  if ($listRaw -notmatch "HTTP_CODE:200") { throw "Legacy read failed: $listRaw" }
  $listJson = ($listRaw -replace "HTTP_CODE:\d+", "").Trim()
  $list = $listJson | ConvertFrom-Json
  $result.webMode.readCount = @($list).Count
  if (@($list).Count -lt 1) { throw "Legacy read returned no counterparties after demo seed." }

  Invoke-Psql @"
update actionfinance.counterparty
   set person_kind='LEGAL',
       document_country='BR',
       document_type='CNPJ',
       document_number='77.000.000/0001-16',
       document_number_normalized='77000000000116',
       document_pending=false
 where id='$supplierId';
insert into actionfinance.counterparty_document_claim (
  tenant_id, company_id, document_country, document_type, document_number_normalized,
  counterparty_id, unit_id, mirrored, created_at)
select tenant_id, company_id, document_country, document_type, document_number_normalized,
       id, null, false, now()
  from actionfinance.counterparty
 where id='$supplierId'
on conflict do nothing;
"@ "actionfinance_migrator" "migrator-test"

  $before = Invoke-Psql "select document_number_normalized||'|'||document_pending||'|'||name from actionfinance.counterparty where id='$supplierId';"
  $result.webMode.fieldsBeforeEdit = $before

  $createdRaw = Invoke-AppHttp -Container $appWeb -Method "POST" -Url $listUrl -Auth $token -Body '{"name":"Fornecedor legado 015","role":"SUPPLIER"}'
  if ($createdRaw -notmatch "HTTP_CODE:200") { throw "Legacy create failed: $createdRaw" }
  $created = (($createdRaw -replace "HTTP_CODE:\d+", "").Trim() | ConvertFrom-Json)
  $result.webMode.legacyCreateId = [string]$created.id
  $result.webMode.legacyCreateName = [string]$created.name

  $current = Invoke-Psql "select version from actionfinance.counterparty where id='$supplierId';"
  $patchBody = '{"name":"Moinho editado pela imagem anterior","active":true,"version":' + $current + '}'
  $updatedRaw = Invoke-AppHttp -Container $appWeb -Method "PATCH" -Url "http://127.0.0.1:8091/api/v1/catalogs/counterparties/${supplierId}?companyId=$companyId" -Auth $token -Body $patchBody
  if ($updatedRaw -notmatch "HTTP_CODE:200") { throw "Legacy edit failed: $updatedRaw" }
  $updated = (($updatedRaw -replace "HTTP_CODE:\d+", "").Trim() | ConvertFrom-Json)
  $result.webMode.legacyEditName = [string]$updated.name

  $after = Invoke-Psql "select document_number_normalized||'|'||document_pending||'|'||name from actionfinance.counterparty where id='$supplierId';"
  $claim = Invoke-Psql "select count(*) from actionfinance.counterparty_document_claim where document_number_normalized='77000000000116';"
  $result.webMode.fieldsAfterEdit = $after
  $result.webMode.claimCount = $claim
  $result.webMode.newFieldsPreserved = ($after -match "77000000000116\|f\|") -or ($after -match "77000000000116\|false\|")
  if ($after -notmatch "77000000000116") {
    $result.webMode.newFieldsPreserved = $false
  } else {
    $result.webMode.newFieldsPreserved = $true
  }

  docker rm -f $appWeb | Out-Null

  Invoke-Docker (@(
    "run", "-d", "--name", $appFly,
    "--network", $net
  ) + $webEnv + @(
    "-e", "ACTIONFINANCE_FLYWAY_ENABLED=true",
    "-e", "ACTIONFINANCE_READINESS_INCLUDE=readinessState,db,flywaySchema",
    $PreviousImage
  ))

  Start-Sleep -Seconds 20
  $flyLogs = docker logs $appFly 2>&1 | Out-String
  Set-Content -LiteralPath (Join-Path $evidenceDir "rollback-migrate-flyway-on.log") -Value $flyLogs -Encoding utf8
  $running = docker inspect $appFly --format "{{.State.Running}}"
  $exitCode = docker inspect $appFly --format "{{.State.ExitCode}}"
  $validateFailed = $flyLogs -match "Validate failed|not resolved locally|Migration checksum mismatch|FlywayException"
  $result.migrateMode = [ordered]@{
    flywayEnabled   = $true
    stillRunning    = ($running -eq "true")
    exitCode        = $exitCode
    validateFailed  = [bool]$validateFailed
    note            = "Previous jar classpath ends at V12. No ignore-missing-migrations. Failure is recorded, not bypassed."
  }
  if ($validateFailed) {
    $hit = ($flyLogs -split "`n" | Where-Object { $_ -match "Validate failed|not resolved locally|Flyway" } | Select-Object -First 8) -join "`n"
    $result.migrateMode.evidence = $hit
  }

  if ($result.webMode.started -and $result.webMode.newFieldsPreserved -and $result.webMode.legacyCreateId) {
    $result.directImageRollbackWeb = "approved-in-rehearsal"
  } else {
    $result.directImageRollbackWeb = "failed"
  }
  if ($validateFailed) {
    $result.directImageRollbackMigrateTask = "failed"
  } elseif ($running -eq "true") {
    $result.directImageRollbackMigrateTask = "approved-in-rehearsal"
  } else {
    $result.directImageRollbackMigrateTask = "failed"
  }

  $result.compatibleAlternative = [ordered]@{
    summary = 'After V14-V19, roll back only the web task (Flyway off), never the migrate task of the previous image. Schema rollback remains a restore with later-write reconciliation, not automatic.'
    tested  = 'web Flyway-off against disposable V19: read, POST name+role, PATCH name, document/claim intact.'
    notAnAutomaticRestore = $true
  }
}
catch {
  $result.error = $_.Exception.Message
  $result.directImageRollbackWeb = $(if ($result.directImageRollbackWeb) { $result.directImageRollbackWeb } else { "failed" })
}
finally {
  Remove-Rehearsal
}

$out = Join-Path $evidenceDir "rollback-ensaio.json"
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $out -Encoding utf8
Write-Host "Wrote $out"
$result | ConvertTo-Json -Depth 6
if ($result.error -and $result.directImageRollbackWeb -ne "approved-in-rehearsal") { exit 1 }
exit 0
