# Borda SIMULATOR isolada com controle de fixture em loopback.
param(
    [string]$Secret = $(if ($env:SPIDER_ACTIONHUB_PAY_EDGE_SECRET) { $env:SPIDER_ACTIONHUB_PAY_EDGE_SECRET } else { "prm008-edge-only" })
)
$ErrorActionPreference = "Stop"
$edge = Join-Path $PSScriptRoot "..\..\..\spider\tools\actionhub-pay-edge\server.js"
if (-not (Test-Path $edge)) {
    Write-Error "Borda Pay não encontrada: $edge"
}
$env:SPIDER_ACTIONHUB_PAY_EDGE_SECRET = $Secret
$env:ACTIONHUB_PAY_EDGE_PORT = "8097"
$env:ACTIONHUB_PAY_EDGE_MODE = "SIMULATOR"
$env:ACTIONHUB_PAY_EDGE_TEST_CONTROL = "1"
Remove-Item Env:ACTIONHUB_PAY_BASE_URL -ErrorAction SilentlyContinue
Write-Host "Borda PROVIDER 127.0.0.1:8097 SIMULATOR TEST_CONTROL=1"
node $edge
