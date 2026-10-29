#Requires -Version 5.1
# After-repair check: hex, remaining wrong rows in tenant/company, stable IDs. No secrets.
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
$policyFile = Join-Path $env:TEMP "af-verify-policy.json"
[System.IO.File]::WriteAllText($policyFile, $policyDoc)
aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-verify-once --policy-document "file://$policyFile" | Out-Null
Remove-Item -LiteralPath $policyFile -Force

$sql = @'
SELECT kind, id::text, extra, nbytes, utf8_hex FROM (
  SELECT 1 AS ord, 'tenant'::text AS kind, id, code AS extra, octet_length(name) AS nbytes, encode(convert_to(name,'UTF8'),'hex') AS utf8_hex
    FROM actionfinance.tenant WHERE id = '4f150085-f5f0-4138-80c3-fcf06db15c3c'
  UNION ALL
  SELECT 2, 'company', id, code, octet_length(name), encode(convert_to(name,'UTF8'),'hex')
    FROM actionfinance.company WHERE id = '624023a4-57e3-415c-b7d0-925ca1acd3b7'
  UNION ALL
  SELECT 3, 'actor', id, status, 0, NULL
    FROM actionfinance.app_user WHERE id = '3548715b-d5fc-494a-a3ed-cfbc9b680125'
  UNION ALL
  SELECT 4, 'remaining_wrong_tenant', NULL, NULL, COUNT(*)::int, NULL
    FROM actionfinance.tenant WHERE encode(convert_to(name,'UTF8'),'hex') = '4c6f6a612064652050c383c2a36573'
  UNION ALL
  SELECT 5, 'remaining_wrong_company', NULL, NULL, COUNT(*)::int, NULL
    FROM actionfinance.company WHERE encode(convert_to(name,'UTF8'),'hex') = '4c6f6a612064652050c383c2a36573'
  UNION ALL
  SELECT 6, 'company_json', id, NULL, octet_length(json_build_object('name', name)::text), encode(convert_to(json_build_object('name', name)::text,'UTF8'),'hex')
    FROM actionfinance.company WHERE id = '624023a4-57e3-415c-b7d0-925ca1acd3b7'
) s ORDER BY ord;
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
        "awslogs-stream-prefix" = "nameverify"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-nameverify-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "verify run-task failed" }
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "verify exit=$exit"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "nameverify/dbadmin/$taskId" --limit 40 --query "events[].message" --output text
  if ($exit -ne "0") { throw "verify failed with exit $exit" }
} finally {
  aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-verify-once | Out-Null
}
