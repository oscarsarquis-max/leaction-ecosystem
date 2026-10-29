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
    'frontend/action-hub/src/lib/loja-checkout-copy.ts' = '/tmp/p95b-loja-checkout-copy.ts'
    'frontend/action-hub/src/lib/loja-checkout-copy.test.mjs' = '/tmp/p95b-loja-checkout-copy.test.mjs'
    'frontend/action-hub/src/lib/client-branding.ts' = '/tmp/p95b-client-branding.ts'
    'frontend/action-hub/src/lib/catalog-api.ts' = '/tmp/p95b-catalog-api.ts'
    'frontend/action-hub/src/components/ClientCheckoutHeader.tsx' = '/tmp/p95b-ClientCheckoutHeader.tsx'
    'frontend/action-hub/src/components/CheckoutChrome.tsx' = '/tmp/p95b-CheckoutChrome.tsx'
    'frontend/action-hub/src/components/MercadoPagoSubscriptionBrick.tsx' = '/tmp/p95b-MercadoPagoSubscriptionBrick.tsx'
    'frontend/action-hub/src/app/loja/page.tsx' = '/tmp/p95b-loja-page.tsx'
    'frontend/action-hub/src/app/loja/contratar/page.tsx' = '/tmp/p95b-loja-contratar.tsx'
    'frontend/action-hub/src/app/dashboard/page.tsx' = '/tmp/p95b-dashboard.tsx'
    'scripts/deploy/p95b-apply-hub.sh' = '/tmp/p95b-apply-hub.sh'
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
& ssh @ssh "sed -i 's/\r$//' /tmp/p95b-apply-hub.sh /tmp/p91c-backup-dbs.sh && bash /tmp/p95b-apply-hub.sh"
if ($LASTEXITCODE -ne 0) { throw 'remote apply failed' }
