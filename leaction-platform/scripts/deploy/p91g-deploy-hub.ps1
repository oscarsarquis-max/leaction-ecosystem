#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu'
)
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '../..')).Path
$KeyFile = if ($env:ACTION_HUB_SSH_KEY) { $env:ACTION_HUB_SSH_KEY } else { Join-Path $RepoRoot 'chaves/action_hub_keys.pem' }
$files = @{
    'services/gateway-api/domain/credits-ops.js' = '/tmp/p91g-credits-ops.js'
    'services/gateway-api/domain/credits-ops.test.js' = '/tmp/p91g-credits-ops.test.js'
    'services/gateway-api/domain/entitlements-api.js' = '/tmp/p91g-entitlements-api.js'
    'services/gateway-api/domain/catalog-subscription.js' = '/tmp/p91g-catalog-subscription.js'
    'services/gateway-api/domain/catalog-subscription.test.js' = '/tmp/p91g-catalog-subscription.test.js'
    'frontend/action-hub/src/components/CatalogPricingCards.tsx' = '/tmp/p91g-CatalogPricingCards.tsx'
    'frontend/action-hub/src/app/loja/page.tsx' = '/tmp/p91g-loja-page.tsx'
    'frontend/action-hub/src/app/loja/contratar/page.tsx' = '/tmp/p91g-loja-contratar.tsx'
    'scripts/deploy/p91g-apply-hub.sh' = '/tmp/p91g-apply-hub.sh'
    'scripts/deploy/p91g-convert-pack.sh' = '/tmp/p91g-convert-pack.sh'
    'scripts/deploy/_prod-backup-dbs.sh' = '/tmp/p91c-backup-dbs.sh'
}
$ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
$scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')
foreach ($pair in $files.GetEnumerator()) {
    $src = Join-Path $RepoRoot $pair.Key
    if (-not (Test-Path $src)) { throw "ausente $src" }
    & scp @scp $src "${User}@${ServerHost}:$($pair.Value)"
    if ($LASTEXITCODE -ne 0) { throw "scp $($pair.Key)" }
}
& ssh @ssh "sed -i 's/\r$//' /tmp/p91g-apply-hub.sh /tmp/p91g-convert-pack.sh /tmp/p91c-backup-dbs.sh && bash /tmp/p91g-apply-hub.sh"
if ($LASTEXITCODE -ne 0) { throw 'remote apply failed' }
