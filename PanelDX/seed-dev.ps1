<#
=====================================================================
 PanelDX - Seed de demonstração (somente banco)
=====================================================================
 NÃO abre/reinicia Flask/Node. Só reseta os usuários demo no Postgres.

 Uso:
   .\seed-dev.ps1 1
   .\seed-dev.ps1 4
   .\seed-dev.ps1 4 -LeadOnly
   .\seed-dev.ps1 1 -FullReset   # local apenas
=====================================================================
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet(1, 2, 3, 4)]
    [int]$Stage,

    [switch]$LeadOnly,
    [switch]$FullReset
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$SeedScript = Join-Path $Root "seed_dev_client.py"
$VenvPython = Join-Path $Root "venv_action\Scripts\python.exe"

if (-not (Test-Path $SeedScript)) {
    throw "seed_dev_client.py não encontrado em $Root"
}

$python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

$argsList = @($SeedScript, "$Stage")
if ($LeadOnly) { $argsList += "--lead-only" }
if ($FullReset) { $argsList += "--full-reset" }

Write-Host ""
Write-Host ">> PanelDX seed (estágio $Stage) — sem abrir janelas de serviço" -ForegroundColor Cyan
Write-Host "   $python $($argsList -join ' ')" -ForegroundColor DarkGray
Write-Host ""

& $python @argsList
exit $LASTEXITCODE
