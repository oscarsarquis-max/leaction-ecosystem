<#
.SYNOPSIS
  Envia codigo ao EC2 action_hub_prod e executa remote-install.sh

.EXAMPLE
  .\scripts\deploy\deploy-remote.ps1 -InitDb
#>
[CmdletBinding()]
param(
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu',
    [string]$RemotePath = '/var/www/leaction-platform',
    [switch]$InitDb,
    [switch]$MigrateDb,
    [switch]$SkipSync
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '../..')).Path
$KeyFile = Join-Path $RepoRoot 'chaves/action_hub_keys.pem'

if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile" }

$ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
$scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')

function Invoke-Ssh([string]$Cmd) {
    & ssh @ssh $Cmd
    if ($LASTEXITCODE -ne 0) { throw "SSH falhou: $Cmd" }
}

if (-not $SkipSync) {
    Write-Host "`n==> Backup tokens ML (persistente)" -ForegroundColor Cyan
    Invoke-Ssh @"
mkdir -p /var/lib/leaction-platform
if [ -f $RemotePath/backend/.ml_tokens.json ]; then
  cp $RemotePath/backend/.ml_tokens.json /var/lib/leaction-platform/.ml_tokens.json
fi
"@

    Write-Host "`n==> Preparando diretorio remoto" -ForegroundColor Cyan
    Invoke-Ssh "sudo rm -rf $RemotePath && sudo mkdir -p $RemotePath && sudo chown -R ${User}:${User} $RemotePath && chmod -R u+rwX $RemotePath"

    Write-Host "==> Enviando codigo (zip, sem node_modules/.next)" -ForegroundColor Cyan
    Push-Location $RepoRoot
    try {
        $zipPath = Join-Path $env:TEMP 'leaction-platform-deploy.zip'
        if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

        $stage = Join-Path $env:TEMP 'leaction-platform-stage'
        if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
        New-Item -ItemType Directory -Path $stage | Out-Null

        $copyItems = @(
            'ecosystem.config.js', 'nginx.conf', 'docker-compose.yml', '.env.production.example', '.gitignore',
            'scripts', 'services', 'shared', 'frontend', 'backend'
        )
        foreach ($item in $copyItems) {
            $src = Join-Path $RepoRoot $item
            if (Test-Path $src) {
                Copy-Item -Path $src -Destination (Join-Path $stage $item) -Recurse -Force
            }
        }
        Get-ChildItem -Path $stage -Recurse -Directory -Filter node_modules | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Path $stage -Recurse -Directory -Filter .next | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path (Join-Path $stage 'services/analysis-engine')) {
            Remove-Item (Join-Path $stage 'services/analysis-engine') -Recurse -Force
        }

        Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zipPath -Force
        Remove-Item $stage -Recurse -Force

        & scp @scp $zipPath "${User}@${ServerHost}:/tmp/leaction-platform-deploy.zip"
        if ($LASTEXITCODE -ne 0) { throw 'scp falhou' }
        Invoke-Ssh "cd $RemotePath && unzip -o /tmp/leaction-platform-deploy.zip >/dev/null 2>&1; rm -f /tmp/leaction-platform-deploy.zip; sudo chattr -R -i $RemotePath 2>/dev/null || true; chmod -R u+rwX $RemotePath; sudo chmod -R a+rwX $RemotePath/frontend/action-hub; test -f frontend/action-hub/package.json"
        & (Join-Path $ScriptDir 'setup-env-remote.ps1') -ServerHost $ServerHost -User $User -RemotePath $RemotePath
        Invoke-Ssh "sudo mkdir -p /var/lib/leaction-platform && sudo chown ${User}:${User} /var/lib/leaction-platform && chmod 700 /var/lib/leaction-platform"
    }
    finally {
        Pop-Location
    }
}

Write-Host "==> Permissoes scripts" -ForegroundColor Cyan
Invoke-Ssh "chmod +x $RemotePath/scripts/deploy/*.sh && sed -i 's/\r$//' $RemotePath/scripts/deploy/*.sh"

if ($InitDb) {
    Write-Host "==> Inicializando banco (leaction_hub)" -ForegroundColor Cyan
    $secretJson = cmd /c "aws secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --no-verify-ssl --query SecretString --output text 2>nul"
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel ler paneldx-db-credentials para migrations' }
    $db = $secretJson | ConvertFrom-Json
    $encPass = [uri]::EscapeDataString($db.password)
    $dbUrl = "postgresql://$($db.username):${encPass}@$($db.host):$($db.port)/leaction_hub?sslmode=require"
    $escapedUrl = $dbUrl.Replace("'", "'\''")
    Invoke-Ssh "cd $RemotePath && export DATABASE_URL='$escapedUrl' && APP_ROOT=$RemotePath bash scripts/deploy/remote-db-init.sh"
}

if ($MigrateDb) {
    Write-Host "==> Aplicando patches no banco (leaction_hub)" -ForegroundColor Cyan
    $secretJson = cmd /c "aws secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --no-verify-ssl --query SecretString --output text 2>nul"
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel ler paneldx-db-credentials para migrations' }
    $db = $secretJson | ConvertFrom-Json
    $encPass = [uri]::EscapeDataString($db.password)
    $dbUrl = "postgresql://$($db.username):${encPass}@$($db.host):$($db.port)/leaction_hub?sslmode=require"
    $escapedUrl = $dbUrl.Replace("'", "'\''")
    Invoke-Ssh "cd $RemotePath && export DATABASE_URL='$escapedUrl' && APP_ROOT=$RemotePath bash scripts/deploy/remote-db-migrate.sh"
}

Write-Host "==> Install + PM2 + Nginx" -ForegroundColor Cyan
Invoke-Ssh "cd $RemotePath && bash scripts/deploy/remote-install.sh"

Write-Host "`n==> Deploy remoto Action Hub concluido." -ForegroundColor Green
