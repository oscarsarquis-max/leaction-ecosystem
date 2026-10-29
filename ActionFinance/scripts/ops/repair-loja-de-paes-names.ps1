#Requires -Version 5.1
# Repairs only the two confirmed Loja de Pães display names via UTF-8 hex.
# IDs: tenant 4f150085-f5f0-4138-80c3-fcf06db15c3c, company 624023a4-57e3-415c-b7d0-925ca1acd3b7.
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
$policyFile = Join-Path $env:TEMP "af-repair-policy.json"
[System.IO.File]::WriteAllText($policyFile, $policyDoc)
aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-repair-once --policy-document "file://$policyFile" | Out-Null
Remove-Item -LiteralPath $policyFile -Force

# "Loja de Pães" UTF-8. Wrong stored form is UTF-8 of U+00C3 U+00A3 (Ã£).
$sql = @'
BEGIN;
UPDATE actionfinance.tenant
   SET name = convert_from(decode('4c6f6a612064652050c3a36573','hex'),'UTF8'),
       updated_at = NOW(),
       version = version + 1
 WHERE id = '4f150085-f5f0-4138-80c3-fcf06db15c3c'
   AND code = 'loja-de-paes'
   AND encode(convert_to(name,'UTF8'),'hex') = '4c6f6a612064652050c383c2a36573';
UPDATE actionfinance.company
   SET name = convert_from(decode('4c6f6a612064652050c3a36573','hex'),'UTF8'),
       updated_at = NOW(),
       version = version + 1
 WHERE id = '624023a4-57e3-415c-b7d0-925ca1acd3b7'
   AND code = 'loja-de-paes'
   AND encode(convert_to(name,'UTF8'),'hex') = '4c6f6a612064652050c383c2a36573';
INSERT INTO actionfinance.access_admin_audit (
  id, occurred_at, executor_kind, executor_label, target_kind, target_id, action, reason, correlation_id, metadata
) VALUES
  (gen_random_uuid(), NOW(), 'ADMIN_CLI', 'prm007-adendo-003', 'IDENTITY',
   '4f150085-f5f0-4138-80c3-fcf06db15c3c', 'PROVISION_USER',
   'PRM007 encoding repair tenant display name', 'prm007-adendo-003',
   jsonb_build_object('kind','DISPLAY_NAME_ENCODING_REPAIR','table','tenant','beforeHex','4c6f6a612064652050c383c2a36573','afterHex','4c6f6a612064652050c3a36573','code','loja-de-paes')),
  (gen_random_uuid(), NOW(), 'ADMIN_CLI', 'prm007-adendo-003', 'IDENTITY',
   '624023a4-57e3-415c-b7d0-925ca1acd3b7', 'PROVISION_USER',
   'PRM007 encoding repair company display name', 'prm007-adendo-003',
   jsonb_build_object('kind','DISPLAY_NAME_ENCODING_REPAIR','table','company','beforeHex','4c6f6a612064652050c383c2a36573','afterHex','4c6f6a612064652050c3a36573','code','loja-de-paes'));
SELECT 'after' AS phase, kind, id::text, octet_length(name) AS nbytes, encode(convert_to(name,'UTF8'),'hex') AS utf8_hex
  FROM (
    SELECT 'tenant' AS kind, id, name FROM actionfinance.tenant WHERE id = '4f150085-f5f0-4138-80c3-fcf06db15c3c'
    UNION ALL
    SELECT 'company', id, name FROM actionfinance.company WHERE id = '624023a4-57e3-415c-b7d0-925ca1acd3b7'
  ) s;
SELECT COUNT(*) AS repaired_audit FROM actionfinance.access_admin_audit WHERE correlation_id = 'prm007-adendo-003';
COMMIT;
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
        "awslogs-stream-prefix" = "namerepair"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-namerepair-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "repair run-task failed" }
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "repair exit=$exit"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "namerepair/dbadmin/$taskId" --limit 40 --query "events[].message" --output text
  if ($exit -ne "0") { throw "repair failed with exit $exit" }
} finally {
  aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-repair-once | Out-Null
}
