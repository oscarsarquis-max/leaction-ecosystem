#Requires -Version 5.1
# Wrapper fino. Credenciais só do processo ou do container local. Não lê .env.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("reference", "demo", "smoke", "inspect", "verify", "coverage", "dry-run")]
    [string]$Command,
    [string]$DatabaseUrl = $env:PANNE_SEED_DATABASE_URL,
    [string]$AnchorDate = "2026-08-24",
    [string]$Scenario = "application",
    [switch]$Rebuild
)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Backend = Join-Path $Root "backend"
$Py = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
if (-not $DatabaseUrl) {
    throw "Defina PANNE_SEED_DATABASE_URL apontando exatamente para um banco *_demo ou *_smoke."
}
if ($DatabaseUrl -match "/panne(\?|$)") {
    throw "Recusado: banco lógico panne."
}
if ($env:PANNE_ENV -eq "production") {
    throw "Recusado: ambiente production."
}
Write-Host "Alvo informado no processo. Comando=$Command"
$args = @("-m", "app.seed", $Command, "--database-url", $DatabaseUrl, "--anchor-date", $AnchorDate, "--scenario", $Scenario)
if ($Rebuild) { $args += "--rebuild" }
Push-Location $Backend
try {
    & $Py @args
    if ($LASTEXITCODE -ne 0) { throw "seed falhou com código $LASTEXITCODE" }
} finally {
    Pop-Location
}
