<#
.SYNOPSIS
  Sobe Postgres (compose) + dicas para API, mocks e frontend.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== Postgres =="
docker compose up -d

Write-Host ""
Write-Host "Em terminais separados:"
Write-Host "  cd $root\services\mock-sistema-cadastro; npm start"
Write-Host "  cd $root\services\mock-sistema-credito; npm start"
Write-Host "  cd $root\backend; mvn spring-boot:run"
Write-Host "  cd $root\frontend; npm run dev"
Write-Host ""
Write-Host "Painel: http://127.0.0.1:5180"
Write-Host "API:    http://127.0.0.1:8080/swagger-ui.html"
