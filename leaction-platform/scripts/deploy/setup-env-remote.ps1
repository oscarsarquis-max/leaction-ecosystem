<#
.SYNOPSIS
  Grava .env de producao no EC2 (nao commita segredos no repo).

.DESCRIPTION
  Le credenciais Mercado Pago do .env LOCAL (raiz leaction-platform).
  Em producao exige Access Token / Public Key APP_USR- (nunca grava TEST-).
#>
[CmdletBinding()]
param(
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu',
    [string]$RemotePath = '/var/www/leaction-platform',
    # So para ambiente de homologacao remota com chaves TEST (nao use em actionhub.com.br)
    [switch]$AllowTestMpKeys
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '../..')).Path
$KeyFile = if ($env:ACTION_HUB_SSH_KEY) { $env:ACTION_HUB_SSH_KEY } else { Join-Path $RepoRoot 'chaves/action_hub_keys.pem' }
if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile (defina ACTION_HUB_SSH_KEY se usar Instance Connect)" }

function Read-DotenvValue {
    param([string]$FilePath, [string]$Key)
    if (-not (Test-Path $FilePath)) { return '' }
    foreach ($line in Get-Content $FilePath -Encoding UTF8) {
        if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
        $parts = $line.Split('=', 2)
        if ($parts[0].Trim() -eq $Key) { return $parts[1].Trim().Trim('"').Trim("'") }
    }
    return ''
}

$localEnv = Join-Path $RepoRoot '.env'
if (-not (Test-Path $localEnv)) {
    throw "Arquivo $localEnv nao encontrado. Copie de .env.production.example e preencha as chaves reais."
}

$mlAppId = Read-DotenvValue $localEnv 'ML_APP_ID'
$mlSecret = Read-DotenvValue $localEnv 'ML_SECRET_KEY'
$mlPublicBase = Read-DotenvValue $localEnv 'ML_PUBLIC_BASE_URL'
if (-not $mlPublicBase -or $mlPublicBase -match '(?i)localhost|127\.0\.0\.1|ngrok|localtunnel|cloudflared') {
    $mlPublicBase = 'https://actionhub.com.br'
}

$jwtSecret = Read-DotenvValue $localEnv 'JWT_SECRET'
if (-not $jwtSecret -or $jwtSecret -match 'super-secret|change.me|exemplo') {
    throw 'JWT_SECRET forte obrigatorio no .env local (nao use placeholder).'
}

$mpAccess = Read-DotenvValue $localEnv 'MP_ACCESS_TOKEN'
if (-not $mpAccess) { $mpAccess = Read-DotenvValue $localEnv 'MERCADOPAGO_ACCESS_TOKEN' }
$mpPublic = Read-DotenvValue $localEnv 'MP_PUBLIC_KEY'
if (-not $mpPublic) { $mpPublic = Read-DotenvValue $localEnv 'NEXT_PUBLIC_MP_PUBLIC_KEY' }

if (-not $mpAccess -or -not $mpPublic) {
    throw @"
Chaves Mercado Pago ausentes no .env local.
Preencha no painel MP (Credenciais de producao):
  MP_ACCESS_TOKEN=APP_USR-...
  MP_PUBLIC_KEY=APP_USR-...
  NEXT_PUBLIC_MP_PUBLIC_KEY=APP_USR-...   (mesmo valor da Public Key)
"@
}

if (-not $AllowTestMpKeys) {
    if ($mpAccess.StartsWith('TEST-') -or $mpPublic.StartsWith('TEST-')) {
        throw @"
Recusado: chaves TEST detectadas. Producao exige APP_USR-.
Obtenha Credenciais de producao em:
  https://www.mercadopago.com.br/developers/panel/app
Ou use -AllowTestMpKeys apenas em homologacao remota (nao em actionhub.com.br).
"@
    }
    if (-not $mpAccess.StartsWith('APP_USR-') -or -not $mpPublic.StartsWith('APP_USR-')) {
        throw 'MP_ACCESS_TOKEN e MP_PUBLIC_KEY devem comecar com APP_USR- em producao.'
    }
}

