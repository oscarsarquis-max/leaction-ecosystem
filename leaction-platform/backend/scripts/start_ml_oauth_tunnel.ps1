# Expõe o Marketplace (:4012) via HTTPS para OAuth do Mercado Livre.
# Requer cloudflared: winget install Cloudflare.cloudflared
#
# Uso:
#   1. Marketplace rodando em http://127.0.0.1:4012
#   2. Execute este script
#   3. Copie a URL https exibida → ML_PUBLIC_BASE_URL no backend/.env
#   4. Cadastre {URL}/marketplace-api/ml/callback no painel ML
#   5. Abra {URL}/marketplace-api/ml/login no browser

$ErrorActionPreference = "Stop"

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "cloudflared nao encontrado. Instale: winget install Cloudflare.cloudflared"
    exit 1
}

Write-Host ""
Write-Host "Iniciando tunel HTTPS -> http://127.0.0.1:4012"
Write-Host "Cole a URL https em backend/.env como ML_PUBLIC_BASE_URL"
Write-Host ""

cloudflared tunnel --url http://127.0.0.1:4012
