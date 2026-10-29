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
    'services/gateway-api/domain/catalog-subscription.js' = '/tmp/p91d-catalog-subscription.js'
    'services/gateway-api/domain/catalog-subscription.test.js' = '/tmp/p91d-catalog-subscription.test.js'
    'services/gateway-api/domain/catalog-public.js' = '/tmp/p91d-catalog-public.js'
    'services/gateway-api/domain/checkout-sessions.js' = '/tmp/p91d-checkout-sessions.js'
    'services/gateway-api/domain/mp-webhooks.js' = '/tmp/p91d-mp-webhooks.js'
    'services/gateway-api/mercadopago.js' = '/tmp/p91d-mercadopago.js'
    'services/gateway-api/server.js' = '/tmp/p91d-server.js'
    'services/gateway-api/domain/credits-ops.js' = '/tmp/p91d-credits-ops.js'
    'shared/database/patch_subscription_cycles.sql' = '/tmp/p91d-patch-subscription-cycles.sql'
    'frontend/action-hub/src/app/dashboard/page.tsx' = '/tmp/p91d-dashboard-page.tsx'
    'scripts/deploy/p91d-apply-hub.sh' = '/tmp/p91d-apply-hub.sh'
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
& ssh @ssh "sed -i 's/\r$//' /tmp/p91d-apply-hub.sh /tmp/p91c-backup-dbs.sh && bash /tmp/p91d-apply-hub.sh"
if ($LASTEXITCODE -ne 0) { throw 'remote apply failed' }
