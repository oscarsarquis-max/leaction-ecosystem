#Requires -Version 5.1
<#
.SYNOPSIS
  Aplica o seed oficial do inovador no database inove4us (Docker leaction_db).
  Não toca LeAction_SysF / PanelDX.
#>
param(
  [string]$Container = "leaction_db",
  [string]$DbName = "inove4us",
  [string]$DbUser = "admin"
)

$ErrorActionPreference = "Stop"
$SqlPath = Join-Path $PSScriptRoot "seed-inovador.sql"
if (-not (Test-Path $SqlPath)) { throw "Arquivo nao encontrado: $SqlPath" }

Write-Host "==> Reset inovador@inove4us.com.br em $DbName ..."
Write-Host "    (creditos=10, limpa desafios/agenda)"
Get-Content -Path $SqlPath -Raw -Encoding utf8 |
  docker exec -i $Container psql -U $DbUser -d $DbName -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw "Falha ao aplicar seed" }

Write-Host "==> OK"
Write-Host "    email   : inovador@inove4us.com.br"
Write-Host "    codigo  : LA-INOVE1"
Write-Host "    creditos: 10 (freemium)"
