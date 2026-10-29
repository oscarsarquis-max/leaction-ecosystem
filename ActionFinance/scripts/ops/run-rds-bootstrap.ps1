#Requires -Version 5.1
# One-off Fargate task to create schema/roles. Does not print passwords.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$account = "253137917703"
$cluster = "actionfinance-cluster"
$migrateRole = "actionfinance-migrate-execution"
$hostName = "actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com"

$masterArn = aws rds describe-db-instances --region $region --db-instance-identifier actionfinance --query "DBInstances[0].MasterUserSecret.SecretArn" --output text
$runtimeArn = aws secretsmanager describe-secret --region $region --secret-id actionfinance/runtime --query ARN --output text
$migratorArn = aws secretsmanager describe-secret --region $region --secret-id actionfinance/migrator --query ARN --output text
if ($LASTEXITCODE -ne 0 -or -not $masterArn) { throw "Unable to resolve secret ARNs." }

$policyDoc = (@{
  Version = "2012-10-17"
  Statement = @(@{
    Effect   = "Allow"
    Action   = @("secretsmanager:GetSecretValue")
    Resource = @($masterArn, $runtimeArn, $migratorArn)
  })
} | ConvertTo-Json -Depth 6)
$policyFile = Join-Path $env:TEMP "af-bootstrap-policy.json"
Set-Content -LiteralPath $policyFile -Value $policyDoc -Encoding ascii
aws iam put-role-policy --role-name $migrateRole --policy-name actionfinance-bootstrap-once --policy-document "file://$policyFile" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to attach bootstrap secret policy." }
Remove-Item -LiteralPath $policyFile -Force

$containerCmd = @'
set -eu
psql -v ON_ERROR_STOP=1 -c "SELECT 1"
if ! psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='actionfinance_migrator'" | grep -q 1; then
  psql -v ON_ERROR_STOP=1 -c "CREATE ROLE actionfinance_migrator LOGIN PASSWORD '${MIGRATOR_PASSWORD}'"
else
  psql -v ON_ERROR_STOP=1 -c "ALTER ROLE actionfinance_migrator PASSWORD '${MIGRATOR_PASSWORD}'"
fi
if ! psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='actionfinance_runtime'" | grep -q 1; then
  psql -v ON_ERROR_STOP=1 -c "CREATE ROLE actionfinance_runtime LOGIN PASSWORD '${RUNTIME_PASSWORD}'"
else
  psql -v ON_ERROR_STOP=1 -c "ALTER ROLE actionfinance_runtime PASSWORD '${RUNTIME_PASSWORD}'"
fi
psql -v ON_ERROR_STOP=1 -c "GRANT actionfinance_migrator TO CURRENT_USER"
psql -v ON_ERROR_STOP=1 -c "CREATE SCHEMA IF NOT EXISTS actionfinance AUTHORIZATION actionfinance_migrator"
psql -v ON_ERROR_STOP=1 -c "GRANT CONNECT ON DATABASE actionfinance TO actionfinance_migrator"
psql -v ON_ERROR_STOP=1 -c "GRANT CONNECT ON DATABASE actionfinance TO actionfinance_runtime"
psql -v ON_ERROR_STOP=1 -c "GRANT USAGE ON SCHEMA actionfinance TO actionfinance_runtime"
psql -v ON_ERROR_STOP=1 -c "REVOKE CREATE ON SCHEMA actionfinance FROM PUBLIC"
psql -v ON_ERROR_STOP=1 -c "REVOKE CREATE ON SCHEMA actionfinance FROM actionfinance_runtime"
echo BOOTSTRAP_OK
'@.Replace("`r`n", "`n").Replace("`r", "`n")

$td = @{
  family                  = "actionfinance-dbadmin"
  networkMode             = "awsvpc"
  requiresCompatibilities = @("FARGATE")
  cpu                     = "256"
  memory                  = "512"
  executionRoleArn        = "arn:aws:iam::${account}:role/$migrateRole"
  runtimePlatform         = @{ operatingSystemFamily = "LINUX"; cpuArchitecture = "X86_64" }
  containerDefinitions    = @(@{
    name      = "dbadmin"
    image     = "public.ecr.aws/docker/library/postgres:17.6"
    essential = $true
    environment = @(
      @{ name = "PGHOST"; value = $hostName }
      @{ name = "PGDATABASE"; value = "actionfinance" }
      @{ name = "PGSSLMODE"; value = "require" }
    )
    secrets = @(
      @{ name = "PGUSER"; valueFrom = "${masterArn}:username::" }
      @{ name = "PGPASSWORD"; valueFrom = "${masterArn}:password::" }
      @{ name = "RUNTIME_PASSWORD"; valueFrom = "${runtimeArn}:password::" }
      @{ name = "MIGRATOR_PASSWORD"; valueFrom = "${migratorArn}:password::" }
    )
    command = @("bash", "-lc", $containerCmd)
    logConfiguration = @{
      logDriver = "awslogs"
      options   = @{
        "awslogs-group"         = "/actionfinance/migrate"
        "awslogs-region"        = $region
        "awslogs-stream-prefix" = "dbadmin"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-dbadmin-td.json"
($td | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $tdFile -Encoding utf8
# AWS CLI on Windows wants the file without BOM issues
$raw = Get-Content -LiteralPath $tdFile -Raw
[System.IO.File]::WriteAllText($tdFile, $raw)

aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
if ($LASTEXITCODE -ne 0) { throw "register-task-definition failed" }

$net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
$taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
if ($LASTEXITCODE -ne 0 -or -not $taskArn -or $taskArn -eq "None") { throw "run-task failed" }
Write-Host "Bootstrap task started."
aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
$exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
Write-Host "Bootstrap task exit=$exit"
if ($exit -ne "0") { throw "Bootstrap task failed with exit $exit" }

aws iam delete-role-policy --role-name $migrateRole --policy-name actionfinance-bootstrap-once | Out-Null
Write-Host "Temporary bootstrap secret policy removed."
