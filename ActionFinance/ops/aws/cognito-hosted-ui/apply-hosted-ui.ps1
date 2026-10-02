#Requires -Version 5.1
[CmdletBinding()]
param(
  [switch] $Apply,
  [switch] $DryRun
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$region = "us-east-2"
$poolName = "actionfinance-operators"
$clientName = "actionfinance-confidential"
$cssPath = Join-Path $here "hosted-ui-classic.css"
$logoPath = Join-Path $here "logo-hosted-ui.png"
$snapshotPath = Join-Path $here "snapshot-atual.json"
$appliedPath = Join-Path $here "applied.json"

if (-not (Test-Path -LiteralPath $cssPath)) { throw "Missing $cssPath" }
if (-not (Test-Path -LiteralPath $logoPath)) { throw "Missing $logoPath. Run make-logo.py first." }

$cssBytes = (Get-Item -LiteralPath $cssPath).Length
$logoBytes = (Get-Item -LiteralPath $logoPath).Length
if ($cssBytes -gt 3KB) { throw "CSS $($cssBytes) exceeds the classic Hosted UI 3 KB limit." }
if ($logoBytes -gt 100KB) { throw "Logo $($logoBytes) exceeds the classic Hosted UI 100 KB limit." }

$pools = aws cognito-idp list-user-pools --region $region --max-results 20 --output json | ConvertFrom-Json
$pool = @($pools.UserPools) | Where-Object { $_.Name -eq $poolName }
if (-not $pool) { throw "User pool $poolName not found in $region." }
if (@($pool).Count -ne 1) { throw "Expected one pool named $poolName." }
$poolId = $pool.Id

$domainName = "actionfinance-253137917703"
$domain = aws cognito-idp describe-user-pool-domain --region $region --domain $domainName --output json | ConvertFrom-Json
$branding = $domain.DomainDescription.ManagedLoginVersion
if ($branding -and $branding -ne 1) {
  throw "Domain $domainName is not Hosted UI classic (ManagedLoginVersion=$branding). Refusing to switch plan."
}

$clients = aws cognito-idp list-user-pool-clients --region $region --user-pool-id $poolId --max-results 20 --output json | ConvertFrom-Json
$client = @($clients.UserPoolClients) | Where-Object { $_.ClientName -eq $clientName }
if (-not $client) { throw "App client $clientName not found in pool $poolId." }
if (@($client).Count -ne 1) { throw "Expected one confidential Finance client." }
$clientId = $client.ClientId
if ($clientId -eq "ALL") { throw "Refusing ClientId=ALL. Finance client only." }

$other = @($clients.UserPoolClients) | Where-Object { $_.ClientId -ne $clientId }
Write-Host "pool=$poolId"
Write-Host "financeClient=$clientId"
Write-Host "otherClients=$($other.Count) (unchanged)"
Write-Host "cssBytes=$cssBytes logoBytes=$logoBytes"

$current = aws cognito-idp get-ui-customization --region $region --user-pool-id $poolId --client-id $clientId --output json
if ($LASTEXITCODE -ne 0) { throw "GetUICustomization failed." }
$parsed = $current | ConvertFrom-Json
$snapshot = [ordered]@{
  UserPoolId = $poolId
  ClientId = $clientId
  Region = $region
  CapturedAt = [DateTime]::UtcNow.ToString("o")
  HadCustomization = [bool]$parsed.UICustomization.CSS
  UICustomization = $parsed.UICustomization
}
($snapshot | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $snapshotPath -Encoding utf8
Write-Host "snapshot=$snapshotPath"

if ($DryRun -or -not $Apply) {
  Write-Host "Dry run. Pass -Apply to write SetUICustomization on the Finance client only."
  exit 0
}

aws cognito-idp set-ui-customization `
  --region $region `
  --user-pool-id $poolId `
  --client-id $clientId `
  --css "file://$cssPath" `
  --image-file "fileb://$logoPath" `
  --output json | Set-Content -LiteralPath $appliedPath -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "SetUICustomization failed. Restore with rollback-hosted-ui.ps1." }

$verify = aws cognito-idp get-ui-customization --region $region --user-pool-id $poolId --client-id $clientId --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Post-apply GetUICustomization failed." }
if ($verify.UICustomization.ClientId -ne $clientId) { throw "Apply did not stay on the Finance client." }
Write-Host "applied ClientId=$($verify.UICustomization.ClientId) CSSVersion=$($verify.UICustomization.CSSVersion)"
Write-Host "imageUrl=$($verify.UICustomization.ImageUrl)"
