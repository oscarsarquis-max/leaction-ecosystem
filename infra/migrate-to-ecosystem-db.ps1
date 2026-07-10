<#
.SYNOPSIS
  Copia bancos do PostgreSQL local (:5432 / PG18) para leaction_db Docker (:5433).

.DESCRIPTION
  Somente LEITURA na origem (pg_dump). Nao altera nem apaga nada no PG local.
  Dump gravado em arquivo dentro do Docker - nunca pipe pg_dump|psql no PowerShell
  (pipe no Windows corrompe acentos -> '??').

.EXAMPLE
  .\migrate-to-ecosystem-db.ps1
  .\migrate-to-ecosystem-db.ps1 -Database LeAction_SysF
#>
[CmdletBinding()]
param(
    [string[]]$Database,
    [switch]$SkipVerify
)

$ErrorActionPreference = 'Stop'

$SourceHost = 'host.docker.internal'
$SourcePort = '5432'
$SourceUser = 'postgres'
$SourcePass = 'Cmgv6190!@'
$TargetContainer = 'leaction_db'
$TargetUser = 'admin'
$PgImage = 'postgres:18'

$AllDatabases = @(
    'LeAction_SysF',
    'MAtivas',
    'chamelleon',
    'inove4us',
    'prodinx',
    'LASim'
)

$Databases = if ($Database) { $Database } else { $AllDatabases }

$VerifyQueries = @{
    'LeAction_SysF' = "SELECT count(*) FROM ctdi_quest WHERE desc_ques LIKE '%??%';"
    'chamelleon'    = "SELECT count(*) FROM framework_blocks WHERE name_bloc LIKE '%??%' OR desc_bloc LIKE '%??%';"
}

function Get-QuotedDbName([string]$Name) {
    if ($Name -cmatch '^[a-z_][a-z0-9_]*$') { return $Name }
    return '"' + $Name + '"'
}

function Invoke-TargetPsql([string]$Sql) {
    docker exec $TargetContainer psql -U $TargetUser -d postgres -v ON_ERROR_STOP=1 -c $Sql | Out-Null
}

function Reset-TargetDatabase([string]$DbName) {
    $quoted = Get-QuotedDbName $DbName
    for ($i = 0; $i -lt 5; $i++) {
        Invoke-TargetPsql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DbName' AND pid <> pg_backend_pid();"
        Start-Sleep -Seconds 1
        $active = docker exec $TargetContainer psql -U $TargetUser -d postgres -tAc `
            "SELECT count(*) FROM pg_stat_activity WHERE datname = '$DbName' AND pid <> pg_backend_pid();"
        if ([int]$active.Trim() -eq 0) { break }
    }
    Invoke-TargetPsql "DROP DATABASE IF EXISTS $quoted;"
    Invoke-TargetPsql "CREATE DATABASE $quoted;"
}

function Test-TargetDbEncoding([string]$DbName) {
    if (-not $VerifyQueries.ContainsKey($DbName)) { return $null }
    $sql = $VerifyQueries[$DbName]
    $bad = docker exec $TargetContainer psql -U $TargetUser -d $DbName -tAc $sql
    return [int]($bad.Trim())
}

function Test-LeactionDbRunning([string]$Name) {
    return (docker inspect -f '{{.State.Running}}' $Name 2>$null) -eq 'true'
}

if (-not (Test-LeactionDbRunning $TargetContainer)) {
    throw "Container '$TargetContainer' nao esta rodando. Suba: cd leaction-platform; docker compose up -d db"
}

$DumpDir = Join-Path $PSScriptRoot '.tmp-migrate'
New-Item -ItemType Directory -Force -Path $DumpDir | Out-Null

Write-Host "`n==> Migrando PG local :5432 -> leaction_db :5433" -ForegroundColor Cyan
Write-Host "    Origem: somente leitura (pg_dump). PG local permanece intacto." -ForegroundColor DarkGray

foreach ($db in $Databases) {
    Write-Host "`n    -> $db" -ForegroundColor Gray
    $safeName = $db -replace '[^a-zA-Z0-9_-]', '_'
    $dumpHostPath = Join-Path $DumpDir "$safeName.sql"
    $dumpContainerPath = "/tmp/migrate-$safeName.sql"

    Reset-TargetDatabase $db

    docker run --rm `
        -e "PGPASSWORD=$SourcePass" `
        --add-host=host.docker.internal:host-gateway `
        -v "${DumpDir}:/backup" `
        $PgImage `
        pg_dump -h $SourceHost -p $SourcePort -U $SourceUser -d $db --no-owner --no-acl --clean --if-exists `
        -f "/backup/$safeName.sql"

    if (-not (Test-Path $dumpHostPath) -or (Get-Item $dumpHostPath).Length -lt 1024) {
        throw "Dump vazio ou ausente para $db"
    }

    docker cp $dumpHostPath "${TargetContainer}:${dumpContainerPath}"
    docker exec $TargetContainer psql -U $TargetUser -d $db -v ON_ERROR_STOP=1 -q -f $dumpContainerPath
    docker exec $TargetContainer rm -f $dumpContainerPath
    Remove-Item -LiteralPath $dumpHostPath -Force -ErrorAction SilentlyContinue

    if (-not $SkipVerify) {
        $bad = Test-TargetDbEncoding $db
        if ($null -ne $bad) {
            if ($bad -gt 0) {
                throw "Encoding corrompido em $db ($bad registros com '??'). Abortado."
            }
            Write-Host "       encoding OK (0 corrompidos)" -ForegroundColor Green
        }
    }
}

Write-Host "`n==> Bancos no leaction_db:" -ForegroundColor Cyan
docker exec $TargetContainer psql -U $TargetUser -d postgres -t -c `
    "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datistemplate = false AND datname <> 'postgres' ORDER BY 1;"

Write-Host "`n==> Migracao concluida. PG local :5432 inalterado." -ForegroundColor Green
