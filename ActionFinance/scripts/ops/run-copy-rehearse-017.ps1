#Requires -Version 5.1
# In-VPC dump/restore/migrate rehearsal. Dump never leaves the task. Prints aggregates only.
[CmdletBinding()]
param(
  [string]$WorkerImage = "253137917703.dkr.ecr.us-east-2.amazonaws.com/actionfinance@sha256:f8056baeab5942b4bbb1072909810306d20ad87e0c8930943bfb14560d48cbfd"
)

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$cluster = "actionfinance-cluster"
$hostName = "actionfinance.czqyam2auctn.us-east-2.rds.amazonaws.com"
$account = "253137917703"
$masterArn = aws rds describe-db-instances --region $region --db-instance-identifier actionfinance --query "DBInstances[0].MasterUserSecret.SecretArn" --output text

$policyDoc = (@{
  Version = "2012-10-17"
  Statement = @(@{
    Effect = "Allow"
    Action = @("secretsmanager:GetSecretValue")
    Resource = @($masterArn)
  })
} | ConvertTo-Json -Depth 6)
$policyFile = Join-Path $env:TEMP "af-copy017-policy.json"
[System.IO.File]::WriteAllText($policyFile, $policyDoc)
aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-copy017-once --policy-document "file://$policyFile" | Out-Null
Remove-Item -LiteralPath $policyFile -Force

$td = @{
  family = "actionfinance-copy-017"
  networkMode = "awsvpc"
  requiresCompatibilities = @("FARGATE")
  cpu = "1024"
  memory = "2048"
  executionRoleArn = "arn:aws:iam::${account}:role/actionfinance-migrate-execution"
  runtimePlatform = @{ operatingSystemFamily = "LINUX"; cpuArchitecture = "X86_64" }
  containerDefinitions = @(
    @{
      name = "copy-pg"
      image = "public.ecr.aws/docker/library/postgres:17.6"
      essential = $false
      environment = @(
        @{ name = "POSTGRES_DB"; value = "actionfinance" }
        @{ name = "POSTGRES_USER"; value = "actionfinance_bootstrap" }
        @{ name = "POSTGRES_PASSWORD"; value = "bootstrap-test" }
      )
      logConfiguration = @{
        logDriver = "awslogs"
        options = @{
          "awslogs-group" = "/actionfinance/migrate"
          "awslogs-region" = $region
          "awslogs-stream-prefix" = "copy017pg"
        }
      }
    }
    @{
      name = "copy-worker"
      image = $WorkerImage
      essential = $true
      dependsOn = @(@{ containerName = "copy-pg"; condition = "START" })
      environment = @(
        @{ name = "PGHOST"; value = $hostName }
        @{ name = "PGDATABASE"; value = "actionfinance" }
        @{ name = "PGSSLMODE"; value = "require" }
        @{ name = "COPY_HOST"; value = "127.0.0.1" }
      )
      secrets = @(
        @{ name = "PGUSER"; valueFrom = "${masterArn}:username::" }
        @{ name = "PGPASSWORD"; valueFrom = "${masterArn}:password::" }
      )
      logConfiguration = @{
        logDriver = "awslogs"
        options = @{
          "awslogs-group" = "/actionfinance/migrate"
          "awslogs-region" = $region
          "awslogs-stream-prefix" = "copy017"
        }
      }
    }
  )
}
$tdFile = Join-Path $env:TEMP "af-copy017-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 10))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-copy-017 --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "copy017 run-task failed" }
  Write-Host "task=$taskArn"
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[?name=='copy-worker'].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "worker_exit=$exit"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "copy017/copy-worker/$taskId" --limit 80 --query "events[].message" --output text
  if ($exit -ne "0") { throw "copy017 failed with exit $exit" }
} finally {
  aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-copy017-once | Out-Null
}
