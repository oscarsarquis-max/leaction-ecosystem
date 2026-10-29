#Requires -Version 5.1
# Isolated ECS transport of the sample display name. No database write.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "af-ecs-override-json.ps1")

# "Padaria São João — Ação e Pães"
$sample = "Padaria S" + [char]0x00E3 + "o Jo" + [char]0x00E3 + "o " + [char]0x2014 + " A" + [char]0x00E7 + [char]0x00E3 + "o e P" + [char]0x00E3 + "es"
$expectedHex = [BitConverter]::ToString([System.Text.Encoding]::UTF8.GetBytes($sample)).Replace("-", "").ToLowerInvariant()

$region = "us-east-2"
$cluster = "actionfinance-cluster"
$overrides = @{
  containerOverrides = @(
    @{
      name = "dbadmin"
      command = @("python", "-c", "import os; print(os.environ['PROBE_NAME'].encode('utf-8').hex())")
      environment = @(@{ name = "PROBE_NAME"; value = $sample })
    }
  )
}
$ovFile = Join-Path $env:TEMP ("af-name-roundtrip-" + [guid]::NewGuid().ToString("n") + ".json")
$json = ConvertTo-AfEcsOverrideJson -Overrides $overrides
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($ovFile, $json, $utf8)
$env:AWS_CLI_FILE_ENCODING = "UTF-8"

$td = @{
  family = "actionfinance-nameprobe"
  networkMode = "awsvpc"
  requiresCompatibilities = @("FARGATE")
  cpu = "256"
  memory = "512"
  executionRoleArn = "arn:aws:iam::253137917703:role/actionfinance-migrate-execution"
  runtimePlatform = @{ operatingSystemFamily = "LINUX"; cpuArchitecture = "X86_64" }
  containerDefinitions = @(@{
    name = "dbadmin"
    image = "public.ecr.aws/docker/library/python:3.12-alpine"
    essential = $true
    command = @("python3", "-c", "print('no-override')")
    logConfiguration = @{
      logDriver = "awslogs"
      options = @{
        "awslogs-group" = "/actionfinance/migrate"
        "awslogs-region" = $region
        "awslogs-stream-prefix" = "nameroundtrip"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-nameroundtrip-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-nameprobe --launch-type FARGATE --network-configuration $net --overrides "file://$ovFile" --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "name roundtrip run-task failed" }
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "roundtrip exit=$exit expectedHex=$expectedHex"
  $log = aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "nameroundtrip/dbadmin/$taskId" --limit 20 --query "events[].message" --output text
  Write-Host $log
  if ($exit -ne "0") { throw "name roundtrip failed with exit $exit" }
  if ($log -notmatch $expectedHex) { throw "ECS did not deliver the expected UTF-8 hex." }
} finally {
  if (Test-Path -LiteralPath $ovFile) { Remove-Item -LiteralPath $ovFile -Force }
}
