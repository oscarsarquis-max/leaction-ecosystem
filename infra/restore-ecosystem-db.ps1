<#
.SYNOPSIS
  Restaura dumps SQL de db-pack/dumps/ no container leaction_db (:5433).
.DESCRIPTION
  Use na máquina destino após git pull, docker compose up -d db e distribute-env.ps1.
#>
[CmdletBinding()]
param(
    [string]$PackRoot,
    [string]$Container = 'leaction_db',
    [string]$DbUser = 'admin',
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$MonorepoRoot = Split-Path $PSScriptRoot -Parent
if (-not $PackRoot) {
    $PackRoot = Join-Path $MonorepoRoot 'db-pack'
}
$DumpsDir = Join-Path $PackRoot 'dumps'
$ManifestPath = Join-Path $PackRoot 'manifest.json'

function Get-QuotedDbName([string]$Name) {
    if ($Name -cmatch '^[a-z_][a-z0-9_]*$') { return $Name }
    return '"' + $Name + '"'
}

function Test-LeactionDbRunning([string]$Name) {
    $state = docker inspect -f '{{.State.Running}}' $Name 2>$null
    return $state -eq 'true'
}

function Invoke-TargetPsql([string]$Sql) {
    docker exec $Container psql -U $DbUser -d postgres -v ON_ERROR_STOP=1 -c "$Sql" | Out-Null
}

if (-not (Test-Path $DumpsDir)) {
    throw "Pasta não encontrada: $DumpsDir`nCopie db-pack/ desta máquina ou rode backup-ecosystem-db.ps1 na origem."
}

$dumpFiles = Get-ChildItem $DumpsDir -Filter '*.sql' | Sort-Object Name
if ($dumpFiles.Count -eq 0) {
    throw "Nenhum .sql em $DumpsDir"
}

if (-not $DryRun -and -not (Test-LeactionDbRunning $Container)) {
    throw "Container '$Container' não está rodando. Suba com: cd leaction-platform; docker compose up -d db"
}

if ($ManifestPath -and (Test-Path $ManifestPath)) {
    $manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
    Write-Host "Manifest: $($manifest.created_at) | PG $($manifest.pg_version)" -ForegroundColor DarkGray
    $entries = @($manifest.databases)
} else {
    $entries = $dumpFiles | ForEach-Object {
        [pscustomobject]@{ name = $_.BaseName; file = "dumps/$($_.Name)" }
    }
}

Write-Host "`n==> Restaurar $($entries.Count) banco(s) em $Container" -ForegroundColor Cyan

if (-not $Force -and -not $DryRun) {
    $answer = Read-Host "Isso sobrescreve os bancos existentes. Continuar? [s/N]"
    if ($answer -notmatch '^[sS]') {
        Write-Host "Cancelado." -ForegroundColor Yellow
        exit 0
    }
}

foreach ($entry in $entries) {
    $db = $entry.name
    $rel = $entry.file -replace '^dumps/', ''
    $file = Join-Path $DumpsDir $rel
    if (-not (Test-Path $file)) {
        throw "Arquivo não encontrado: $file"
    }

    Write-Host "    -> $db ($rel)" -ForegroundColor Gray
    if ($DryRun) { continue }

    $quoted = Get-QuotedDbName $db
    Invoke-TargetPsql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db' AND pid <> pg_backend_pid();"
    Invoke-TargetPsql "DROP DATABASE IF EXISTS $quoted;"
    Invoke-TargetPsql "CREATE DATABASE $quoted;"

    Get-Content -LiteralPath $file.FullName -Raw -Encoding utf8 `
        | docker exec -i $Container psql -U $DbUser -d $db -v ON_ERROR_STOP=0 -q | Out-Null
}

if (-not $DryRun) {
    Write-Host "`n==> Bancos restaurados:" -ForegroundColor Cyan
    docker exec $Container psql -U $DbUser -d postgres -t -c `
        "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datistemplate = false AND datname <> 'postgres' ORDER BY 1;"
}

Write-Host "`n==> Restauração concluída." -ForegroundColor Green
