<#
.SYNOPSIS
  Repara squads faltantes nas sprints do lead demo (sem reset completo).
#>
[CmdletBinding()]
param(
    [switch]$ViaEc2,
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path

function Get-RdsCredentials {
    $secretJson = cmd /c "aws secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --no-verify-ssl --query SecretString --output text 2>nul"
    if ($LASTEXITCODE -ne 0) { throw 'Secrets Manager indisponivel' }
    return $secretJson | ConvertFrom-Json
}

$db = Get-RdsCredentials
Write-Host "`n==> Reparar squads demo no RDS" -ForegroundColor Cyan

if ($ViaEc2) {
    $KeyFile = Join-Path (Resolve-Path (Join-Path $RepoRoot '../leaction-platform')).Path 'chaves/action_hub_keys.pem'
    $remoteDir = '/tmp/paneldx-repair'
    $remoteVenv = '/tmp/paneldx-repair-venv'
    $ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
    $scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')

    & ssh @ssh "rm -rf $remoteDir && mkdir -p $remoteDir/LeAction_SysF $remoteDir/scripts"
    & scp @scp (Join-Path $RepoRoot 'seed_dev_client.py') "${User}@${ServerHost}:$remoteDir/"
    & scp @scp (Join-Path $RepoRoot 'LeAction_SysF/sprint_squad.py') "${User}@${ServerHost}:$remoteDir/LeAction_SysF/"
    & scp @scp (Join-Path $RepoRoot 'scripts/repair_demo_squads.py') "${User}@${ServerHost}:$remoteDir/scripts/"

    $remoteCmd = @(
        "export DB_HOST='$($db.host)'",
        "export DB_PORT='$($db.port)'",
        "export DB_NAME='LeAction_SysF'",
        "export DB_USER='$($db.username)'",
        "export DB_PASS='$($db.password -replace "'", "'\''")'",
        "export DB_SSLMODE='require'",
        "export SEED_DEV_ALLOW='1'",
        "export SEED_PROD_CONFIRM='paneldx-repair-squads'",
        "python3 -m venv $remoteVenv",
        "$remoteVenv/bin/pip install -q psycopg2-binary werkzeug",
        "cd $remoteDir && PYTHONPATH=$remoteDir/LeAction_SysF $remoteVenv/bin/python scripts/repair_demo_squads.py",
        "rm -rf $remoteDir $remoteVenv"
    ) -join ' && '

    & ssh @ssh $remoteCmd
    if ($LASTEXITCODE -ne 0) { throw 'Reparo via EC2 falhou' }
} else {
    $Python = Join-Path $RepoRoot 'venv_action/Scripts/python.exe'
    if (-not (Test-Path $Python)) { throw 'Use -ViaEc2 ou crie venv_action' }
    $env:DB_HOST = $db.host
    $env:DB_PORT = [string]$db.port
    $env:DB_NAME = 'LeAction_SysF'
    $env:DB_USER = $db.username
    $env:DB_PASS = $db.password
    $env:DB_SSLMODE = 'require'
    $env:SEED_DEV_ALLOW = '1'
    $env:SEED_PROD_CONFIRM = 'paneldx-repair-squads'
    Push-Location $RepoRoot
    try {
        & $Python (Join-Path $RepoRoot 'scripts/repair_demo_squads.py')
    } finally { Pop-Location }
}

Write-Host "`n==> Reparo concluido." -ForegroundColor Green