$curUser = Read-DotenvValue $localEnv 'MARKETPLACE_CURATION_USER'
if (-not $curUser) { $curUser = 'curadoria' }
$curPass = Read-DotenvValue $localEnv 'MARKETPLACE_CURATION_PASSWORD'
if (-not $curPass) {
    throw 'MARKETPLACE_CURATION_PASSWORD obrigatorio no .env local (sem default fraco).'
}
$curSecret = Read-DotenvValue $localEnv 'MARKETPLACE_CURATION_AUTH_SECRET'
if (-not $curSecret) {
    throw 'MARKETPLACE_CURATION_AUTH_SECRET obrigatorio no .env local.'
}

$webhookInove = Read-DotenvValue $localEnv 'APP_WEBHOOK_URL_INOVE4US'
$prodWebhookInove = 'https://inove4us.com.br/api/webhooks/actionhub'
if (-not $webhookInove) {
    $webhookInove = $prodWebhookInove
} elseif ($webhookInove -match '(?i)localhost|127\.0\.0\.1|0\.0\.0\.0|ngrok|localtunnel|cloudflared') {
    Write-Host "[!] APP_WEBHOOK_URL_INOVE4US local/tunel ignorado em producao -> $prodWebhookInove" -ForegroundColor Yellow
    $webhookInove = $prodWebhookInove
}

