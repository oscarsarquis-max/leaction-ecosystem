#Requires -Version 5.1
# Encerra API e Vite iniciados por start-demo.ps1.
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$PidFile = Join-Path $Root ".tmp-demo\pids.json"
if (-not (Test-Path $PidFile)) {
    Write-Host "Nenhum pid de demo encontrado."
    exit 0
}
$data = Get-Content $PidFile -Raw | ConvertFrom-Json
foreach ($id in @($data.api, $data.fe)) {
    if ($id) {
        try { Stop-Process -Id ([int]$id) -Force -ErrorAction Stop } catch { }
    }
}
Remove-Item $PidFile -Force
Write-Host "Demo encerrada."
