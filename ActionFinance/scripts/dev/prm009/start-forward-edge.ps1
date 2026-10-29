# Borda FORWARD isolada na :8098. Não substitui a listagem por simulador. Não para a :8097.
$ErrorActionPreference = "Stop"
$edge = Join-Path $PSScriptRoot "..\..\..\..\spider\tools\actionhub-pay-edge\server.js"
if (-not (Test-Path $edge)) { throw "Borda não encontrada: $edge" }
if (Get-NetTCPConnection -LocalPort 8098 -State Listen -ErrorAction SilentlyContinue) {
    throw "Porta 8098 ocupada. Recusando iniciar."
}
$env:ACTIONHUB_PAY_EDGE_MODE = "FORWARD"
$env:ACTIONHUB_PAY_EDGE_PORT = "8098"
$env:ACTIONHUB_PAY_EDGE_TEST_CONTROL = "1"
$env:ACTIONHUB_PAY_BASE_URL = "http://127.0.0.1:4101"
if (-not $env:SPIDER_ACTIONHUB_PAY_EDGE_SECRET) {
    $env:SPIDER_ACTIONHUB_PAY_EDGE_SECRET = "prm009-edge-forward"
}
if (-not $env:ACTIONHUB_PAY_PROVIDER_SECRET) {
    $env:ACTIONHUB_PAY_PROVIDER_SECRET = "prm009-hub-provider"
}
Write-Host "Borda FORWARD 127.0.0.1:8098 -> Hub isolado :4101"
node $edge
