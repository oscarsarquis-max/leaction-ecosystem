<#
.SYNOPSIS
  Grava .env de producao no EC2 (nao commita segredos no repo).
#>
[CmdletBinding()]
param(
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu',
    [string]$RemotePath = '/var/www/leaction-platform'
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '../..')).Path
$KeyFile = Join-Path $RepoRoot 'chaves/action_hub_keys.pem'

function Read-DotenvValue {
    param([string]$FilePath, [string]$Key)
    if (-not (Test-Path $FilePath)) { return '' }
    foreach ($line in Get-Content $FilePath -Encoding UTF8) {
        if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
        $parts = $line.Split('=', 2)
        if ($parts[0].Trim() -eq $Key) { return $parts[1].Trim() }
    }
    return ''
}

$localEnv = Join-Path $RepoRoot '.env'
$mlAppId = Read-DotenvValue $localEnv 'ML_APP_ID'
$mlSecret = Read-DotenvValue $localEnv 'ML_SECRET_KEY'
$mlPublicBase = Read-DotenvValue $localEnv 'ML_PUBLIC_BASE_URL'
if (-not $mlPublicBase) { $mlPublicBase = 'https://actionhub.com.br' }

$curUser = Read-DotenvValue $localEnv 'MARKETPLACE_CURATION_USER'
if (-not $curUser) { $curUser = 'curadoria' }
$curPass = Read-DotenvValue $localEnv 'MARKETPLACE_CURATION_PASSWORD'
if (-not $curPass) { $curPass = 'ActionHub@Curadoria2026' }
$curSecret = Read-DotenvValue $localEnv 'MARKETPLACE_CURATION_AUTH_SECRET'
if (-not $curSecret) { $curSecret = 'leaction-mp-curation-session-key-2026-prod' }

$secretJson = cmd /c "aws secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --no-verify-ssl --query SecretString --output text 2>nul"
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel ler paneldx-db-credentials' }
$db = $secretJson | ConvertFrom-Json
$encPass = [uri]::EscapeDataString($db.password)
$dbUrl = "postgresql://$($db.username):${encPass}@$($db.host):$($db.port)/leaction_hub?sslmode=require"

$rootEnv = @"
DATABASE_URL=$dbUrl
ACTION_HUB_PUBLIC_URL=https://actionhub.com.br
GATEWAY_PORT=4001
JWT_SECRET=super-secret-hub-key-2026
MP_ACCESS_TOKEN=TEST-3871797996578626-062312-7af5da37a9be87bbe4f67213b76a60d7-3494102340
MP_PUBLIC_KEY=TEST-2de295aa-f19b-474a-9a38-1496cc0db7aa
MP_SUBSCRIPTION_REASON="Assinatura Mensal - Leaction Hub"
MP_SUBSCRIPTION_AMOUNT=99
MP_SUBSCRIPTION_CURRENCY=BRL
MP_SUBSCRIPTION_FREQUENCY=1
MP_SUBSCRIPTION_FREQUENCY_TYPE=months
MP_CHECKOUT_MODE=card
MP_PANELDX_PAYMENT_AMOUNT=1
MARKETPLACE_PORT=4012
ML_PUBLIC_BASE_URL=$mlPublicBase
ML_TOKENS_FILE=/var/lib/leaction-platform/.ml_tokens.json
"@

if ($mlAppId) { $rootEnv += "`nML_APP_ID=$mlAppId" }
if ($mlSecret) { $rootEnv += "`nML_SECRET_KEY=$mlSecret" }

$feEnv = @"
NODE_ENV=production
PORT=4000
HUB_GATEWAY_INTERNAL_URL=http://127.0.0.1:4001
MARKETPLACE_INTERNAL_URL=http://127.0.0.1:4012
NEXT_PUBLIC_PANELDX_URL=
NEXT_PUBLIC_MP_PUBLIC_KEY=TEST-2de295aa-f19b-474a-9a38-1496cc0db7aa
NEXT_PUBLIC_MP_SUBSCRIPTION_AMOUNT=99
NEXT_PUBLIC_MP_PANELDX_PAYMENT_AMOUNT=1
MARKETPLACE_CURATION_USER=$curUser
MARKETPLACE_CURATION_PASSWORD=$curPass
MARKETPLACE_CURATION_AUTH_SECRET=$curSecret
"@

$sshTarget = "${User}@${ServerHost}"
$rootTmp = Join-Path $env:TEMP 'action-hub-root.env'
$feTmp = Join-Path $env:TEMP 'action-hub-fe.env.production'
function Write-UnixEnvFile([string]$Path, [string]$Content) {
    $normalized = ($Content -replace "`r`n", "`n" -replace "`r", "`n").Trim() + "`n"
    [System.IO.File]::WriteAllBytes($Path, [Text.Encoding]::UTF8.GetBytes($normalized))
}

Write-UnixEnvFile $rootTmp $rootEnv.Trim()
Write-UnixEnvFile $feTmp $feEnv.Trim()

& ssh -i $KeyFile -o StrictHostKeyChecking=no $sshTarget "mkdir -p $RemotePath/frontend/action-hub $RemotePath/backend"
& scp -i $KeyFile -o StrictHostKeyChecking=no $rootTmp "${sshTarget}:${RemotePath}/.env"
& scp -i $KeyFile -o StrictHostKeyChecking=no $feTmp "${sshTarget}:${RemotePath}/frontend/action-hub/.env.production"
if ($LASTEXITCODE -ne 0) { throw 'Falha ao enviar .env' }

Remove-Item $rootTmp, $feTmp -Force -ErrorAction SilentlyContinue
Write-Host "[OK] .env de producao gravado em $RemotePath" -ForegroundColor Green
if ($mlAppId -and $mlSecret) {
    Write-Host "[OK] Credenciais ML Marketplace incluidas" -ForegroundColor Green
} else {
    Write-Host "[!] ML_APP_ID/ML_SECRET_KEY ausentes no .env local" -ForegroundColor Yellow
}
