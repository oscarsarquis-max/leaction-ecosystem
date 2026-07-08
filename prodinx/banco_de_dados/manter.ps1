#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ">> A subir PostgreSQL (Docker)..." -ForegroundColor Cyan
docker compose up -d

Write-Host ">> A aguardar disponibilidade da base..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    docker exec prodinx-postgres pg_isready -U postgres -d prodinx | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    throw "PostgreSQL nao ficou disponivel a tempo."
}

Write-Host ">> A aplicar schema e migracoes..." -ForegroundColor Cyan
Get-Content "$Root\schema.sql" | docker exec -i prodinx-postgres psql -U postgres -d prodinx -v ON_ERROR_STOP=1
Get-Content "$Root\migrations\001_indicadores_temporal.sql" | docker exec -i prodinx-postgres psql -U postgres -d prodinx -v ON_ERROR_STOP=1

Write-Host ">> Estado da tabela indicadores:" -ForegroundColor Green
docker exec prodinx-postgres psql -U postgres -d prodinx -c "\d indicadores"

Write-Host ">> Base prodinx pronta em localhost:5435" -ForegroundColor Green
