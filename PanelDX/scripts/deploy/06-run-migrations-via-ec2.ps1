<#
.SYNOPSIS
  Aplica migrations PanelDX no RDS via EC2 Action Hub (mesma VPC do RDS).

.EXAMPLE
  .\scripts\deploy\06-run-migrations-via-ec2.ps1
  .\scripts\deploy\06-run-migrations-via-ec2.ps1 -Only 004_leaf_dime_area_escolar.sql,005_agenda_eventos.sql
#>
[CmdletBinding()]
param(
    [string]$ServerHost = '3.17.19.188',
    [string]$User = 'ubuntu',
    [string[]]$Only
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$MigrationsDir = Join-Path $RepoRoot 'migrations'
$KeyFile = Join-Path (Resolve-Path (Join-Path $RepoRoot '../leaction-platform')).Path 'chaves/action_hub_keys.pem'

if (-not (Test-Path $KeyFile)) {
    throw "Chave SSH nao encontrada: $KeyFile"
}

$ssh = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no', "${User}@${ServerHost}")
$scp = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=no')

function Invoke-Ssh([string]$Cmd) {
    & ssh @ssh $Cmd
    if ($LASTEXITCODE -ne 0) { throw "SSH falhou: $Cmd" }
}

$secretJson = cmd /c "aws secretsmanager get-secret-value --secret-id paneldx-db-credentials --region us-east-2 --no-verify-ssl --query SecretString --output text 2>nul"
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel ler paneldx-db-credentials' }
$db = $secretJson | ConvertFrom-Json
$encPass = [uri]::EscapeDataString($db.password)
$dbUrl = "postgresql://$($db.username):${encPass}@$($db.host):$($db.port)/LeAction_SysF?sslmode=require"
$escapedUrl = $dbUrl.Replace("'", "'\''")

$remoteDir = '/tmp/paneldx-migrations'
Invoke-Ssh "rm -rf $remoteDir && mkdir -p $remoteDir"

$files = Get-ChildItem $MigrationsDir -Filter '*.sql' | Sort-Object Name
if ($Only) { $files = $files | Where-Object { $Only -contains $_.Name } }
if (-not $files) { Write-Host 'Nenhuma migration.'; exit 0 }

foreach ($f in $files) {
    & scp @scp $f.FullName "${User}@${ServerHost}:${remoteDir}/$($f.Name)"
    if ($LASTEXITCODE -ne 0) { throw "scp falhou: $($f.Name)" }
}

Write-Host "`n==> Migrations PanelDX via EC2 ($($files.Count) arquivo(s))" -ForegroundColor Cyan
foreach ($f in $files) {
    Write-Host "    -> $($f.Name)" -ForegroundColor Gray
    Invoke-Ssh "export DATABASE_URL='$escapedUrl' && psql `"`$DATABASE_URL`" -v ON_ERROR_STOP=1 -f $remoteDir/$($f.Name)"
}
Invoke-Ssh "rm -rf $remoteDir"
Write-Host "`n==> Migrations PanelDX aplicadas." -ForegroundColor Green
