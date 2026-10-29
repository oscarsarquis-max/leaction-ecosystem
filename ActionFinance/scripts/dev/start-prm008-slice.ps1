# Fatia isolada PRM_008: borda PROVIDER + lembrete de AF e Spider.
# Não sobe Pay de produção. Não declara integração real com Mercado Pago.
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
Write-Host "Borda PROVIDER em 127.0.0.1:8097 (SIMULATOR). ActionFinance nao deve ter esta URL."
Write-Host "Spider: SPIDER_ACTIONHUB_PAY_EDGE_URL=http://127.0.0.1:8097 SPIDER_ACTIONHUB_PAY_EDGE_SECRET=$Secret SPIDER_ACTIONFINANCE_APPLICATION_SECRET=<mesmo do AF>"
Write-Host "AF local-demo: ACTIONFINANCE_INTEGRATION_HOMOLOG=true ACTIONFINANCE_SPIDER_BASE_URL=http://127.0.0.1:8080 ACTIONFINANCE_SPIDER_SECRET=<mesmo>"
Write-Host "Referencia de teste do simulador: pay-homolog-0001"
node $edge
