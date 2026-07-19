<#
.SYNOPSIS
  Aplica o seed de demonstracao no RDS PanelDX (mesma estrutura do seed_dev_client.py local).

  Remove e recria SOMENTE os 3 usuarios demo e os dados vinculados a eles.
  Nao apaga outros clientes ou projetos do banco.

.PARAMETER Stage
  1=login | 2=pre-survey | 3=avaliacao completa | 4=plano + Kanban mock

.PARAMETER ConfirmDemoReset
  Obrigatorio — confirma reset dos usuarios demo (nao da base inteira).

.PARAMETER ViaEc2
  Executa via EC2 Action Hub (recomendado — RDS na VPC privada).

.EXAMPLE
  .\scripts\deploy\09-seed-prod-demo.ps1 -Stage 1 -ConfirmDemoReset -ViaEc2
#>
[CmdletBinding()]
param(
    [ValidateSet(1, 2, 3, 4)]
    [int]$Stage = 1,
    [switch]$ConfirmDemoReset,
    [switch]$ViaEc2,
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$SeedScript = Join-Path $RepoRoot 'seed_dev_client.py'
$Python = Join-Path $RepoRoot 'venv_action/Scripts/python.exe'

if (-not $ConfirmDemoReset) {
    throw @'
Confirmacao obrigatoria: -ConfirmDemoReset

Remove e recria apenas:
  • sysadmin@leaction.com.br  (senha PanelDX1!)
  • executor@paneldx.com.br   (senha PanelDX1!)
  • sistema@paneldx.com.br    (codigo LA-PANEL1) e todo o funil desse cliente

Outros clientes e projetos do RDS NAO sao apagados.
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
Write-Host "`n==> Seed demo RDS - estagio $Stage" -ForegroundColor Cyan
Write-Host "    Host: $($db.host)" -ForegroundColor Yellow
Write-Host "    Escopo: somente usuarios demo (sem TRUNCATE global)." -ForegroundColor Green

if ($ViaEc2) {
    $KeyFile = Join-Path (Resolve-Path (Join-Path $RepoRoot '../leaction-platform')).Path 'chaves/action_hub_keys.pem'
    if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile" }

    $ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
    $scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')
    $remoteDir = '/tmp/paneldx-seed'
    $remoteVenv = '/tmp/paneldx-seed-venv'

    & ssh @ssh "rm -rf $remoteDir && mkdir -p $remoteDir/LeAction_SysF"
    & scp @scp $SeedScript "${User}@${ServerHost}:$remoteDir/seed_dev_client.py"
    & scp @scp (Join-Path $RepoRoot 'LeAction_SysF/sprint_squad.py') "${User}@${ServerHost}:$remoteDir/LeAction_SysF/"
    if ($LASTEXITCODE -ne 0) { throw 'scp do seed falhou' }

    $remoteCmd = @(
        "export DB_HOST='$($db.host)'",
        "export DB_PORT='$($db.port)'",
        "export DB_NAME='LeAction_SysF'",
        "export DB_USER='$($db.username)'",
        "export DB_PASS='$($db.password -replace "'", "'\''")'",
        "export DB_SSLMODE='require'",
        "export SEED_DEV_ALLOW='1'",
        "export SEED_PROD_CONFIRM='paneldx-demo-users'",
        "export SEED_TEAM_PASSWORD='PanelDX1!'",
        "python3 -m venv $remoteVenv",
        "$remoteVenv/bin/pip install -q psycopg2-binary werkzeug",
        "cd $remoteDir && PYTHONPATH=$remoteDir/LeAction_SysF $remoteVenv/bin/python seed_dev_client.py $Stage",
        "rm -rf $remoteDir $remoteVenv"
    ) -join ' && '

    & ssh @ssh $remoteCmd
    if ($LASTEXITCODE -ne 0) { throw 'Seed via EC2 falhou' }
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
    $env:SEED_PROD_CONFIRM = 'paneldx-demo-users'
    $env:SEED_TEAM_PASSWORD = 'PanelDX1!'

    Push-Location $RepoRoot
    try {
        & $Python $SeedScript $Stage
        if ($LASTEXITCODE -ne 0) { throw "seed_dev_client.py falhou (exit $LASTEXITCODE)" }
    } finally {
        Pop-Location
    }
}

Write-Host "`n==> Seed producao concluido (estagio $Stage)." -ForegroundColor Green
Write-Host 'Credenciais (producao):' -ForegroundColor Gray
Write-Host '  Lead     : sistema@paneldx.com.br  /  LA-PANEL1' -ForegroundColor Gray
Write-Host '  Sysadmin : sysadmin@leaction.com.br  /  PanelDX1!' -ForegroundColor Gray
Write-Host '  Executor : executor@paneldx.com.br   /  PanelDX1!' -ForegroundColor Gray
