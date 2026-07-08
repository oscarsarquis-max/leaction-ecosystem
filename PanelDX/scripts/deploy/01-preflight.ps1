<#
.SYNOPSIS
  Checagens antes do deploy PanelDX (docker, aws, conta).

.EXAMPLE
  .\scripts\deploy\01-preflight.ps1
  .\scripts\deploy\01-preflight.ps1 -Account 253137917703 -VerifySsl
#>
[CmdletBinding()]
param(
    [string]$Account,
    [switch]$VerifySsl
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_common.ps1')
if (-not $Account) { $Account = $script:DeployDefaults.Account }

$null = Test-DeployPrerequisites -Account $Account -VerifySsl:$VerifySsl
Write-DeployOk 'Preflight concluido — pronto para build/deploy.'
