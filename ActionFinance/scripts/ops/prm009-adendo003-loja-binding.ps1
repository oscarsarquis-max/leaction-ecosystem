#Requires -Version 5.1
# Binding lojadepaes/PRODUCTION after V13. Does not print secrets.
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
$policyFile = Join-Path $env:TEMP "af-binding-policy.json"
[System.IO.File]::WriteAllText($policyFile, $policyDoc)
aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-binding-once --policy-document "file://$policyFile" | Out-Null
Remove-Item -LiteralPath $policyFile -Force

$sql = @'
INSERT INTO actionfinance.pay_company_mapping (id, tenant_id, company_id, pay_app_id, environment, authorized, created_at, updated_at)
SELECT '624023a4-57e3-415c-b7d0-925ca1acd801', c.tenant_id, c.id, 'lojadepaes', 'PRODUCTION', true, now(), now()
FROM actionfinance.company c
WHERE c.id = '624023a4-57e3-415c-b7d0-925ca1acd3b7'
ON CONFLICT (tenant_id, company_id) DO UPDATE
SET pay_app_id = 'lojadepaes', environment = 'PRODUCTION', authorized = true, updated_at = now();
SELECT 'flyway=' || string_agg(version, ',' ORDER BY installed_rank)
  FROM actionfinance.flyway_schema_history WHERE success;
SELECT 'loja_company=' || count(*) FROM actionfinance.company WHERE id = '624023a4-57e3-415c-b7d0-925ca1acd3b7';
SELECT 'loja_membership=' || count(*) FROM actionfinance.company_membership
 WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7' AND status = 'ACTIVE';
SELECT 'loja_mapping=' || pay_app_id || '/' || environment
  FROM actionfinance.pay_company_mapping
 WHERE company_id = '624023a4-57e3-415c-b7d0-925ca1acd3b7';
SELECT 'test_mapping=' || pay_app_id || '/' || environment
  FROM actionfinance.pay_company_mapping
 WHERE company_id = '9c2e0a10-4f11-4b8a-9c2e-0a104f11000c';
SELECT 'receipts=' || count(*) FROM actionfinance.pay_receipt_transaction;
'@
$sql = $sql.Replace("`r`n", " ").Replace("`r", " ").Replace("`n", " ")
$cmd = "set -eu; psql -v ON_ERROR_STOP=1 -A -F '|' -c `"$sql`""

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
        "awslogs-stream-prefix" = "lojabind"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-lojabind-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "binding run-task failed" }
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "binding_exit=$exit"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "lojabind/dbadmin/$taskId" --limit 40 --query "events[].message" --output text
  if ($exit -ne "0") { throw "binding failed with exit $exit" }
} finally {
  aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-binding-once | Out-Null
}
