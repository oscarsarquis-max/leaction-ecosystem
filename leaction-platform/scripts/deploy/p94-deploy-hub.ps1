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
    'services/gateway-api/domain/credits-ops.js' = '/tmp/p94-credits-ops.js'
    'services/gateway-api/domain/credits-ops.test.js' = '/tmp/p94-credits-ops.test.js'
    'services/gateway-api/domain/outbox-worker.js' = '/tmp/p94-outbox-worker.js'
    'services/gateway-api/domain/outbox-worker.plans.test.js' = '/tmp/p94-outbox-worker.plans.test.js'
    'services/gateway-api/domain/loja-plans-notify.js' = '/tmp/p94-loja-plans-notify.js'
    'services/gateway-api/domain/catalog-subscription.js' = '/tmp/p94-catalog-subscription.js'
    'scripts/deploy/p94-apply-hub.sh' = '/tmp/p94-apply-hub.sh'
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
& ssh @ssh "sed -i 's/\r$//' /tmp/p94-apply-hub.sh /tmp/p91c-backup-dbs.sh && bash /tmp/p94-apply-hub.sh"
if ($LASTEXITCODE -ne 0) { throw 'remote apply failed' }
