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
if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile" }

$files = @{
    'services/gateway-api/lib/seller-crypto.js' = '/tmp/p1-seller-crypto.js'
    'services/gateway-api/domain/sellers-oauth.js' = '/tmp/p1-sellers-oauth.js'
    'services/gateway-api/domain/seller-charges.js' = '/tmp/p1-seller-charges.js'
    'services/gateway-api/domain/sellers-pay.test.js' = '/tmp/p1-sellers-pay.test.js'
    'shared/database/patch_seller_payments.sql' = '/tmp/p1-patch_seller_payments.sql'
    'frontend/action-hub/src/app/checkout/seller/page.tsx' = '/tmp/p1-checkout-seller-page.tsx'
    'scripts/deploy/p1-pay-apply-hub.sh' = '/tmp/p1-pay-apply-hub.sh'
    'scripts/deploy/_prod-backup-dbs.sh' = '/tmp/p91c-backup-dbs.sh'
}

$ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
$scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')

foreach ($pair in $files.GetEnumerator()) {
    $src = Join-Path $RepoRoot $pair.Key
    if (-not (Test-Path $src)) { throw "ausente $src" }
    Write-Host "scp $($pair.Key)"
    & scp @scp $src "${User}@${ServerHost}:$($pair.Value)"
    if ($LASTEXITCODE -ne 0) { throw "scp $($pair.Key)" }
}

& ssh @ssh "sed -i 's/\r$//' /tmp/p1-pay-apply-hub.sh /tmp/p91c-backup-dbs.sh && bash /tmp/p1-pay-apply-hub.sh"
if ($LASTEXITCODE -ne 0) { throw 'remote apply failed' }
Write-Host 'P1-Pay deploy concluido (flag false).' -ForegroundColor Green
