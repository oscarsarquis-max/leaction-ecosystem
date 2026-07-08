# Sobe API (:6010) + Web (:6173) do Diario de Obra
$ErrorActionPreference = "Stop"
$appsRoot = $PSScriptRoot
$apiDir = Join-Path $appsRoot "diario-obra-api"
$webDir = Join-Path $appsRoot "diario-obra-web"

Write-Host "=== Diario de Obra - start local ===" -ForegroundColor Green

# API
$apiPython = Join-Path $apiDir ".venv\Scripts\python.exe"
if (-not (Test-Path $apiPython)) {
  Write-Host "Criando venv da API..." -ForegroundColor Yellow
  Set-Location $apiDir
  python -m venv .venv
  & .\.venv\Scripts\pip.exe install -r requirements.txt
}

Write-Host "Iniciando API na porta 6010..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$apiDir'; `$env:PORT='6010'; & '$apiPython' run.py"
)

Start-Sleep -Seconds 2

# Web
if (-not (Test-Path (Join-Path $webDir "node_modules"))) {
  Write-Host "Instalando dependencias do frontend..." -ForegroundColor Yellow
  Set-Location $webDir
  npm install
}

Write-Host "Iniciando Web na porta 6173..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$webDir'; npm run dev"
)

Write-Host ""
Write-Host "API:  http://localhost:6010/health" -ForegroundColor Green
Write-Host "Web:  http://localhost:6173" -ForegroundColor Green
Write-Host "Use start-diario-obra.ps1 sempre com API e Web juntos." -ForegroundColor Yellow
