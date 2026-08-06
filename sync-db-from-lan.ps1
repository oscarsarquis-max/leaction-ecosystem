<#
.SYNOPSIS
  Atalho na raiz: sync LAN dos bancos de TODAS as aplicacoes do ecossistema.

.DESCRIPTION
  1) Bancos no leaction_db (hub, MAtivas, chamelleon, inove4us, inove4us_school,
     prodinx, LASim, diario-obra)
     via infra\sync-ecosystem-db-from-lan.ps1 (porta 5433)
  2) Banco Phanton (orquestrador) via phanton\database\sync-phanton-db-from-lan.ps1 (porta 5435)

  Rode na maquina DESTINO. Na ORIGEM, antes:
    .\infra\open-leaction-db-lan.ps1
    .\phanton\database\open-phanton-db-lan.ps1

.EXAMPLE
  cd C:\Projetos
  .\sync-db-from-lan.ps1 -SourceHost 192.168.0.41 -Force

.EXAMPLE
  # So leaction_db (sem Phanton)
  .\sync-db-from-lan.ps1 -SourceHost 192.168.0.41 -Force -SkipPhanton

.EXAMPLE
  .\sync-db-from-lan.ps1 -SourceHost 192.168.0.41 -CompareOnly
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$SourceHost,

    [int]$SourcePort = 5433,

    [string]$DbUser = 'admin',

    [string]$DbPassword = 'password123',

    [string]$Container = 'leaction_db',

    [string[]]$Database,

    [switch]$CompareOnly,

    [switch]$Force,

    [switch]$ForceAll,

    # Nao sincroniza o Postgres do Phanton (:5435)
    [switch]$SkipPhanton,

    [int]$PhantonPort = 5435,

    [string]$PhantonDbUser = 'postgres',

    [string]$PhantonDbPassword = 'password',

    [string]$PhantonDatabase = 'orquestrador',

    [string]$PhantonContainer = 'phanton_orquestrador_db'
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot

$eco = Join-Path $Root 'infra\sync-ecosystem-db-from-lan.ps1'
if (-not (Test-Path $eco)) {
    throw "Script nao encontrado: $eco"
}

Write-Host "`n############################################" -ForegroundColor Cyan
Write-Host " Sync DB - todas as aplicacoes (LAN)" -ForegroundColor Cyan
Write-Host "############################################`n" -ForegroundColor Cyan

& $eco `
    -SourceHost $SourceHost `
    -SourcePort $SourcePort `
    -DbUser $DbUser `
    -DbPassword $DbPassword `
    -Container $Container `
    -Database $Database `
    -CompareOnly:$CompareOnly `
    -Force:$Force `
    -ForceAll:$ForceAll

if ($SkipPhanton) {
    Write-Host "`nPhanton: pulado (-SkipPhanton).`n" -ForegroundColor DarkGray
    return
}

$phanton = Join-Path $Root 'phanton\database\sync-phanton-db-from-lan.ps1'
if (-not (Test-Path $phanton)) {
    Write-Host "AVISO: script Phanton nao encontrado ($phanton) - ignorando." -ForegroundColor Yellow
    return
}

Write-Host "`n############################################" -ForegroundColor Cyan
Write-Host " Sync Phanton (orquestrador :$PhantonPort)" -ForegroundColor Cyan
Write-Host "############################################`n" -ForegroundColor Cyan

if ($CompareOnly) {
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $tcp.BeginConnect($SourceHost, $PhantonPort, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(8000, $false)
        if ($ok -and $tcp.Connected) {
            $tcp.EndConnect($iar) | Out-Null
            Write-Host "Phanton origem ${SourceHost}:${PhantonPort} alcancavel (CompareOnly - sem restore)." -ForegroundColor Green
        } else {
            Write-Host "Phanton origem ${SourceHost}:${PhantonPort} inacessivel. Na origem: .\phanton\database\open-phanton-db-lan.ps1" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Phanton origem ${SourceHost}:${PhantonPort} inacessivel. Na origem: .\phanton\database\open-phanton-db-lan.ps1" -ForegroundColor Yellow
    } finally {
        $tcp.Close()
    }
    return
}

$phantonArgs = @{
    SourceHost      = $SourceHost
    SourcePort      = $PhantonPort
    DbUser          = $PhantonDbUser
    DbPassword      = $PhantonDbPassword
    Database        = $PhantonDatabase
    LocalContainer  = $PhantonContainer
}
if ($Force -or $ForceAll) {
    $phantonArgs['Force'] = $true
}

& $phanton @phantonArgs

Write-Host "`nSync completo (ecossistema + Phanton).`n" -ForegroundColor Green
