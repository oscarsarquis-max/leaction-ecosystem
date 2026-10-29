#Requires -Version 5.1
# Loja titles/settlements/movements + AF run repeat fingerprints. No secrets printed.
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
$policyFile = Join-Path $env:TEMP "af-prova001-sets-policy.json"
[System.IO.File]::WriteAllText($policyFile, $policyDoc)
aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-prova001-sets-once --policy-document "file://$policyFile" | Out-Null
Remove-Item -LiteralPath $policyFile -Force

$sql = @'
SELECT 'run=' || id::text || ' env=' || environment || ' status=' || status
    || ' started=' || started_at
    || ' finished=' || coalesce(finished_at::text,'none')
    || ' imported=' || imported_count || ' updated=' || updated_count || ' review=' || review_count
    || ' msg=' || coalesce(left(spider_message_id,64),'none')
  FROM actionfinance.pay_receipt_sync_run
 WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7'
 ORDER BY started_at DESC
 LIMIT 4;
SELECT 'sets_loja titles=' || (SELECT count(*) FROM actionfinance.financial_title WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7')
    || ' settlements=' || (SELECT count(*) FROM actionfinance.settlement WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7')
    || ' movements=' || (SELECT count(*) FROM actionfinance.cash_movement WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7');
SELECT 'sets_all titles=' || (SELECT count(*) FROM actionfinance.financial_title)
    || ' settlements=' || (SELECT count(*) FROM actionfinance.settlement)
    || ' movements=' || (SELECT count(*) FROM actionfinance.cash_movement);
SELECT 'txn_loja=' || count(*) || ' distinct_id=' || count(DISTINCT transaction_id)
    || ' fp=' || md5(string_agg(transaction_id || '|' || coalesce(amount_minor::text,'') || '|' || coalesce(paid_amount_minor::text,'') || '|' || review_required::text, ',' ORDER BY transaction_id))
  FROM actionfinance.pay_receipt_transaction
 WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7';
SELECT 'rev_loja=' || count(*) || ' runs=' || count(DISTINCT sync_run_id)
  FROM actionfinance.pay_receipt_transaction_revision
 WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7';
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
        "awslogs-stream-prefix" = "prova001s"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-prova001-sets-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "prova001 sets run-task failed" }
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "query_exit=$exit"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "prova001s/dbadmin/$taskId" --limit 40 --query "events[].message" --output text
  if ($exit -ne "0") { throw "prova001 sets failed with exit $exit" }
} finally {
  aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-prova001-sets-once | Out-Null
}
