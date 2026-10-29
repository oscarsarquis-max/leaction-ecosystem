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
    'frontend/action-hub/public/brands/lojadepaes.png' = '/tmp/p95a-lojadepaes.png'
    'frontend/action-hub/src/components/ClientCheckoutHeader.tsx' = '/tmp/p95a-ClientCheckoutHeader.tsx'
    'frontend/action-hub/src/lib/loja-brand-asset.test.mjs' = '/tmp/p95a-loja-brand-asset.test.mjs'
    'scripts/deploy/p95a-apply-hub.sh' = '/tmp/p95a-apply-hub.sh'
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
& ssh @ssh "sed -i 's/\r$//' /tmp/p95a-apply-hub.sh /tmp/p91c-backup-dbs.sh && bash /tmp/p95a-apply-hub.sh"
if ($LASTEXITCODE -ne 0) { throw 'remote apply failed' }
