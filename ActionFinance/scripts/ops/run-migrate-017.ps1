#Requires -Version 5.1
# One-shot production migrate via the existing actionfinance-migrate family.
# Does not print secrets. Does not touch the web service.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$cluster = "actionfinance-cluster"
$net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"

$td = aws ecs describe-task-definition --region $region --task-definition actionfinance-migrate --query "taskDefinition.{rev:revision,image:containerDefinitions[0].image}" --output json
Write-Host "migrate_taskdef=$td"

$taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-migrate --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
if (-not $taskArn -or $taskArn -eq "None") { throw "migrate run-task failed" }
Write-Host "task=$taskArn"
aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
$exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
$taskId = ($taskArn -split "/")[-1]
$stream = "migrate/actionfinance-migrate/$taskId"
Write-Host "migrate_exit=$exit stream=$stream"
$logs = aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name $stream --limit 80 --query "events[].message" --output text
$logs = $logs -replace "password=[^\s]+", "password=***" -replace "client-secret=[^\s]+", "client-secret=***"
Write-Host $logs
if ($logs -notmatch "now at version v19") { throw "migrate logs did not reach v19" }
Write-Host "MIGRATE_V19_OK"
