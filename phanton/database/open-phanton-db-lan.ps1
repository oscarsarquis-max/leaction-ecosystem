#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Na ORIGEM (máquina com a base phanton): sobe o Postgres e libera TCP 5435 na LAN.

.EXAMPLE
  cd C:\Projetos\leaction-ecosystem\phanton\database
  .\open-phanton-db-lan.ps1
#>
[CmdletBinding()]
param(
    [int]$Port = 5435,
    [string]$RuleName = 'Phanton DB LAN'
)

$ErrorActionPreference = 'Stop'
$ComposeDir = $PSScriptRoot

Write-Host "`n==> Subindo phanton_orquestrador_db..." -ForegroundColor Cyan
Push-Location $ComposeDir
docker compose up -d
Pop-Location

$status = docker ps --filter name=phanton_orquestrador_db --format "{{.Status}}"
$ports = docker port phanton_orquestrador_db 5432 2>$null
Write-Host "Container: $status" -ForegroundColor Green
Write-Host "Port map:  $ports"

$existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Regra firewall '$RuleName' já existe — atualizando..." -ForegroundColor Yellow
    Set-NetFirewallRule -DisplayName $RuleName -Enabled True -Profile Private, Domain
} else {
    New-NetFirewallRule `
        -DisplayName $RuleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $Port `
        -Profile Private, Domain | Out-Null
    Write-Host "Regra firewall '$RuleName' criada (TCP $Port, Private+Domain)." -ForegroundColor Green
}

$lan = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -match '^192\.168\.' } |
    Select-Object -ExpandProperty IPAddress

Write-Host "`n==> Resumo" -ForegroundColor Cyan
Write-Host "IP LAN: $($lan -join ', ')"
Write-Host "Porta: $Port | User: postgres | Senha: password | DB: orquestrador"
Write-Host "Na outra máquina (destino):"
Write-Host "  .\phanton\database\sync-phanton-db-from-lan.ps1 -SourceHost <IP-desta-maquina> -Force"
