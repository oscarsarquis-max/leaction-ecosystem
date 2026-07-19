<#
.SYNOPSIS
  Seed de producao — SOMENTE sistema@paneldx.com.br (lead demo LA-PANEL1).

  Remove e recria exclusivamente o cliente/funil desse e-mail.
  Nao toca em sysadmin, executor, consultores nem outros clientes.

.PARAMETER Stage
  1=login | 2=pre-survey | 3=avaliacao completa | 4=plano + Kanban mock

.PARAMETER ConfirmLeadReset
  Obrigatorio — confirma reset apenas do lead sistema@paneldx.com.br.

.PARAMETER ViaEc2
  Executa via EC2 Action Hub (recomendado — RDS na VPC privada).

.EXAMPLE
  .\scripts\deploy\12-seed-prod-lead-only.ps1 -Stage 1 -ConfirmLeadReset -ViaEc2
#>
[CmdletBinding()]
param(
    [ValidateSet(1, 2, 3, 4)]
    [int]$Stage = 1,
    [switch]$ConfirmLeadReset,
    [switch]$ViaEc2,
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$SeedScript = Join-Path $RepoRoot 'scripts/seed_prod_lead_paneldx.py'
$Python = Join-Path $RepoRoot 'venv_action/Scripts/python.exe'

if (-not $ConfirmLeadReset) {
    throw @'
Confirmacao obrigatoria: -ConfirmLeadReset

Remove e recria APENAS:
  • sistema@paneldx.com.br  (codigo LA-PANEL1) e todo o funil desse cliente

NAO remove sysadmin, executor, consultores nem outros clientes do RDS.
'@
}

function Get-RdsCredentials {
    $secretJson = cmd /c "aws secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --no-verify-ssl --query SecretString --output text 2>nul"
    if ($LASTEXITCODE -ne 0) {
        throw 'Nao foi possivel ler paneldx-db-credentials no Secrets Manager'
    }
    return $secretJson | ConvertFrom-Json
}

$db = Get-RdsCredentials
Write-Host "`n==> Seed lead RDS (somente sistema@paneldx.com.br) - estagio $Stage" -ForegroundColor Cyan
Write-Host "    Host: $($db.host)" -ForegroundColor Yellow
Write-Host "    Escopo: lead demo isolado (sem sysadmin/executor)." -ForegroundColor Green

if ($ViaEc2) {
    $KeyFile = Join-Path (Resolve-Path (Join-Path $RepoRoot '../leaction-platform')).Path 'chaves/action_hub_keys.pem'
    if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile" }

    $ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
    $scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')
    $remoteDir = '/tmp/paneldx-seed-lead'
    $remoteVenv = '/tmp/paneldx-seed-lead-venv'

    & ssh @ssh "rm -rf $remoteDir && mkdir -p $remoteDir/scripts $remoteDir/LeAction_SysF"
    & scp @scp $SeedScript "${User}@${ServerHost}:$remoteDir/scripts/seed_prod_lead_paneldx.py"
    & scp @scp (Join-Path $RepoRoot 'seed_dev_client.py') "${User}@${ServerHost}:$remoteDir/seed_dev_client.py"
    & scp @scp (Join-Path $RepoRoot 'LeAction_SysF/sprint_squad.py') "${User}@${ServerHost}:$remoteDir/LeAction_SysF/"
    if ($LASTEXITCODE -ne 0) { throw 'scp do seed lead falhou' }

    $remoteCmd = @(
        "export DB_HOST='$($db.host)'",
        "export DB_PORT='$($db.port)'",
        "export DB_NAME='LeAction_SysF'",
        "export DB_USER='$($db.username)'",
        "export DB_PASS='$($db.password -replace "'", "'\''")'",
        "export DB_SSLMODE='require'",
        "export SEED_DEV_ALLOW='1'",
        "export SEED_PROD_CONFIRM='paneldx-demo-lead'",
        "python3 -m venv $remoteVenv",
        "$remoteVenv/bin/pip install -q psycopg2-binary werkzeug python-dotenv",
        "cd $remoteDir && PYTHONPATH=$remoteDir/LeAction_SysF $remoteVenv/bin/python scripts/seed_prod_lead_paneldx.py $Stage",
        "rm -rf $remoteDir $remoteVenv"
    ) -join ' && '

    & ssh @ssh $remoteCmd
    if ($LASTEXITCODE -ne 0) { throw 'Seed lead via EC2 falhou' }
} else {
    if (-not (Test-Path $Python)) {
        throw "Python local nao encontrado: $Python. Use -ViaEc2 ou crie venv_action."
    }

    $env:DB_HOST = $db.host
    $env:DB_PORT = [string]$db.port
    $env:DB_NAME = 'LeAction_SysF'
    $env:DB_USER = $db.username
    $env:DB_PASS = $db.password
    $env:DB_SSLMODE = 'require'
    $env:SEED_DEV_ALLOW = '1'
    $env:SEED_PROD_CONFIRM = 'paneldx-demo-lead'

    Push-Location $RepoRoot
    try {
        & $Python $SeedScript $Stage
        if ($LASTEXITCODE -ne 0) { throw "seed_prod_lead_paneldx.py falhou (exit $LASTEXITCODE)" }
    } finally {
        Pop-Location
    }
}

Write-Host "`n==> Seed lead producao concluido (estagio $Stage)." -ForegroundColor Green
Write-Host 'Credencial:' -ForegroundColor Gray
Write-Host '  Lead: sistema@paneldx.com.br  /  LA-PANEL1' -ForegroundColor Gray
