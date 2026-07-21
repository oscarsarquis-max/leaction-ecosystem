#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-Port($Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return [bool]$conn
}

Write-Host "=== Prodinx - Arranque ===" -ForegroundColor Cyan

if (-not (Test-Port 5432)) {
    Write-Host "AVISO: PostgreSQL local (5432) nao detectado." -ForegroundColor Yellow
}

if (Test-Port 5000) {
    Write-Host "Flask/watcher ja ativo na porta 5000." -ForegroundColor Green
} else {
    Write-Host "A iniciar Flask + watcher JSON (porta 5000)..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\servicos'; python app.py"
    Start-Sleep -Seconds 3
}

if (Test-Port 3002) {
    Write-Host "Backend ja ativo na porta 3002." -ForegroundColor Green
} else {
    Write-Host "A iniciar backend (porta 3002)..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\backend'; npm start"
    Start-Sleep -Seconds 2
}

if (Test-Port 5176) {
    Write-Host "Frontend ja ativo na porta 5176." -ForegroundColor Green
} else {
    Write-Host "A iniciar frontend (porta 5176)..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\frontend'; npm run dev"
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "Pasta quente de JSON (copie ficheiros .json para aqui):" -ForegroundColor Green
Write-Host "  $Root\jsonfiles" -ForegroundColor White
Write-Host ""
Write-Host "Abra no browser externo (Chrome/Edge):" -ForegroundColor Green
Write-Host "  http://localhost:5176" -ForegroundColor White
Write-Host "  http://127.0.0.1:5176" -ForegroundColor White
Write-Host ""
Write-Host "API backend:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:3002/api/dashboard/metricas" -ForegroundColor White
Write-Host ""
Write-Host "Flask ingestao (watcher ativo se porta 5000 estiver UP):" -ForegroundColor Green
Write-Host "  http://127.0.0.1:5000/health" -ForegroundColor White

$AppUrl = "http://localhost:5176/"
Write-Host ""
Write-Host "A abrir browser externo: $AppUrl" -ForegroundColor Cyan

$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$edgeArm = "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe"
$chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
$chromeX86 = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"

if (Test-Path $edge) {
    Start-Process -FilePath $edge -ArgumentList $AppUrl
} elseif (Test-Path $edgeArm) {
    Start-Process -FilePath $edgeArm -ArgumentList $AppUrl
} elseif (Test-Path $chrome) {
    Start-Process -FilePath $chrome -ArgumentList $AppUrl
} elseif (Test-Path $chromeX86) {
    Start-Process -FilePath $chromeX86 -ArgumentList $AppUrl
} else {
    Start-Process $AppUrl
}
