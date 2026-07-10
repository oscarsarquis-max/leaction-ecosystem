#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Expõe leaction_db (Docker :5433) na LAN para pg_dump de outras estações.

.EXAMPLE
  cd C:\Projetos\infra
  .\open-leaction-db-lan.ps1
#>
[CmdletBinding()]
param(
    [int]$Port = 5433,
    [string]$RuleName = 'LeAction DB LAN'
)

$ErrorActionPreference = 'Stop'
$ComposeDir = 'C:\Projetos\leaction-platform'

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

Write-Host "`nBancos disponíveis:" -ForegroundColor Cyan
docker exec leaction_db psql -U admin -d postgres -c "\l"

$lan = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -match '^192\.168\.' } |
    Select-Object -ExpandProperty IPAddress

Write-Host "`n==> Resumo" -ForegroundColor Cyan
Write-Host "IP LAN (192.168.*): $($lan -join ', ')"
Write-Host "Porta: $Port | User: admin | Senha: password123 (compose)"
Write-Host "Teste na outra máquina:"
foreach ($ip in $lan) {
    Write-Host "  Test-NetConnection -ComputerName $ip -Port $Port"
}
