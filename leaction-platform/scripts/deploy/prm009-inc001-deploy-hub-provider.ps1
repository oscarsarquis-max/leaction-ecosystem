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
    'services/gateway-api/domain/spider-pay-lookup.js' = '/tmp/spider-pay-lookup.js'
    'services/gateway-api/domain/spider-pay-lookup.test.js' = '/tmp/spider-pay-lookup.test.js'
    'services/gateway-api/domain/amount-checkout.js' = '/tmp/amount-checkout.js'
    'services/gateway-api/domain/mp-webhooks.js' = '/tmp/mp-webhooks.js'
    'services/gateway-api/domain/amount-observation.test.js' = '/tmp/amount-observation.test.js'
    'services/gateway-api/domain/amount-checkout.test.js' = '/tmp/amount-checkout.test.js'
    'services/gateway-api/domain/pay-regression.test.js' = '/tmp/pay-regression.test.js'
    'services/gateway-api/lib/money-cents.test.js' = '/tmp/money-cents.test.js'
    'services/gateway-api/admin/payments.js' = '/tmp/admin-payments.js'
    'services/gateway-api/mercadopago.js' = '/tmp/mercadopago.js'
    'services/gateway-api/scripts/prm009-inc001-apply-hub-provider.sh' = '/tmp/prm009-inc001-apply-hub-provider.sh'
}
$ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
$scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')
foreach ($pair in $files.GetEnumerator()) {
    $src = Join-Path $RepoRoot $pair.Key
    & scp @scp $src "${User}@${ServerHost}:$($pair.Value)"
    if ($LASTEXITCODE -ne 0) { throw "scp failed $($pair.Key)" }
}
& ssh @ssh "sed -i 's/\r$//' /tmp/prm009-inc001-apply-hub-provider.sh && bash /tmp/prm009-inc001-apply-hub-provider.sh"
if ($LASTEXITCODE -ne 0) { throw 'remote apply failed' }
