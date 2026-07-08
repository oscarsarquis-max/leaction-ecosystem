<#
.SYNOPSIS
  Restaura o catálogo eSIM no RDS (provedor Base Mobile + 3 eventos padrão).

.EXAMPLE
  .\scripts\deploy\10-seed-esim-catalog.ps1 -ViaEc2
#>
[CmdletBinding()]
param(
    [switch]$ViaEc2,
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$SeedScript = Join-Path $RepoRoot 'scripts/seed_esim_catalog.py'
$Python = Join-Path $RepoRoot 'venv_action/Scripts/python.exe'

function Get-RdsCredentials {
    $secretJson = cmd /c "aws secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --no-verify-ssl --query SecretString --output text 2>nul"
    if ($LASTEXITCODE -ne 0) {
        throw 'Nao foi possivel ler paneldx-db-credentials no Secrets Manager'
    }
    return $secretJson | ConvertFrom-Json
}

$db = Get-RdsCredentials
Write-Host "`n==> Seed catálogo eSIM no RDS" -ForegroundColor Cyan
Write-Host "    Host: $($db.host)" -ForegroundColor Yellow

if ($ViaEc2) {
    $KeyFile = Join-Path (Resolve-Path (Join-Path $RepoRoot '../leaction-platform')).Path 'chaves/action_hub_keys.pem'
    if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile" }

    $ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
    $scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')
    $remoteSeed = '/tmp/paneldx-seed_esim_catalog.py'
    $remoteVenv = '/tmp/paneldx-esim-venv'

    & scp @scp $SeedScript "${User}@${ServerHost}:$remoteSeed"
    if ($LASTEXITCODE -ne 0) { throw 'scp do seed eSIM falhou' }

    $remoteCmd = @(
        "export DB_HOST='$($db.host)'",
        "export DB_PORT='$($db.port)'",
        "export DB_NAME='LeAction_SysF'",
        "export DB_USER='$($db.username)'",
        "export DB_PASS='$($db.password -replace "'", "'\''")'",
        "export DB_SSLMODE='require'",
        "export SEED_DEV_ALLOW='1'",
        "export SEED_PROD_CONFIRM='paneldx-esim-catalog'",
        "python3 -m venv $remoteVenv",
        "$remoteVenv/bin/pip install -q psycopg2-binary",
        "$remoteVenv/bin/python $remoteSeed",
        "rm -rf $remoteVenv $remoteSeed"
    ) -join ' && '

    & ssh @ssh $remoteCmd
    if ($LASTEXITCODE -ne 0) { throw 'Seed eSIM via EC2 falhou' }
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
    $env:SEED_PROD_CONFIRM = 'paneldx-esim-catalog'

    Push-Location $RepoRoot
    try {
        & $Python $SeedScript
        if ($LASTEXITCODE -ne 0) { throw "seed_esim_catalog.py falhou (exit $LASTEXITCODE)" }
    } finally {
        Pop-Location
    }
}

Write-Host "`n==> Catálogo eSIM restaurado." -ForegroundColor Green
Write-Host 'Verifique: https://paneldx.com.br/admin/esim (login sysadmin)' -ForegroundColor Gray
