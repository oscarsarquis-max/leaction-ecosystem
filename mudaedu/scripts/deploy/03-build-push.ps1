<#
.SYNOPSIS
  Build das imagens Docker e push para o ECR (sem alterar o ECS).

.PARAMETER Tag
  Tag da imagem, ex.: v50.0.11

.PARAMETER Only
  Subconjunto: backend, worker, frontend

.EXAMPLE
  .\scripts\deploy\03-build-push.ps1 -Tag v50.0.11
  .\scripts\deploy\03-build-push.ps1 -Tag v50.0.11 -Only backend,worker
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Tag,

    [ValidateSet('backend', 'worker', 'frontend')]
    [string[]]$Only,

    [string]$Account,
    [string]$Region,
    [switch]$VerifySsl,
    [switch]$SkipLogin
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_common.ps1')
if (-not $Account) { $Account = $script:DeployDefaults.Account }
if (-not $Region)  { $Region  = $script:DeployDefaults.Region }

$RepoRoot = Get-DeployRepoRoot
$Registry = "$Account.dkr.ecr.$Region.amazonaws.com"
$Services = Get-DeployServices -Only $Only

if ($Services.Count -eq 0) {
    throw 'Nenhum servico selecionado. Use -Only backend,worker,frontend ou omita para todos.'
}

$null = Test-DeployPrerequisites -Account $Account -VerifySsl:$VerifySsl
if (-not $SkipLogin) {
    Connect-DeployEcr -Registry $Registry -Region $Region -VerifySsl:$VerifySsl
}

Write-DeployOk "Registry: $Registry | Tag: $Tag | Servicos: $($Services.Name -join ', ')"
Publish-DeployImages -Tag $Tag -Registry $Registry -Services $Services -RepoRoot $RepoRoot
Write-Host "`n==> Build/push concluido." -ForegroundColor Cyan
