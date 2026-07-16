<#
.SYNOPSIS
  Atalho na raiz do workspace para sync LAN dos bancos Docker.
.DESCRIPTION
  Encaminha para infra\sync-ecosystem-db-from-lan.ps1 — rode na máquina DESTINO.

.EXAMPLE
  cd C:\Projetos
  .\sync-db-from-lan.ps1 -SourceHost 192.168.0.50 -CompareOnly

.EXAMPLE
  .\sync-db-from-lan.ps1 -SourceHost 192.168.0.50 -Force
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
    [switch]$ForceAll
)

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'infra\sync-ecosystem-db-from-lan.ps1'
if (-not (Test-Path $script)) {
    throw "Script não encontrado: $script"
}

& $script `
    -SourceHost $SourceHost `
    -SourcePort $SourcePort `
    -DbUser $DbUser `
    -DbPassword $DbPassword `
    -Container $Container `
    -Database $Database `
    -CompareOnly:$CompareOnly `
    -Force:$Force `
    -ForceAll:$ForceAll
