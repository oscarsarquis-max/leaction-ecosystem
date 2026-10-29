# Endpoint real de listagem contra o Postgres descartável :55432.
$ErrorActionPreference = "Stop"
if (Get-NetTCPConnection -LocalPort 4101 -State Listen -ErrorAction SilentlyContinue) {
    throw "Porta 4101 ocupada. Recusando iniciar."
}
$env:PRM009_HUB_DATABASE_URL = "postgresql://prm009:prm009@127.0.0.1:55432/hub_prm009"
$env:PRM009_HUB_PORT = "4101"
$env:ACTIONHUB_PAY_LOOKUP_ENABLED = "true"
$env:ACTIONHUB_PAY_LOOKUP_ISOLATED = "true"
$env:ACTIONHUB_PAY_ENVIRONMENT = "sandbox"
if (-not $env:ACTIONHUB_PAY_PROVIDER_SECRET) {
    $env:ACTIONHUB_PAY_PROVIDER_SECRET = "prm009-hub-provider"
}
Write-Host "Hub isolado 127.0.0.1:4101 (código spider-pay-lookup.js, banco descartável)"
node (Join-Path $PSScriptRoot "hub-isolated.js")
