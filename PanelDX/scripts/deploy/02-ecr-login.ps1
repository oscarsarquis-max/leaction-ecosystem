<#
.SYNOPSIS
  Autentica o Docker no ECR da conta PanelDX.

.EXAMPLE
  .\scripts\deploy\02-ecr-login.ps1
#>
[CmdletBinding()]
param(
    [string]$Account,
    [string]$Region,
    [switch]$VerifySsl
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_common.ps1')
if (-not $Account) { $Account = $script:DeployDefaults.Account }
if (-not $Region)  { $Region  = $script:DeployDefaults.Region }

$Registry = "$Account.dkr.ecr.$Region.amazonaws.com"
$null = Test-DeployPrerequisites -Account $Account -VerifySsl:$VerifySsl
Connect-DeployEcr -Registry $Registry -Region $Region -VerifySsl:$VerifySsl
