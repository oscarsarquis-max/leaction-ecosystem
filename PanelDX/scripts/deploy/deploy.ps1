<#
.SYNOPSIS
  Orquestrador do deploy PanelDX (ECR + ECS).

  Executa em sequencia: preflight -> ecr-login -> build-push -> ecs-deploy
  Para etapas isoladas, use os scripts numerados 01 a 04.

.EXAMPLE
  .\scripts\deploy\deploy.ps1 -Tag v50.0.11
  .\scripts\deploy\deploy.ps1 -Tag v50.0.11 -Only backend,worker
  .\scripts\deploy\deploy.ps1 -Tag v50.0.11 -SkipBuild
  .\scripts\deploy\deploy.ps1 -Tag v50.0.11 -SkipDeploy
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

    [switch]$SkipBuild,
    [switch]$SkipDeploy,
    [switch]$VerifySsl
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir '_common.ps1')
if (-not $Account) { $Account = $script:DeployDefaults.Account }
if (-not $Region)  { $Region  = $script:DeployDefaults.Region }
if (-not $Cluster) { $Cluster = $script:DeployDefaults.Cluster }

$here = $ScriptDir

& (Join-Path $here '01-preflight.ps1') -Account $Account -VerifySsl:$VerifySsl

if (-not $SkipBuild) {
    & (Join-Path $here '02-ecr-login.ps1') -Account $Account -Region $Region -VerifySsl:$VerifySsl
    $buildArgs = @{ Tag = $Tag; Account = $Account; Region = $Region; SkipLogin = $true; VerifySsl = $VerifySsl }
    if ($Only) { $buildArgs.Only = $Only }
    & (Join-Path $here '03-build-push.ps1') @buildArgs
} else {
    Write-Host "`n[!]  SkipBuild: imagens nao foram construidas." -ForegroundColor Yellow
}

if (-not $SkipDeploy) {
    $ecsArgs = @{ Tag = $Tag; Account = $Account; Region = $Region; Cluster = $Cluster; VerifySsl = $VerifySsl }
    if ($Only) { $ecsArgs.Only = $Only }
    & (Join-Path $here '04-ecs-deploy.ps1') @ecsArgs
} else {
    Write-Host "`n[!]  SkipDeploy: ECS nao foi alterado." -ForegroundColor Yellow
}

Write-Host "`n==> Deploy PanelDX concluido." -ForegroundColor Cyan
