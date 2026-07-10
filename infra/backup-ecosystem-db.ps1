<#
.SYNOPSIS
  Exporta schema + dados de todos os bancos do container leaction_db (:5433).
.DESCRIPTION
  Gera dumps SQL em db-pack/dumps/ para transferir para outra estação (USB/zip).
  Não versionar db-pack/ — contém dados reais de desenvolvimento.
#>
[CmdletBinding()]
param(
    [string]$OutputRoot,
    [string]$Container = 'leaction_db',
    [string]$DbUser = 'admin',
    [int]$HostPort = 5433
)

$ErrorActionPreference = 'Stop'

$MonorepoRoot = Split-Path $PSScriptRoot -Parent
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $MonorepoRoot 'db-pack'
}
$DumpsDir = Join-Path $OutputRoot 'dumps'

$Databases = @(
    'leaction_hub',
    'LeAction_SysF',
    'MAtivas',
    'chamelleon',
    'inove4us',
    'prodinx',
    'LASim',
    'diario-obra'
)

function Get-QuotedDbName([string]$Name) {
    if ($Name -cmatch '^[a-z_][a-z0-9_]*$') { return $Name }
    return '"' + $Name + '"'
}

function Test-LeactionDbRunning([string]$Name) {
    $state = docker inspect -f '{{.State.Running}}' $Name 2>$null
    return $state -eq 'true'
}

if (-not (Test-LeactionDbRunning $Container)) {
    throw "Container '$Container' não está rodando. Suba com: cd leaction-platform; docker compose up -d db"
}

New-Item -ItemType Directory -Force -Path $DumpsDir | Out-Null

$pgVersion = docker exec $Container psql -U $DbUser -d postgres -tAc "SHOW server_version;" | ForEach-Object { $_.Trim() }
$timestamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'

Write-Host "`n==> Backup leaction_db (PG $pgVersion) -> $DumpsDir" -ForegroundColor Cyan

$manifest = [ordered]@{
    created_at    = (Get-Date -Format 'o')
    pg_version    = $pgVersion
    container     = $Container
    host_port     = $HostPort
    databases     = @()
}

foreach ($db in $Databases) {
  $safeName = $db -replace '[^a-zA-Z0-9_-]', '_'
  $outFile = Join-Path $DumpsDir "$safeName.sql"
  Write-Host "    -> $db" -ForegroundColor Gray

  docker exec $Container pg_dump -U $DbUser -d $db --no-owner --no-acl --clean --if-exists `
    | Set-Content -Path $outFile -Encoding utf8

  $sizeKb = [math]::Round((Get-Item $outFile).Length / 1KB, 1)
  $manifest.databases += [ordered]@{
    name     = $db
    file     = "dumps/$safeName.sql"
    size_kb  = $sizeKb
  }
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $OutputRoot 'manifest.json') -Encoding utf8

Write-Host "`n==> Arquivos gerados:" -ForegroundColor Cyan
Get-ChildItem $DumpsDir -Filter '*.sql' | ForEach-Object {
    Write-Host ("    {0,-20} {1,8:N1} KB" -f $_.Name, ($_.Length / 1KB))
}

Write-Host "`n==> Copie a pasta db-pack/ junto com env-pack/ para a outra estação." -ForegroundColor Green
Write-Host "    Restaurar: .\infra\restore-ecosystem-db.ps1 -Force`n" -ForegroundColor Green
