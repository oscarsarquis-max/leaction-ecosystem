<#
.SYNOPSIS
  Túnel SSH para Postgres de produção do Chamelleon (pgAdmin / DBeaver).

.DESCRIPTION
  O Postgres do Chamelleon NÃO está no RDS PanelDX.
  - Seu túnel habitual (5434) -> RDS paneldx-database (PanelDX, Action Hub, etc.)
  - Este túnel (5435)       -> EC2 chamelleon.com.br (bancos chamelleon + diario-obra)

  Use os dois túneis em paralelo (duas janelas de terminal).

.EXAMPLE
  .\infra\aws\pgadmin-tunnel.ps1
  # pgAdmin: localhost:5435, DB chamelleon ou diario-obra, user chamelleon

.EXAMPLE
  .\infra\aws\pgadmin-tunnel.ps1 -ViaBastion
  # Mesmo destino, passando pelo bastion PanelDX (Jump Host)
#>
[CmdletBinding()]
param(
    [string]$ServerIp = '18.227.125.118',
    [string]$BastionHost = 'ec2-user@3.145.51.253',
    [string]$KeyFile = 'C:\Projetos\Chaves\paneldx-bastion-key.pem',
    [int]$LocalPort = 5435,
    [switch]$ViaBastion
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $KeyFile)) {
    throw "Chave SSH não encontrada: $KeyFile"
}

Write-Host "`n==> Túnel Postgres Chamelleon (complementar ao RDS :5434)" -ForegroundColor Cyan
Write-Host "    RDS PanelDX (seu tunel atual):  localhost:5434" -ForegroundColor DarkGray
Write-Host "    Chamelleon (este tunel):        localhost:$LocalPort" -ForegroundColor Gray
Write-Host "    Bancos:   chamelleon | diario-obra" -ForegroundColor Gray
Write-Host "    Usuário:  chamelleon" -ForegroundColor Gray
Write-Host "    Senha:    ssh ... ubuntu@$ServerIp `"sudo cat /var/log/chamelleon-bootstrap.log`"" -ForegroundColor Gray
Write-Host "`n    Mantenha esta janela aberta. Ctrl+C para encerrar.`n" -ForegroundColor Yellow

$sshCommon = @('-o', 'StrictHostKeyChecking=accept-new', '-i', $KeyFile, '-N', '-L', "${LocalPort}:127.0.0.1:5432")

if ($ViaBastion) {
    ssh @sshCommon '-J' $BastionHost "ubuntu@$ServerIp"
} else {
    ssh @sshCommon "ubuntu@$ServerIp"
}
