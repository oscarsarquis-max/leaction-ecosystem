<#
.SYNOPSIS
  No DESTINO: pg_dump da base phanton (orquestrador) na outra estação e restaura local.

.EXAMPLE
  # Nesta máquina (.41), puxar do DESKTOP-BA2U3G4 (.46):
  .\phanton\database\sync-phanton-db-from-lan.ps1 -SourceHost 192.168.0.46 -Force

.NOTES
  Pré-requisito na ORIGEM:
    cd ...\phanton\database
    .\open-phanton-db-lan.ps1   # libera TCP 5435
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceHost,

    [int]$SourcePort = 5435,

    [string]$DbUser = 'postgres',

    [string]$DbPassword = 'password',

    [string]$Database = 'orquestrador',

    [string]$LocalContainer = 'phanton_orquestrador_db',

    [string]$PgImage = 'postgres:15',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ComposeDir = $PSScriptRoot
$WorkDir = Join-Path $ComposeDir '_lan-sync'
$DumpFile = Join-Path $WorkDir 'orquestrador.dump'

Write-Host "`n==> Sync phanton DB ($SourceHost:$SourcePort/$Database -> local)" -ForegroundColor Cyan

# Connectivity
$tnc = Test-NetConnection -ComputerName $SourceHost -Port $SourcePort -WarningAction SilentlyContinue
if (-not $tnc.TcpTestSucceeded) {
    throw "Porta $SourcePort fechada em $SourceHost. Na ORIGEM rode: .\open-phanton-db-lan.ps1"
}

New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

Write-Host "==> Dump remoto..." -ForegroundColor Cyan
docker run --rm `
    -e PGPASSWORD=$DbPassword `
    -v "${WorkDir}:/out" `
    $PgImage `
    pg_dump -h $SourceHost -p $SourcePort -U $DbUser -d $Database `
    --format=custom --no-owner --no-acl -f /out/orquestrador.dump
if ($LASTEXITCODE -ne 0) { throw 'pg_dump remoto falhou' }

$bytes = (Get-Item $DumpFile).Length
Write-Host "Dump OK ($bytes bytes)" -ForegroundColor Green

if (-not $Force) {
    $ans = Read-Host "Restaurar em $LocalContainer (DROP schema public)? [s/N]"
    if ($ans -notmatch '^[sS]') { Write-Host 'Cancelado.'; return }
}

Write-Host "==> Garantindo container local..." -ForegroundColor Cyan
Push-Location $ComposeDir
docker compose up -d
Pop-Location

$deadline = (Get-Date).AddSeconds(60)
do {
    $ready = docker exec $LocalContainer pg_isready -U $DbUser -d $Database 2>$null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)
if ($LASTEXITCODE -ne 0) { throw "Container local $LocalContainer nao ficou pronto" }

Write-Host "==> Restaurando..." -ForegroundColor Cyan
docker exec $LocalContainer psql -U $DbUser -d $Database -v ON_ERROR_STOP=1 -c `
    "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres; GRANT ALL ON SCHEMA public TO public;"
docker run --rm `
    -e PGPASSWORD=$DbPassword `
    --network container:$LocalContainer `
    -v "${WorkDir}:/out" `
    $PgImage `
    pg_restore -h 127.0.0.1 -p 5432 -U $DbUser -d $Database --no-owner --no-acl --clean --if-exists /out/orquestrador.dump
# pg_restore pode retornar warnings; checa tabelas
docker exec $LocalContainer psql -U $DbUser -d $Database -c `
    "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;"

Write-Host "`n==> Sync phanton concluído." -ForegroundColor Green
Write-Host "Dump em: $DumpFile"
