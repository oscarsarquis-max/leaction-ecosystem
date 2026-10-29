#Requires -Version 5.1
# Read latest Loja PRODUCTION sync runs. No secrets printed.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$cluster = "actionfinance-cluster"
$hostName = "actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com"
$masterArn = aws rds describe-db-instances --region $region --db-instance-identifier actionfinance --query "DBInstances[0].MasterUserSecret.SecretArn" --output text
$policyDoc = (@{
  Version = "2012-10-17"
  Statement = @(@{
    Effect = "Allow"
    Action = @("secretsmanager:GetSecretValue")
    Resource = @($masterArn)
  })
} | ConvertTo-Json -Depth 6)
$policyFile = Join-Path $env:TEMP "af-inc002-policy.json"
[System.IO.File]::WriteAllText($policyFile, $policyDoc)
aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-inc002-query-once --policy-document "file://$policyFile" | Out-Null
Remove-Item -LiteralPath $policyFile -Force

$sql = @'
SELECT 'run=' || id::text || ' env=' || environment || ' status=' || status
    || ' started=' || started_at || ' finished=' || coalesce(finished_at::text,'none')
    || ' imported=' || imported_count || ' updated=' || updated_count || ' review=' || review_count
    || ' err=' || coalesce(left(last_error,160),'none')
    || ' corr=' || coalesce(left(root_correlation_id,48),'none')
    || ' msg=' || coalesce(left(spider_message_id,64),'none')
  FROM actionfinance.pay_receipt_sync_run
 WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7'
 ORDER BY started_at DESC
 LIMIT 8;
SELECT 'txn_loja=' || count(*)
    || ' review=' || count(*) FILTER (WHERE review_required)
    || ' charged=' || count(*) FILTER (WHERE amount_minor is not null and not coalesce(amount_absent,false))
    || ' paid_absent=' || count(*) FILTER (WHERE coalesce(paid_amount_absent,true) or paid_amount_minor is null)
    || ' paid_set=' || count(*) FILTER (WHERE paid_amount_minor is not null and not coalesce(paid_amount_absent,false))
  FROM actionfinance.pay_receipt_transaction
 WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7';
SELECT 'txn_all=' || count(*) FROM actionfinance.pay_receipt_transaction;
SELECT 'titles=' || count(*) FROM actionfinance.financial_title;
SELECT 'flyway=' || string_agg(version, ',' ORDER BY installed_rank)
  FROM actionfinance.flyway_schema_history WHERE success;
'@
$sql = $sql.Replace("`r`n", " ").Replace("`r", " ").Replace("`n", " ")
$cmd = "set -eu; psql -v ON_ERROR_STOP=1 -A -t -c `"$sql`""

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
        "awslogs-stream-prefix" = "inc002q"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-inc002-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "inc002 query run-task failed" }
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "query_exit=$exit"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "inc002q/dbadmin/$taskId" --limit 40 --query "events[].message" --output text
  if ($exit -ne "0") { throw "inc002 query failed with exit $exit" }
} finally {
  aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-inc002-query-once | Out-Null
}
