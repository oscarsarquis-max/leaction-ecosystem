<#
.SYNOPSIS
  Registra nova revisao das task definitions e atualiza servicos ECS.

.PARAMETER Tag
  Tag ja publicada no ECR, ex.: v50.0.11

.EXAMPLE
  .\scripts\deploy\04-ecs-deploy.ps1 -Tag v50.0.11
  .\scripts\deploy\04-ecs-deploy.ps1 -Tag v50.0.11 -Only frontend
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Tag,

    [ValidateSet('backend', 'worker', 'frontend')]
    [string[]]$Only,

    [string]$Account,
    [string]$Region,
    [string]$Cluster,
    [switch]$VerifySsl
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_common.ps1')
if (-not $Account) { $Account = $script:DeployDefaults.Account }
if (-not $Region)  { $Region  = $script:DeployDefaults.Region }
if (-not $Cluster) { $Cluster = $script:DeployDefaults.Cluster }

$Registry = "$Account.dkr.ecr.$Region.amazonaws.com"
$Services = Get-DeployServices -Only $Only

if ($Services.Count -eq 0) {
    throw 'Nenhum servico selecionado.'
}

$null = Test-DeployPrerequisites -Account $Account -VerifySsl:$VerifySsl
Write-DeployOk "Cluster: $Cluster | Tag: $Tag | Servicos: $($Services.Name -join ', ')"

Update-DeployEcsServices -Tag $Tag -Registry $Registry -Region $Region `
    -Cluster $Cluster -Services $Services -VerifySsl:$VerifySsl

Show-DeployWaitCommands -Cluster $Cluster -Region $Region -Services $Services -VerifySsl:$VerifySsl
Write-Host "`n==> ECS deploy disparado." -ForegroundColor Cyan
