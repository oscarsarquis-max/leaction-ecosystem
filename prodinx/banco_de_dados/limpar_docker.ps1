#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "=== Prodinx - Limpeza da base Docker ===" -ForegroundColor Cyan
Write-Host "O servidor canonico e o PostgreSQL LOCAL na porta 5432." -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Parar o contentor e APAGAR o volume prodinx_pgdata? (s/N)"
if ($confirm -notin @("s", "S", "sim", "SIM")) {
    Write-Host "Operacao cancelada." -ForegroundColor Yellow
    exit 0
}

Write-Host ">> A parar contentor prodinx-postgres..." -ForegroundColor Cyan
docker compose down -v 2>$null
if ($LASTEXITCODE -ne 0) {
    docker stop prodinx-postgres 2>$null
    docker rm prodinx-postgres 2>$null
    docker volume rm banco_de_dados_prodinx_pgdata 2>$null
}

Write-Host ">> Volume Docker removido." -ForegroundColor Green
Write-Host ""
Write-Host "Base ativa: PostgreSQL local (localhost:5432 / prodinx)" -ForegroundColor Green
Write-Host "Para recriar o Docker no futuro (opcional): .\manter.ps1" -ForegroundColor Gray
