#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Expõe leaction_db (Docker :5433) na LAN para pg_dump de outras estações.

.DESCRIPTION
  Bancos típicos neste container: leaction_hub, MAtivas, chamelleon, inove4us,
  inove4us_school, prodinx, LASim, diario-obra.

  Para o Phanton (porta 5435, container separado), rode também:
    ..\phanton\database\open-phanton-db-lan.ps1

.EXAMPLE
  cd C:\Projetos\leaction-ecosystem\infra
  .\open-leaction-db-lan.ps1
#>
[CmdletBinding()]
param(
    [int]$Port = 5433,
    [string]$RuleName = 'LeAction DB LAN',
    [string]$ComposeDir = ''
)

$ErrorActionPreference = 'Stop'
if (-not $ComposeDir) {
    $ComposeDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'leaction-platform'
}

Write-Host "`n==> Subindo leaction_db..." -ForegroundColor Cyan
Push-Location $ComposeDir
docker compose up -d db
Pop-Location

$status = docker ps --filter name=leaction_db --format "{{.Status}}"
$ports = docker port leaction_db 5432 2>$null
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

Write-Host "`nBancos disponíveis (leaction_db):" -ForegroundColor Cyan
docker exec leaction_db psql -U admin -d postgres -c "\l"

$lan = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -match '^192\.168\.' } |
    Select-Object -ExpandProperty IPAddress

Write-Host "`n==> Resumo" -ForegroundColor Cyan
Write-Host "IP LAN (192.168.*): $($lan -join ', ')"
Write-Host "Porta: $Port | User: admin | Senha: password123 (compose)"
Write-Host "Na outra máquina (destino), puxar TODAS as apps:"
foreach ($ip in $lan) {
    Write-Host "  .\sync-db-from-lan.ps1 -SourceHost $ip -Force"
}
Write-Host "Phanton (opcional, se ainda não liberou):"
Write-Host "  ..\phanton\database\open-phanton-db-lan.ps1"
