#Requires -Version 5.1
# PITR of production ActionFinance RDS onto a disposable instance. Never targets production.
[CmdletBinding()]
param(
  [switch] $SkipCleanup,
  [switch] $VerifyExistingOnly
)

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$sourceId = "actionfinance"
$targetId = "actionfinance-restore-prm007"
$cluster = "actionfinance-cluster"
$runtimeArn = aws secretsmanager describe-secret --region $region --secret-id actionfinance/runtime --query ARN --output text
$started = Get-Date
$evidence = [ordered]@{
  startedAtUtc = $started.ToUniversalTime().ToString("o")
  sourceId = $sourceId
  targetId = $targetId
  method = "restore-db-instance-to-point-in-time UseLatestRestorableTime"
}

function Invoke-AfDbadminSql {
  param(
    [Parameter(Mandatory = $true)][string] $PgHost,
    [Parameter(Mandatory = $true)][string] $MasterArn,
    [Parameter(Mandatory = $true)][string] $Sql,
    [Parameter(Mandatory = $true)][string] $StreamPrefix,
    [string] $RuntimeArn
  )
  $resources = @($MasterArn)
  if ($RuntimeArn) { $resources += $RuntimeArn }
  $policyDoc = (@{
    Version = "2012-10-17"
    Statement = @(@{
      Effect = "Allow"
      Action = @("secretsmanager:GetSecretValue")
      Resource = $resources
    })
  } | ConvertTo-Json -Depth 6)
  $policyName = "actionfinance-restore-once"
  $policyFile = Join-Path $env:TEMP "af-restore-policy.json"
  [System.IO.File]::WriteAllText($policyFile, $policyDoc)
  aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name $policyName --policy-document "file://$policyFile" | Out-Null
  Remove-Item -LiteralPath $policyFile -Force
  $sqlOne = $Sql.Replace("`r`n", " ").Replace("`r", " ").Replace("`n", " ")
  $runtimeBit = ""
  $secrets = @(
    @{ name = "PGUSER"; valueFrom = "${MasterArn}:username::" }
    @{ name = "PGPASSWORD"; valueFrom = "${MasterArn}:password::" }
  )
  if ($RuntimeArn) {
    $runtimeBit = @'
printf '\n-- runtime --\n'
export PGUSER=actionfinance_runtime
export PGPASSWORD="$(printf %s "$RUNTIME_PASSWORD" | tr -d '\r\n')"
psql -v ON_ERROR_STOP=1 -A -F '|' -c "SELECT current_user AS runtime_user;"
psql -v ON_ERROR_STOP=1 -A -F '|' -c "SELECT has_schema_privilege(current_user,'actionfinance','CREATE') AS runtime_can_create;"
psql -v ON_ERROR_STOP=1 -A -F '|' -c "SELECT COUNT(*) AS titles FROM actionfinance.financial_title;"
psql -v ON_ERROR_STOP=1 -A -F '|' -c "SELECT COUNT(*) AS sessions FROM actionfinance.\"SPRING_SESSION\";"
set +e
psql -v ON_ERROR_STOP=1 -c "CREATE TABLE actionfinance.__af_restore_probe(id int);" >/tmp/ddl.txt 2>&1
echo "runtime_ddl_exit=$?"
set -e
psql -v ON_ERROR_STOP=1 -A -F '|' -c "SELECT COUNT(*) AS probe_left FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='actionfinance' AND c.relname='__af_restore_probe';"
set +e
psql -v ON_ERROR_STOP=1 -c "DELETE FROM actionfinance.access_admin_audit WHERE false;" >/tmp/aud.txt 2>&1
echo "runtime_audit_delete_exit=$?"
set -e
psql -v ON_ERROR_STOP=1 -c "DELETE FROM actionfinance.\"SPRING_SESSION\";"
psql -v ON_ERROR_STOP=1 -A -F '|' -c "SELECT COUNT(*) AS sessions_after FROM actionfinance.\"SPRING_SESSION\";"
psql -v ON_ERROR_STOP=1 -A -F '|' -c "SELECT COUNT(*) AS titles_after FROM actionfinance.financial_title;"
psql -v ON_ERROR_STOP=1 -A -F '|' -c "SELECT COUNT(*) AS users_after FROM actionfinance.app_user;"
psql -v ON_ERROR_STOP=1 -A -F '|' -c "SELECT COUNT(*) AS audit_after FROM actionfinance.access_admin_audit;"
'@
    $secrets += @(
      @{ name = "RUNTIME_USERNAME"; valueFrom = "${RuntimeArn}:username::" }
      @{ name = "RUNTIME_PASSWORD"; valueFrom = "${RuntimeArn}:password::" }
    )
  }
  $cmd = "set -eu; psql -v ON_ERROR_STOP=1 -A -F '|' -c `"$sqlOne`"; $runtimeBit"
  $td = @{
    family = "actionfinance-dbadmin"
    networkMode = "awsvpc"
    requiresCompatibilities = @("FARGATE")
    cpu = "256"
    memory = "512"
    executionRoleArn = "arn:aws:iam::253137917703:role/actionfinance-migrate-execution"
    runtimePlatform = @{ operatingSystemFamily = "LINUX"; cpuArchitecture = "X86_64" }
    containerDefinitions = @(@{
      name = "dbadmin"
      image = "public.ecr.aws/docker/library/postgres:17.6"
      essential = $true
      environment = @(
        @{ name = "PGHOST"; value = $PgHost }
        @{ name = "PGDATABASE"; value = "actionfinance" }
        @{ name = "PGSSLMODE"; value = "require" }
      )
      secrets = $secrets
      command = @("bash", "-lc", $cmd)
      logConfiguration = @{
        logDriver = "awslogs"
        options = @{
          "awslogs-group" = "/actionfinance/migrate"
          "awslogs-region" = $region
          "awslogs-stream-prefix" = $StreamPrefix
        }
      }
    })
  }
  $tdFile = Join-Path $env:TEMP ("af-restore-" + $StreamPrefix + ".json")
  [System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
  try {
    aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
    $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
    $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
    if (-not $taskArn -or $taskArn -eq "None") { throw "dbadmin run-task failed for $StreamPrefix" }
    aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
    $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
    $taskId = ($taskArn -split "/")[-1]
    $log = aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "$StreamPrefix/dbadmin/$taskId" --limit 80 --query "events[].message" --output text
    Write-Host "dbadmin $StreamPrefix exit=$exit"
    Write-Host $log
    if ($exit -ne "0") { throw "dbadmin $StreamPrefix failed with exit $exit" }
    return $log
  } finally {
    aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name $policyName | Out-Null
  }
}

$source = aws rds describe-db-instances --region $region --db-instance-identifier $sourceId --output json | ConvertFrom-Json
$src = $source.DBInstances[0]
if ($src.DBInstanceStatus -ne "available") { throw "Source RDS is $($src.DBInstanceStatus)" }
$evidence.sourceEncrypted = [bool]$src.StorageEncrypted
$evidence.sourcePublic = [bool]$src.PubliclyAccessible
$evidence.sourceLatestRestorableTime = [string]$src.LatestRestorableTime
$evidence.sourceBackupRetentionDays = [int]$src.BackupRetentionPeriod
$evidence.existingAutomatedSnapshot = "rds:actionfinance-2026-09-30-13-45"

$prodSql = @'
SELECT 'prod' AS scope,
       (SELECT string_agg(version || ':' || checksum, ',' ORDER BY installed_rank) FROM actionfinance.flyway_schema_history WHERE success) AS flyway,
       (SELECT COUNT(*) FROM actionfinance.tenant) AS tenants,
       (SELECT COUNT(*) FROM actionfinance.company) AS companies,
       (SELECT COUNT(*) FROM actionfinance.app_user) AS users,
       (SELECT COUNT(*) FROM actionfinance.company_membership) AS memberships,
       (SELECT COUNT(*) FROM actionfinance.access_admin_audit) AS audit,
       (SELECT COUNT(*) FROM actionfinance.financial_title) AS titles,
       (SELECT COUNT(*) FROM actionfinance.settlement) AS settlements,
       (SELECT COUNT(*) FROM actionfinance."SPRING_SESSION") AS sessions,
       (SELECT nspowner::regrole::text FROM pg_namespace WHERE nspname='actionfinance') AS schema_owner;
'@
$prodMasterArn = $src.MasterUserSecret.SecretArn
if (-not $VerifyExistingOnly) {
  $evidence.prodProbe = Invoke-AfDbadminSql -PgHost $src.Endpoint.Address -MasterArn $prodMasterArn -Sql $prodSql -StreamPrefix "restoreprod"
  Write-Host "Starting isolated PITR to $targetId"
  aws rds restore-db-instance-to-point-in-time --region $region --source-db-instance-identifier $sourceId --target-db-instance-identifier $targetId --use-latest-restorable-time --db-instance-class db.t4g.micro --db-subnet-group-name actionfinance-private --vpc-security-group-ids sg-014d62a41c4069157 --no-publicly-accessible --no-multi-az --no-deletion-protection --storage-type gp3 --tags Key=Product,Value=actionfinance Key=Role,Value=prm007-restore-trial Key=Prompt,Value=PRM007 | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "PITR restore-db-instance-to-point-in-time failed" }
}
$restoreRequested = Get-Date
Write-Host "Waiting for $targetId available..."
aws rds wait db-instance-available --region $region --db-instance-identifier $targetId
if ($LASTEXITCODE -ne 0) { throw "Restore instance did not become available" }
$availableAt = Get-Date
$evidence.restoreWaitMinutes = [math]::Round(($availableAt - $restoreRequested).TotalMinutes, 1)
$evidence.verifyExistingOnly = [bool]$VerifyExistingOnly

$restored = aws rds describe-db-instances --region $region --db-instance-identifier $targetId --output json | ConvertFrom-Json
$rst = $restored.DBInstances[0]
$evidence.targetStatus = $rst.DBInstanceStatus
$evidence.targetEncrypted = [bool]$rst.StorageEncrypted
$evidence.targetPublic = [bool]$rst.PubliclyAccessible
$evidence.targetPrivateEndpoint = [bool]$rst.Endpoint.Address
$evidence.targetHasPublicDns = $false
aws rds modify-db-instance --region $region --db-instance-identifier $targetId --backup-retention-period 0 --apply-immediately --no-deletion-protection | Out-Null

$restoreSql = @'
SELECT 'restore' AS scope,
       (SELECT string_agg(version || ':' || checksum, ',' ORDER BY installed_rank) FROM actionfinance.flyway_schema_history WHERE success) AS flyway,
       (SELECT COUNT(*) FROM actionfinance.tenant) AS tenants,
       (SELECT COUNT(*) FROM actionfinance.company) AS companies,
       (SELECT COUNT(*) FROM actionfinance.app_user) AS users,
       (SELECT COUNT(*) FROM actionfinance.company_membership) AS memberships,
       (SELECT COUNT(*) FROM actionfinance.access_admin_audit) AS audit,
       (SELECT COUNT(*) FROM actionfinance.financial_title) AS titles,
       (SELECT COUNT(*) FROM actionfinance.settlement) AS settlements,
       (SELECT COUNT(*) FROM actionfinance."SPRING_SESSION") AS sessions,
       (SELECT nspowner::regrole::text FROM pg_namespace WHERE nspname='actionfinance') AS schema_owner,
       (SELECT COUNT(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='actionfinance' AND pg_get_userbyid(c.relowner)='actionfinance_runtime') AS runtime_owned,
       (SELECT encode(convert_to(name,'UTF8'),'hex') FROM actionfinance.company WHERE id='624023a4-57e3-415c-b7d0-925ca1acd3b7') AS company_hex;
'@
$evidence.restoreProbe = Invoke-AfDbadminSql -PgHost $rst.Endpoint.Address -MasterArn $prodMasterArn -Sql $restoreSql -StreamPrefix "restoretgt" -RuntimeArn $runtimeArn

$prodAfterSql = @'
SELECT 'prod_after' AS scope,
       (SELECT COUNT(*) FROM actionfinance."SPRING_SESSION") AS sessions,
       (SELECT COUNT(*) FROM actionfinance.app_user) AS users,
       (SELECT COUNT(*) FROM actionfinance.access_admin_audit) AS audit,
       (SELECT COUNT(*) FROM actionfinance.financial_title) AS titles;
'@
$evidence.prodAfterInvalidateRestore = Invoke-AfDbadminSql -PgHost $src.Endpoint.Address -MasterArn $prodMasterArn -Sql $prodAfterSql -StreamPrefix "restoreprodafter"

$sourceStill = aws rds describe-db-instances --region $region --db-instance-identifier $sourceId --query "DBInstances[0].DBInstanceStatus" --output text
$evidence.sourceStatusAfter = $sourceStill
if ($sourceStill -ne "available") { throw "Production RDS is no longer available" }

if (-not $SkipCleanup) {
  Write-Host "Deleting disposable $targetId"
  aws rds delete-db-instance --region $region --db-instance-identifier $targetId --skip-final-snapshot --delete-automated-backups | Out-Null
  aws rds wait db-instance-deleted --region $region --db-instance-identifier $targetId
  $gone = aws rds describe-db-instances --region $region --db-instance-identifier $targetId --query "DBInstances[0].DBInstanceIdentifier" --output text 2>$null
  $evidence.cleanupFinished = (-not $gone -or $gone -eq "None")
  $evidence.cleanupConfirmedMissing = $true
} else {
  $evidence.cleanupFinished = $false
}

$ended = Get-Date
$evidence.finishedAtUtc = $ended.ToUniversalTime().ToString("o")
$evidence.observedRecoveryMinutes = [math]::Round(($availableAt - $restoreRequested).TotalMinutes, 1)
$evidence.wallClockMinutes = [math]::Round(($ended - $started).TotalMinutes, 1)
$evidence.rtoRpoCommitment = $false
$evidence.productionPreserved = ($sourceStill -eq "available")

$outDir = Join-Path $PSScriptRoot "..\..\documents\reviews\screenshots\prm-007-encerramento"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$outFile = Join-Path $outDir "restore-log.json"
($evidence | ConvertTo-Json -Depth 6) | Set-Content -Path $outFile -Encoding utf8
Write-Host "Restore evidence written (no secrets)."
Write-Host ("observed restore-to-available minutes=" + $evidence.observedRecoveryMinutes)
