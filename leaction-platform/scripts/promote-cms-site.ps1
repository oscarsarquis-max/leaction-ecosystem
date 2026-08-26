<#
.SYNOPSIS
  Promove Micro-CMS local → produção (independente de deploy de app).

.DESCRIPTION
  1) Exporta cms_site_config do Hub local (Postgres)
  2) Compara com https://api.actionhub.com.br/api/public/cms
  3) Com -Force:
     - sobe ao S3 imagens /images/* ainda só no disco local (cms-uploads)
     - envia JSON ao EC2 e aplica Postgres + snapshot S3 do site

  Não faz git push. Não sincroniza leaction_hub inteiro.

.EXAMPLE
  cd C:\Projetos\leaction-platform
  .\scripts\promote-cms-site.ps1 -Key inove4us -CompareOnly

.EXAMPLE
  .\scripts\promote-cms-site.ps1 -Key inove4us-school -Force

.EXAMPLE
  # Trazer prod → local (sem S3)
  .\scripts\promote-cms-site.ps1 -Key inove4us -PullFromProd
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('default', 'inove4us', 'inove4us-school')]
    [string]$Key,

    [switch]$CompareOnly,
    [switch]$Force,
    [switch]$PullFromProd,

    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu',
    [string]$RemotePath = '/var/www/leaction-platform',
    [string]$ProdApiUrl = 'https://api.actionhub.com.br',

    # Hub local (Docker leaction_db). Não use a DATABASE_URL de prod do .env.
    [string]$LocalDatabaseUrl = 'postgresql://admin:password123@localhost:5433/leaction_hub'
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$KeyFile = if ($env:ACTION_HUB_SSH_KEY) { $env:ACTION_HUB_SSH_KEY } else { Join-Path $RepoRoot 'chaves/action_hub_keys.pem' }

$secretsDir = Join-Path $RepoRoot '.deploy-secrets'
if (-not (Test-Path $secretsDir)) { New-Item -ItemType Directory -Path $secretsDir | Out-Null }
$exportFile = Join-Path $secretsDir "cms-$Key.json"

$env:CMS_PROMOTE_PROD_URL = $ProdApiUrl
$env:CMS_PROMOTE_LOCAL_DATABASE_URL = $LocalDatabaseUrl
$env:DATABASE_URL = $LocalDatabaseUrl
$env:NODE_PATH = (Join-Path $RepoRoot 'services\gateway-api\node_modules')

Push-Location $RepoRoot
try {
    if ($PullFromProd) {
        Write-Host "==> Pull prod → local ($Key)" -ForegroundColor Cyan
        node .\scripts\promote-cms-site.js --key=$Key --pull-from-prod --apply-local --export=$exportFile
        if ($LASTEXITCODE -ne 0) { throw "pull-from-prod falhou ($LASTEXITCODE)" }
        Write-Host "OK: local atualizado a partir de prod. Arquivo: $exportFile" -ForegroundColor Green
        return
    }

    Write-Host "==> Export + compare local vs prod ($Key)" -ForegroundColor Cyan
    node .\scripts\promote-cms-site.js --key=$Key --compare-only --export=$exportFile
    $compareExit = $LASTEXITCODE
    if ($compareExit -notin 0, 3) { throw "compare falhou ($compareExit)" }

    if ($CompareOnly) {
        if ($compareExit -eq 3) {
            Write-Host "CompareOnly: há diferença. Use -Force para promover local → prod." -ForegroundColor Yellow
        } else {
            Write-Host "CompareOnly: local e prod equivalentes." -ForegroundColor Green
        }
        return
    }

    if (-not $Force) {
        Write-Host "Nada aplicado. Use -CompareOnly ou -Force." -ForegroundColor Yellow
        return
    }

    if (-not (Test-Path $KeyFile)) {
        throw "Chave SSH nao encontrada: $KeyFile"
    }
    if (-not (Test-Path $exportFile)) {
        throw "Export ausente: $exportFile"
    }

    Write-Host "==> Reescrevendo localhost → S3 no JSON exportado" -ForegroundColor Cyan
    node .\scripts\rewrite-cms-loopback-media.js --file=$exportFile
    if ($LASTEXITCODE -ne 0) { throw "rewrite de mídia falhou ($LASTEXITCODE)" }

    Write-Host "==> Sincronizando imagens referenciadas → S3" -ForegroundColor Cyan
    # Precisa AWS_* / CMS_S3_* do .env do Hub (dotenv no script).
    node .\scripts\sync-cms-images-from-json.js --file=$exportFile
    $imgExit = $LASTEXITCODE
    if ($imgExit -eq 2) {
        Write-Host "WARN: algumas imagens não estavam no disco local nem no S3." -ForegroundColor Yellow
    } elseif ($imgExit -ne 0) {
        throw "sync de imagens falhou ($imgExit)"
    }

    Write-Host "==> Enviando $exportFile → EC2 e aplicando" -ForegroundColor Cyan
    $remoteJson = "/tmp/cms-promote-$Key.json"
    $ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
    $scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')

    & scp @scp $exportFile "${User}@${ServerHost}:$remoteJson"
    if ($LASTEXITCODE -ne 0) { throw 'scp falhou' }

    # Garante script apply no servidor (pode estar desatualizado sem git pull)
    & scp @scp (Join-Path $ScriptDir 'apply-cms-site-json.js') "${User}@${ServerHost}:$RemotePath/scripts/apply-cms-site-json.js"
    if ($LASTEXITCODE -ne 0) { throw 'scp apply script falhou' }

    $remoteCmd = @"
set -euo pipefail
cd '$RemotePath'
set -a; . ./.env; set +a
# NODE_PATH para aws-sdk/pg do gateway
export NODE_PATH='$RemotePath/services/gateway-api/node_modules'
node scripts/apply-cms-site-json.js --file='$remoteJson'
# limpa arquivo temporário
rm -f '$remoteJson'
# smoke
curl -fsS '$ProdApiUrl/api/public/cms?config_key=$Key' | head -c 200
echo
"@
    $bashFile = Join-Path $env:TEMP "cms-promote-$Key.sh"
    [System.IO.File]::WriteAllText($bashFile, ($remoteCmd -replace "`r`n", "`n"))
    & scp @scp $bashFile "${User}@${ServerHost}:/tmp/cms-promote-$Key.sh"
    & ssh @ssh "sed -i 's/\r$//' /tmp/cms-promote-$Key.sh; bash /tmp/cms-promote-$Key.sh"
    if ($LASTEXITCODE -ne 0) { throw "apply remoto falhou ($LASTEXITCODE)" }

    Write-Host "`n==> Promote OK: $Key → prod (Postgres + S3)" -ForegroundColor Green
    Write-Host "Verifique /acesso nos satélites (cache ~CMS_CACHE_TTL_SEC)." -ForegroundColor Cyan
}
finally {
    Pop-Location
}
