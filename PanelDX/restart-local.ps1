<#
=====================================================================
 PanelDX - Restart local (libera portas + start-local)
=====================================================================
 Uso:
   .\restart-local.ps1
   .\restart-local.ps1 -Only frontend
=====================================================================
#>

[CmdletBinding()]
param(
    [ValidateSet("backend", "frontend")]
    [string[]]$Only,

    [switch]$OpenBrowser,
    [int]$FlaskPort = 5002,
    [int]$NodePort = 3000
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$StartScript = Join-Path $Root "start-local.ps1"

$argsList = @()
if ($Only) { $argsList += @("-Only"); $argsList += $Only }
if ($OpenBrowser) { $argsList += "-OpenBrowser" }
$argsList += @("-FlaskPort", "$FlaskPort", "-NodePort", "$NodePort")

# start-local já mata portas/janelas por padrão
& $StartScript @argsList
exit $LASTEXITCODE
