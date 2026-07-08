<#
.SYNOPSIS
  Posiciona lead demo por estagio — telecom ou construcao civil (engenharia).

.EXAMPLE
  .\seed-dev-client.ps1 -Stage 3 -Sector telecom
  .\seed-dev-client.ps1 -Stage 1 -Sector construcao
#>
[CmdletBinding()]
param(
    [ValidateSet(1, 2, 3)]
    [int]$Stage = 1,
    [ValidateSet("telecom", "construcao")]
    [string]$Sector = "telecom"
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$Python = Join-Path $BackendDir ".venv\Scripts\python.exe"
$Script = Join-Path $BackendDir "scripts\seed_dev_client.py"

if (-not (Test-Path $Python)) {
    throw "Venv nao encontrado em backend\.venv. Rode .\start-local.ps1 primeiro."
}

Write-Host "`n==> Seed Chamelleon - estagio $Stage ($Sector)" -ForegroundColor Cyan

& $Python $Script $Stage --sector $Sector
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nCredenciais:" -ForegroundColor Green
if ($Sector -eq "telecom") {
    Write-Host "  Lead: sistema@paneldx.com.br (codigo LA-PANEL1)"
} else {
    Write-Host "  Lead: engenharia@paneldx.com.br (codigo LA-ENG1)"
}
