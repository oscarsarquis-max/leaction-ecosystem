#Requires -Version 5.1
# One-off Fargate access-admin. Does not print secrets.
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string[]] $AppArgs
)

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$cluster = "actionfinance-cluster"
$net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"

$overrides = @{
  containerOverrides = @(
    @{
      name = "actionfinance-migrate"
      command = $AppArgs
      environment = @(
        @{ name = "SPRING_PROFILES_ACTIVE"; value = "access-admin" }
        @{ name = "ACTIONFINANCE_FLYWAY_ENABLED"; value = "false" }
      )
    }
  )
}
$ovFile = Join-Path $env:TEMP ("af-access-admin-" + [guid]::NewGuid().ToString("n") + ".json")
. (Join-Path $PSScriptRoot "af-ecs-override-json.ps1")
$json = ConvertTo-AfEcsOverrideJson -Overrides $overrides
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($ovFile, $json, $utf8)
$env:AWS_CLI_FILE_ENCODING = "UTF-8"
try {
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-migrate --launch-type FARGATE --network-configuration $net --overrides "file://$ovFile" --query "tasks[0].taskArn" --output text
  if ($LASTEXITCODE -ne 0 -or -not $taskArn -or $taskArn -eq "None") { throw "access-admin run-task failed" }
  Write-Host "access-admin task started."
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  $stream = "migrate/actionfinance-migrate/$taskId"
  Write-Host "access-admin exit=$exit stream=$stream"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name $stream --limit 80 --query "events[].message" --output text | ForEach-Object {
    $_ -replace "password=[^\s]+", "password=***" -replace "client-secret=[^\s]+", "client-secret=***"
  }
  if ($exit -ne "0") { throw "access-admin failed with exit $exit" }
} finally {
  if (Test-Path -LiteralPath $ovFile) { Remove-Item -LiteralPath $ovFile -Force }
}
