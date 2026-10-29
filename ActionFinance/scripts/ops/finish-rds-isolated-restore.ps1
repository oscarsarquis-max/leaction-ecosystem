#Requires -Version 5.1
# Runtime checks + cleanup for the existing disposable restore instance.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$sourceId = "actionfinance"
$targetId = "actionfinance-restore-prm007"
$cluster = "actionfinance-cluster"
$runtimeArn = aws secretsmanager describe-secret --region $region --secret-id actionfinance/runtime --query ARN --output text
$source = aws rds describe-db-instances --region $region --db-instance-identifier $sourceId --output json | ConvertFrom-Json
$src = $source.DBInstances[0]
$prodMasterArn = $src.MasterUserSecret.SecretArn
aws rds wait db-instance-available --region $region --db-instance-identifier $targetId
$restored = aws rds describe-db-instances --region $region --db-instance-identifier $targetId --output json | ConvertFrom-Json
$rst = $restored.DBInstances[0]

function Invoke-AfTask {
  param(
    [Parameter(Mandatory = $true)][string] $PgHost,
    [Parameter(Mandatory = $true)][string] $StreamPrefix,
    [Parameter(Mandatory = $true)][object[]] $Environment,
    [Parameter(Mandatory = $true)][object[]] $Secrets,
    [Parameter(Mandatory = $true)][string[]] $Command,
    [Parameter(Mandatory = $true)][string[]] $SecretArns
  )
  $policyDoc = (@{
    Version = "2012-10-17"
    Statement = @(@{
      Effect = "Allow"
      Action = @("secretsmanager:GetSecretValue")
      Resource = $SecretArns
    })
  } | ConvertTo-Json -Depth 6)
  $policyName = "actionfinance-restore-once"
  $policyFile = Join-Path $env:TEMP "af-restore-policy.json"
  [System.IO.File]::WriteAllText($policyFile, $policyDoc)
  aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name $policyName --policy-document "file://$policyFile" | Out-Null
  Remove-Item -LiteralPath $policyFile -Force
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
      environment = $Environment
      secrets = $Secrets
      command = $Command
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
  $tdFile = Join-Path $env:TEMP ("af-finish-" + $StreamPrefix + ".json")
  [System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
  try {
    aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
    $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
    $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
    if (-not $taskArn -or $taskArn -eq "None") { throw "run-task $StreamPrefix failed" }
    aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
    $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
    $taskId = ($taskArn -split "/")[-1]
    $log = aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "$StreamPrefix/dbadmin/$taskId" --limit 80 --query "events[].message" --output text
    Write-Host "task $StreamPrefix exit=$exit"
    Write-Host $log
    if ($exit -ne "0") { throw "task $StreamPrefix failed with exit $exit" }
    return $log
  } finally {
    aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name $policyName | Out-Null
  }
}

$commonEnv = @(
  @{ name = "PGHOST"; value = $rst.Endpoint.Address }
  @{ name = "PGDATABASE"; value = "actionfinance" }
  @{ name = "PGSSLMODE"; value = "require" }
  @{ name = "PGUSER"; value = "actionfinance_runtime" }
)
$runtimeScript = @'
printf "runtime_user=%s\n" "$PGUSER"; psql -v ON_ERROR_STOP=1 -A -F "|" -c "SELECT current_user AS runtime_user;"; psql -v ON_ERROR_STOP=1 -A -F "|" -c "SELECT has_schema_privilege(current_user, E'actionfinance', E'CREATE') AS runtime_can_create;"; psql -v ON_ERROR_STOP=1 -A -F "|" -c "SELECT COUNT(*) AS titles FROM actionfinance.financial_title;"; psql -v ON_ERROR_STOP=1 -A -F "|" -c "SELECT COUNT(*) AS sessions FROM actionfinance.\"SPRING_SESSION\";"; psql -c "CREATE TABLE actionfinance.__af_restore_probe(id int);" ; echo "runtime_ddl_exit=$?"; psql -c "DELETE FROM actionfinance.access_admin_audit WHERE false;"; echo "runtime_audit_delete_exit=$?"; psql -v ON_ERROR_STOP=1 -c "DELETE FROM actionfinance.\"SPRING_SESSION\";"; psql -v ON_ERROR_STOP=1 -A -F "|" -c "SELECT COUNT(*) AS sessions_after FROM actionfinance.\"SPRING_SESSION\";"; psql -v ON_ERROR_STOP=1 -A -F "|" -c "SELECT COUNT(*) AS titles_after FROM actionfinance.financial_title;"; psql -v ON_ERROR_STOP=1 -A -F "|" -c "SELECT COUNT(*) AS users_after FROM actionfinance.app_user;"; psql -v ON_ERROR_STOP=1 -A -F "|" -c "SELECT COUNT(*) AS audit_after FROM actionfinance.access_admin_audit;"
'@
$runtimeCmd = @("bash", "-lc", $runtimeScript)
$evidence = [ordered]@{
  targetId = $targetId
  targetEncrypted = [bool]$rst.StorageEncrypted
  targetPublic = [bool]$rst.PubliclyAccessible
  priorMasterProbe = "flyway V1-V7 match; 1 tenant/company/user/membership; audit 6; titles 0; settlements 0; sessions 1; owner migrator; runtime_owned 0; company hex c3a3"
}

$prodEnv = @(
  @{ name = "PGHOST"; value = $src.Endpoint.Address }
  @{ name = "PGDATABASE"; value = "actionfinance" }
  @{ name = "PGSSLMODE"; value = "require" }
)
$prodScript = @'
psql -v ON_ERROR_STOP=1 -A -F "|" -c "SELECT E'prod_after' AS scope, (SELECT COUNT(*) FROM actionfinance.\"SPRING_SESSION\") AS sessions, (SELECT COUNT(*) FROM actionfinance.app_user) AS users, (SELECT COUNT(*) FROM actionfinance.access_admin_audit) AS audit, (SELECT COUNT(*) FROM actionfinance.financial_title) AS titles;"
'@
$prodCmd = @("bash", "-lc", $prodScript)
try {
  $evidence.runtimeProbe = Invoke-AfTask -PgHost $rst.Endpoint.Address -StreamPrefix "restorert2" -Environment $commonEnv -Secrets @(@{ name = "PGPASSWORD"; valueFrom = "${runtimeArn}:password::" }) -Command $runtimeCmd -SecretArns @($runtimeArn)
  $evidence.prodAfter = Invoke-AfTask -PgHost $src.Endpoint.Address -StreamPrefix "restoreprodafter2" -Environment $prodEnv -Secrets @(
    @{ name = "PGUSER"; valueFrom = "${prodMasterArn}:username::" }
    @{ name = "PGPASSWORD"; valueFrom = "${prodMasterArn}:password::" }
  ) -Command $prodCmd -SecretArns @($prodMasterArn)
} finally {
  Write-Host "Deleting disposable $targetId"
  aws rds delete-db-instance --region $region --db-instance-identifier $targetId --skip-final-snapshot --delete-automated-backups | Out-Null
  aws rds wait db-instance-deleted --region $region --db-instance-identifier $targetId
  $sourceStill = aws rds describe-db-instances --region $region --db-instance-identifier $sourceId --query "DBInstances[0].DBInstanceStatus" --output text
  $evidence.sourceStatusAfter = $sourceStill
  $evidence.cleanupFinished = $true
  $evidence.productionPreserved = ($sourceStill -eq "available")
  $outDir = Join-Path $PSScriptRoot "..\..\documents\reviews\screenshots\prm-007-encerramento"
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  ($evidence | ConvertTo-Json -Depth 6) | Set-Content -Path (Join-Path $outDir "restore-log.json") -Encoding utf8
  Write-Host "Restore evidence written (no secrets)."
}
