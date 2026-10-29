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
    'frontend/action-hub/src/lib/client-branding.ts' = '/tmp/p95-client-branding.ts'
    'frontend/action-hub/src/lib/loja-return.ts' = '/tmp/p95-loja-return.ts'
    'frontend/action-hub/src/lib/loja-return.test.mjs' = '/tmp/p95-loja-return.test.mjs'
    'frontend/action-hub/src/app/loja/page.tsx' = '/tmp/p95-loja-page.tsx'
    'frontend/action-hub/src/app/loja/contratar/page.tsx' = '/tmp/p95-loja-contratar.tsx'
    'frontend/action-hub/src/components/SiteHeader.tsx' = '/tmp/p95-SiteHeader.tsx'
    'frontend/action-hub/src/components/ClientCheckoutHeader.tsx' = '/tmp/p95-ClientCheckoutHeader.tsx'
    'frontend/action-hub/src/components/CatalogPricingCards.tsx' = '/tmp/p95-CatalogPricingCards.tsx'
    'frontend/action-hub/src/middleware.ts' = '/tmp/p95-middleware.ts'
    'frontend/action-hub/next.config.ts' = '/tmp/p95-next.config.ts'
    'scripts/deploy/p95-apply-hub.sh' = '/tmp/p95-apply-hub.sh'
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
& ssh @ssh "sed -i 's/\r$//' /tmp/p95-apply-hub.sh /tmp/p91c-backup-dbs.sh && bash /tmp/p95-apply-hub.sh"
if ($LASTEXITCODE -ne 0) { throw 'remote apply failed' }
