# Copia tokens OAuth do Mercado Livre do servidor de produção para o ambiente local.
#
# Pré-requisito: chave SSH em leaction-platform/chaves/action_hub_keys.pem
#                (ou ACTION_HUB_SSH_KEY apontando para o .pem)
#
# Uso:
#   .\scripts\dev\pull-ml-tokens.ps1
#   .\scripts\dev\pull-ml-tokens.ps1 -ServerHost 1.2.3.4 -User ubuntu

param(
    [string]$ServerHost = $env:ACTION_HUB_SSH_HOST,
    [string]$User = $(if ($env:ACTION_HUB_SSH_USER) { $env:ACTION_HUB_SSH_USER } else { 'ubuntu' }),
    [string]$RemoteTokens = '/var/lib/leaction-platform/.ml_tokens.json'
)

$ErrorActionPreference = 'Stop'
$HubRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $HubRoot 'backend'))) {
    $HubRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
}

$KeyFile = if ($env:ACTION_HUB_SSH_KEY) { $env:ACTION_HUB_SSH_KEY } else { Join-Path $HubRoot 'chaves\action_hub_keys.pem' }
$LocalTokens = Join-Path $HubRoot 'backend\.ml_tokens.json'

if (-not $ServerHost) {
    Write-Host "Defina -ServerHost ou ACTION_HUB_SSH_HOST (IP/DNS do actionhub)."
    exit 1
}
if (-not (Test-Path -LiteralPath $KeyFile)) {
    Write-Host "Chave SSH ausente: $KeyFile"
    Write-Host "Sem ela, copie manualmente do servidor:"
    Write-Host "  $RemoteTokens  ->  $LocalTokens"
    Write-Host "Depois: .\scripts\dev\restart-hub-service.ps1 -Service marketplace"
    exit 1
}

Write-Host "Baixando $User@${ServerHost}:$RemoteTokens"
& scp -i $KeyFile -o StrictHostKeyChecking=no "${User}@${ServerHost}:${RemoteTokens}" $LocalTokens
if ($LASTEXITCODE -ne 0) {
    # fallback path no deploy antigo
    $alt = '/var/www/leaction-platform/backend/.ml_tokens.json'
    Write-Host "Tentando fallback $alt"
    & scp -i $KeyFile -o StrictHostKeyChecking=no "${User}@${ServerHost}:${alt}" $LocalTokens
    if ($LASTEXITCODE -ne 0) { throw 'scp dos tokens ML falhou' }
}

Write-Host "OK -> $LocalTokens"
Write-Host "Reinicie o marketplace: .\scripts\dev\restart-hub-service.ps1 -Service marketplace"
