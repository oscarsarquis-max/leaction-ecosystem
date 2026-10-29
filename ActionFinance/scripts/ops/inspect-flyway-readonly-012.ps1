#Requires -Version 5.1
# Read-only Flyway history on the effective public RDS. Prints no secrets.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$cluster = "actionfinance-cluster"
$hostName = "actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com"
$account = "253137917703"
$masterArn = aws rds describe-db-instances --region $region --db-instance-identifier actionfinance --query "DBInstances[0].MasterUserSecret.SecretArn" --output text
$engine = aws rds describe-db-instances --region $region --db-instance-identifier actionfinance --query "DBInstances[0].[Engine,EngineVersion,DBName,DBInstanceStatus]" --output text
Write-Host "account=$account region=$region instance=actionfinance host=$hostName db=actionfinance engine=$engine"
Write-Host "secret_arn_present=$([bool]$masterArn)"

$policyDoc = (@{
  Version = "2012-10-17"
  Statement = @(@{
    Effect = "Allow"
    Action = @("secretsmanager:GetSecretValue")
    Resource = @($masterArn)
  })
} | ConvertTo-Json -Depth 6)
$policyFile = Join-Path $env:TEMP "af-flyway012-policy.json"
[System.IO.File]::WriteAllText($policyFile, $policyDoc)
aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-flyway012-query-once --policy-document "file://$policyFile" | Out-Null
Remove-Item -LiteralPath $policyFile -Force

$sql = @'
SELECT version || '=' || checksum::text || ' ok=' || success::text || ' on=' || installed_on::text
  FROM actionfinance.flyway_schema_history
 ORDER BY installed_rank;
SELECT 'max_success_rank=' || coalesce(max(installed_rank)::text,'none')
    || ' latest_version=' || coalesce((
         SELECT version FROM actionfinance.flyway_schema_history
          WHERE success ORDER BY installed_rank DESC LIMIT 1),'none')
  FROM actionfinance.flyway_schema_history WHERE success;
SELECT 'has_v13=' || exists(SELECT 1 FROM actionfinance.flyway_schema_history WHERE version='13' AND success)::text
    || ' has_v14=' || exists(SELECT 1 FROM actionfinance.flyway_schema_history WHERE version='14' AND success)::text
    || ' has_v15=' || exists(SELECT 1 FROM actionfinance.flyway_schema_history WHERE version='15' AND success)::text
    || ' titles=' || (SELECT count(*) FROM actionfinance.financial_title)::text;
'@
$sql = $sql.Replace("`r`n", " ").Replace("`r", " ").Replace("`n", " ")
$cmd = "set -eu; psql -v ON_ERROR_STOP=1 -A -t -c `"$sql`""

$td = @{
  family = "actionfinance-dbadmin"
  networkMode = "awsvpc"
  requiresCompatibilities = @("FARGATE")
  cpu = "256"
  memory = "512"
  executionRoleArn = "arn:aws:iam::${account}:role/actionfinance-migrate-execution"
  runtimePlatform = @{ operatingSystemFamily = "LINUX"; cpuArchitecture = "X86_64" }
  containerDefinitions = @(@{
    name = "dbadmin"
    image = "public.ecr.aws/docker/library/postgres:17.6"
    essential = $true
    environment = @(
      @{ name = "PGHOST"; value = $hostName }
      @{ name = "PGDATABASE"; value = "actionfinance" }
      @{ name = "PGSSLMODE"; value = "require" }
    )
    secrets = @(
      @{ name = "PGUSER"; valueFrom = "${masterArn}:username::" }
      @{ name = "PGPASSWORD"; valueFrom = "${masterArn}:password::" }
    )
    command = @("bash", "-lc", $cmd)
    logConfiguration = @{
      logDriver = "awslogs"
      options = @{
        "awslogs-group" = "/actionfinance/migrate"
        "awslogs-region" = $region
        "awslogs-stream-prefix" = "flyway012"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-flyway012-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "flyway012 query run-task failed" }
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "query_exit=$exit"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "flyway012/dbadmin/$taskId" --limit 80 --query "events[].message" --output text
  if ($exit -ne "0") { throw "flyway012 query failed with exit $exit" }
} finally {
  aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-flyway012-query-once | Out-Null
}
