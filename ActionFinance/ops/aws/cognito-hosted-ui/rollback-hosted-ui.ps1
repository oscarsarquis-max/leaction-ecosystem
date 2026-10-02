#Requires -Version 5.1
[CmdletBinding()]
param(
  [switch] $Apply
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$region = "us-east-2"
$snapshotPath = Join-Path $here "snapshot-atual.json"
if (-not (Test-Path -LiteralPath $snapshotPath)) { throw "Missing $snapshotPath. Run apply-hosted-ui.ps1 first." }

$snapshot = Get-Content -LiteralPath $snapshotPath -Raw -Encoding utf8 | ConvertFrom-Json
$poolId = $snapshot.UserPoolId
if (-not $poolId) { $poolId = $snapshot.UICustomization.UserPoolId }
$clientId = $snapshot.ClientId
if (-not $clientId) { $clientId = $snapshot.UICustomization.ClientId }
if (-not $poolId -or -not $clientId) { throw "Snapshot is missing UserPoolId or ClientId." }
if ($clientId -eq "ALL") { throw "Refusing to rollback ClientId=ALL." }

$css = [string]$snapshot.UICustomization.CSS
$cssFile = Join-Path $here "rollback.css"
Set-Content -LiteralPath $cssFile -Value $css -Encoding ascii -NoNewline

$imageUrl = [string]$snapshot.UICustomization.ImageUrl
$args = @(
  "cognito-idp", "set-ui-customization",
  "--region", $region,
  "--user-pool-id", $poolId,
  "--client-id", $clientId,
  "--css", "file://$($cssFile.Replace('\', '/'))"
)
$imageFile = Join-Path $here "rollback-logo.png"
if ($imageUrl) {
  Invoke-WebRequest -Uri $imageUrl -OutFile $imageFile
  $args += @("--image-file", "fileb://$($imageFile.Replace('\', '/'))")
}

Write-Host "pool=$poolId client=$clientId imageRestore=$([bool]$imageUrl)"
if (-not $Apply) {
  Write-Host "Dry run. Pass -Apply to restore snapshot-atual.json on the Finance client only."
  exit 0
}

aws @args
if ($LASTEXITCODE -ne 0) { throw "Rollback SetUICustomization failed." }
Write-Host "Restored Finance Hosted UI from snapshot-atual.json."