function Get-PaneldxDbSecretJson {
    $awsCmd = Get-Command aws -ErrorAction SilentlyContinue
    if ($awsCmd) {
        $out = & aws secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --query SecretString --output text 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return $out }
    }
    # Fallback: AWS CLI via Docker (quando aws.exe nao esta no PATH)
    if (-not $env:AWS_ACCESS_KEY_ID -or -not $env:AWS_SECRET_ACCESS_KEY) {
        throw 'AWS credentials ausentes (AWS_ACCESS_KEY_ID/SECRET) e aws CLI indisponivel.'
    }
    if (-not $env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION = 'us-east-2' }
    $out = docker run --rm `
        -e AWS_ACCESS_KEY_ID `
        -e AWS_SECRET_ACCESS_KEY `
        -e AWS_DEFAULT_REGION `
        public.ecr.aws/aws-cli/aws-cli:latest `
        secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --query SecretString --output text 2>&1
    if ($LASTEXITCODE -ne 0 -or -not $out) { throw "Nao foi possivel ler paneldx-db-credentials: $out" }
    return ($out | Out-String).Trim()
}

$secretJson = Get-PaneldxDbSecretJson
$db = $secretJson | ConvertFrom-Json
$encPass = [uri]::EscapeDataString($db.password)
$dbUrl = 'postgresql://{0}:{1}@{2}:{3}/leaction_hub?sslmode=require' -f $db.username, $encPass, $db.host, $db.port

$adminEmails = Read-DotenvValue $localEnv 'HUB_ADMIN_EMAILS'
if (-not $adminEmails) { $adminEmails = 'admin@actionhub.com.br,sysadmin@inove4us.com.br' }

$prodMasterKey = Read-DotenvValue $localEnv 'PRODUCTION_MASTER_KEY'
if (-not $prodMasterKey) {
    throw 'PRODUCTION_MASTER_KEY obrigatorio no .env local (gatekeeper lock/unlock/bypass).'
}

$crmTrackingSecret = Read-DotenvValue $localEnv 'CRM_TRACKING_SECRET'
if (-not $crmTrackingSecret) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $crmTrackingSecret = [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
    Write-Host '[!] CRM_TRACKING_SECRET ausente no .env local - gerado para este deploy (salve no .env local).' -ForegroundColor Yellow
}

$nl = [Environment]::NewLine
$rootLines = @(
    "DATABASE_URL=$dbUrl",
    'ACTION_HUB_PUBLIC_URL=https://actionhub.com.br',
    'GATEWAY_PORT=4001',
    'NODE_ENV=production',
    "JWT_SECRET=$jwtSecret",
    "HUB_ADMIN_EMAILS=$adminEmails",
    "APP_WEBHOOK_URL_INOVE4US=$webhookInove",
    "MP_ACCESS_TOKEN=$mpAccess",
    "MP_PUBLIC_KEY=$mpPublic",
    'MP_SUBSCRIPTION_REASON="Assinatura Mensal - Leaction Hub"',
    'MP_SUBSCRIPTION_AMOUNT=99',
    'MP_SUBSCRIPTION_CURRENCY=BRL',
    'MP_SUBSCRIPTION_FREQUENCY=1',
    'MP_SUBSCRIPTION_FREQUENCY_TYPE=months',
    'MP_CHECKOUT_MODE=card',
    'ALLOW_PAYMENT_SIMULATION=0',
    ('PRODUCTION_MASTER_KEY="{0}"' -f $prodMasterKey),
    "CRM_TRACKING_SECRET=$crmTrackingSecret",
    'MARKETPLACE_PORT=4012',
    "ML_PUBLIC_BASE_URL=$mlPublicBase",
    'ML_TOKENS_FILE=/var/lib/leaction-platform/.ml_tokens.json'
)
if ($mlAppId) { $rootLines += "ML_APP_ID=$mlAppId" }
if ($mlSecret) { $rootLines += "ML_SECRET_KEY=$mlSecret" }
$rootEnv = ($rootLines -join $nl)

$feLines = @(
    'NODE_ENV=production',
    'PORT=4000',
    'ACTION_HUB_PUBLIC_URL=https://actionhub.com.br',
    'HUB_GATEWAY_INTERNAL_URL=http://127.0.0.1:4001',
    'MARKETPLACE_INTERNAL_URL=http://127.0.0.1:4012',
    'NEXT_PUBLIC_PANELDX_URL=',
    "JWT_SECRET=$jwtSecret",
    "HUB_ADMIN_EMAILS=$adminEmails",
    "NEXT_PUBLIC_HUB_ADMIN_EMAILS=$adminEmails",
    "NEXT_PUBLIC_MP_PUBLIC_KEY=$mpPublic",
    'NEXT_PUBLIC_MP_SUBSCRIPTION_AMOUNT=99',
    ('PRODUCTION_MASTER_KEY="{0}"' -f $prodMasterKey),
    "CRM_TRACKING_SECRET=$crmTrackingSecret",
    "MARKETPLACE_CURATION_USER=$curUser",
    "MARKETPLACE_CURATION_PASSWORD=$curPass",
    "MARKETPLACE_CURATION_AUTH_SECRET=$curSecret"
)
$feEnv = ($feLines -join $nl)

$sshTarget = ($User + '@' + $ServerHost)
$rootTmp = Join-Path $env:TEMP 'action-hub-root.env'
$feTmp = Join-Path $env:TEMP 'action-hub-fe.env.production'
function Write-UnixEnvFile([string]$Path, [string]$Content) {
    $normalized = ($Content -replace "`r`n", "`n" -replace "`r", "`n").Trim() + "`n"
    [System.IO.File]::WriteAllBytes($Path, [Text.Encoding]::UTF8.GetBytes($normalized))
}

Write-UnixEnvFile $rootTmp $rootEnv.Trim()
Write-UnixEnvFile $feTmp $feEnv.Trim()

& ssh -i $KeyFile -o StrictHostKeyChecking=no $sshTarget "mkdir -p $RemotePath/frontend/action-hub $RemotePath/backend"
& scp -i $KeyFile -o StrictHostKeyChecking=no $rootTmp ($sshTarget + ':' + $RemotePath + '/.env')
& scp -i $KeyFile -o StrictHostKeyChecking=no $feTmp ($sshTarget + ':' + $RemotePath + '/frontend/action-hub/.env.production')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao enviar .env' }

Remove-Item $rootTmp, $feTmp -Force -ErrorAction SilentlyContinue
Write-Host "[OK] .env de producao gravado em $RemotePath" -ForegroundColor Green
Write-Host ("[OK] MP Public Key prefix: {0}..." -f $mpPublic.Substring(0, [Math]::Min(12, $mpPublic.Length))) -ForegroundColor Green
if ($mlAppId -and $mlSecret) {
    Write-Host '[OK] Credenciais ML Marketplace incluidas' -ForegroundColor Green
} else {
    Write-Host '[!] ML_APP_ID/ML_SECRET_KEY ausentes no .env local' -ForegroundColor Yellow
}
