#Requires -Version 5.1
# Revalidate public RDS Flyway and aggregate counts. Prints no secrets and no row data.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$cluster = "actionfinance-cluster"
$hostName = "actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com"
$account = "253137917703"
$masterArn = aws rds describe-db-instances --region $region --db-instance-identifier actionfinance --query "DBInstances[0].MasterUserSecret.SecretArn" --output text
Write-Host "account=$account instance=actionfinance host=$hostName secret_arn_present=$([bool]$masterArn)"

$policyDoc = (@{
  Version = "2012-10-17"
  Statement = @(@{
    Effect = "Allow"
    Action = @("secretsmanager:GetSecretValue")
    Resource = @($masterArn)
  })
} | ConvertTo-Json -Depth 6)
$policyFile = Join-Path $env:TEMP "af-origin017-policy.json"
[System.IO.File]::WriteAllText($policyFile, $policyDoc)
aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-origin017-query-once --policy-document "file://$policyFile" | Out-Null
Remove-Item -LiteralPath $policyFile -Force

$sql = @'
SELECT 'flyway=' || string_agg(version, ',' ORDER BY installed_rank)
  FROM actionfinance.flyway_schema_history WHERE success;
SELECT 'v13_checksum=' || coalesce((SELECT checksum::text FROM actionfinance.flyway_schema_history WHERE version='13' AND success),'missing');
SELECT 'has_v14=' || exists(SELECT 1 FROM actionfinance.flyway_schema_history WHERE version='14' AND success)
    || ' has_v19=' || exists(SELECT 1 FROM actionfinance.flyway_schema_history WHERE version='19' AND success);
SELECT 'titles=' || (SELECT count(*) FROM actionfinance.financial_title)
    || ' counterparties=' || (SELECT count(*) FROM actionfinance.counterparty)
    || ' categories=' || (SELECT count(*) FROM actionfinance.financial_category);
SELECT 'title_links=' || count(*) FROM actionfinance.financial_title t
  JOIN actionfinance.counterparty c
    ON c.tenant_id=t.tenant_id AND c.company_id=t.company_id AND c.id=t.counterparty_id;
SELECT 'amount_sum=' || coalesce(sum(amount_minor),0) FROM actionfinance.financial_title;
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
        "awslogs-stream-prefix" = "origin017"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-origin017-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "origin017 query run-task failed" }
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "query_exit=$exit"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "origin017/dbadmin/$taskId" --limit 80 --query "events[].message" --output text
  if ($exit -ne "0") { throw "origin017 query failed with exit $exit" }
} finally {
  aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-origin017-query-once | Out-Null
}
