<#
.SYNOPSIS
  Seed de consultores demo no RDS PanelDX (Portal do Parceiro).

  Cria/atualiza os 4 consultores demo e vinculos em contratos de teste.
  Nao apaga outros usuarios nem clientes (upsert idempotente).

.PARAMETER ConfirmConsultoresSeed
  Obrigatorio em producao.

.PARAMETER ViaEc2
  Executa via EC2 Action Hub (recomendado).

.EXAMPLE
  .\scripts\deploy\13-seed-prod-consultores.ps1 -ConfirmConsultoresSeed -ViaEc2
#>
[CmdletBinding()]
param(
    [switch]$ConfirmConsultoresSeed,
    [switch]$ViaEc2,
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$SeedScript = Join-Path $RepoRoot 'scripts/seed_consultores_demo.py'
$Python = Join-Path $RepoRoot 'venv_action/Scripts/python.exe'

if (-not $ConfirmConsultoresSeed) {
    throw 'Confirmacao obrigatoria: -ConfirmConsultoresSeed'
}

function Get-RdsCredentials {
    $secretJson = cmd /c "aws secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --no-verify-ssl --query SecretString --output text 2>nul"
    if ($LASTEXITCODE -ne 0) {
        throw 'Nao foi possivel ler paneldx-db-credentials no Secrets Manager'
    }
    return $secretJson | ConvertFrom-Json
}

$db = Get-RdsCredentials
Write-Host "`n==> Seed consultores demo RDS" -ForegroundColor Cyan
Write-Host "    Host: $($db.host)" -ForegroundColor Yellow

if ($ViaEc2) {
    $KeyFile = Join-Path (Resolve-Path (Join-Path $RepoRoot '../leaction-platform')).Path 'chaves/action_hub_keys.pem'
    if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile" }

    $ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
    $scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')
    $remoteDir = '/tmp/paneldx-seed-consultores'
    $remoteVenv = '/tmp/paneldx-seed-consultores-venv'

    & ssh @ssh "rm -rf $remoteDir && mkdir -p $remoteDir/scripts"
    & scp @scp $SeedScript "${User}@${ServerHost}:$remoteDir/scripts/seed_consultores_demo.py"
    if ($LASTEXITCODE -ne 0) { throw 'scp consultores falhou' }

    $remoteCmd = @(
        "export DB_HOST='$($db.host)'",
        "export DB_PORT='$($db.port)'",
        "export DB_NAME='LeAction_SysF'",
        "export DB_USER='$($db.username)'",
        "export DB_PASS='$($db.password -replace "'", "'\''")'",
        "export DB_SSLMODE='require'",
        "export SEED_DEV_ALLOW='1'",
        "export SEED_PROD_CONFIRM='paneldx-demo-consultores'",
        "python3 -m venv $remoteVenv",
        "$remoteVenv/bin/pip install -q psycopg2-binary werkzeug python-dotenv",
        "cd $remoteDir && $remoteVenv/bin/python scripts/seed_consultores_demo.py",
        "rm -rf $remoteDir $remoteVenv"
    ) -join ' && '

    & ssh @ssh $remoteCmd
    if ($LASTEXITCODE -ne 0) { throw 'Seed consultores via EC2 falhou' }
} else {
    if (-not (Test-Path $Python)) {
        throw "Python local nao encontrado: $Python. Use -ViaEc2."
    }

    $env:DB_HOST = $db.host
    $env:DB_PORT = [string]$db.port
    $env:DB_NAME = 'LeAction_SysF'
    $env:DB_USER = $db.username
    $env:DB_PASS = $db.password
    $env:DB_SSLMODE = 'require'
    $env:SEED_DEV_ALLOW = '1'
    $env:SEED_PROD_CONFIRM = 'paneldx-demo-consultores'

    Push-Location $RepoRoot
    try {
        & $Python $SeedScript
        if ($LASTEXITCODE -ne 0) { throw "seed_consultores_demo.py falhou" }
    } finally {
        Pop-Location
    }
}

Write-Host "`n==> Consultores demo criados/atualizados." -ForegroundColor Green
Write-Host 'Senha para todos: Consultor@2026' -ForegroundColor Gray
Write-Host '  consultor.agencia.alpha@leaction.com.br' -ForegroundColor Gray
Write-Host '  consultor.joao@leaction.com.br' -ForegroundColor Gray
Write-Host '  consultor.maria@leaction.com.br' -ForegroundColor Gray
Write-Host '  consultor@paneldx.com.br' -ForegroundColor Gray
