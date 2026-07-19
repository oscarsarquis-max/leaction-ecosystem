<#
=====================================================================
 PanelDX — atalho para scripts/deploy/deploy.ps1 (AWS ECS)
=====================================================================
 Mantido por compatibilidade. A logica foi dividida em scripts em
 scripts/deploy/ (preflight, ecr-login, build-push, ecs-deploy, migrations).

 EXEMPLOS
   ./deploy.ps1 -Tag v50.0.11
   ./deploy.ps1 -Tag v50.0.11 -Only backend,worker
   ./deploy.ps1 -Tag v50.0.11 -SkipBuild
   ./deploy.ps1 -Tag v50.0.11 -SkipDeploy

 ETAPAS ISOLADAS
   ./scripts/deploy/03-build-push.ps1 -Tag v50.0.11
   ./scripts/deploy/04-ecs-deploy.ps1 -Tag v50.0.11
   ./scripts/deploy/05-run-migrations.ps1
=====================================================================
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
$forward = @{
    Tag        = $Tag
    SkipBuild  = $SkipBuild
    SkipDeploy = $SkipDeploy
    VerifySsl  = $VerifySsl
}
if ($Only)    { $forward.Only    = $Only }
if ($Account) { $forward.Account = $Account }
if ($Region)  { $forward.Region  = $Region }
if ($Cluster) { $forward.Cluster = $Cluster }

& (Join-Path $PSScriptRoot 'scripts/deploy/deploy.ps1') @forward
