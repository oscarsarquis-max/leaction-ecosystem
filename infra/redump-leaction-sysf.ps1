<#
.SYNOPSIS
  Gera um dump limpo de LeAction_SysF em UTF-8 (custom format) e restaura no leaction-postgres.

.DESCRIPTION
  O dump em "G:\Meu Drive\...\bkbases\LeAction_SysF.sql" já veio com acentos
  substituídos por "??" (bytes 3f3f). Restaurar esse arquivo de novo NÃO corrige
  a tela. Este script:

  A) Faz pg_dump de uma fonte íntegra (RDS ou Postgres local) com client_encoding=UTF8
  B) Recria o banco local e restaura o dump novo
  C) Valida se ainda existem literais "??" em catálogos

.EXEMPLO — dump a partir do RDS (produção)
  $env:SRC_HOST = 'paneldx-database.czqyam2auctn.us-east-2.rds.amazonaws.com'
  $env:SRC_PORT = '5432'
  $env:SRC_DB   = 'LeAction_SysF'
  $env:SRC_USER = 'postgres'
  $env:SRC_PASS = '***'
  $env:SRC_SSL  = 'require'
  .\redump-leaction-sysf.ps1

.EXEMPLO — só restaurar um dump já gerado
  .\redump-leaction-sysf.ps1 -DumpFile "C:\Projetos\leaction-ecosystem\infra\dumps\LeAction_SysF_utf8.dump" -SkipDump
#>

[CmdletBinding()]
param(
    [string]$DumpFile = (Join-Path $PSScriptRoot "dumps\LeAction_SysF_utf8.dump"),
    [string]$TargetContainer = "leaction-postgres",
    [string]$TargetDb = "LeAction_SysF",
    [string]$TargetUser = "postgres",
    [string]$PgImage = "postgres:18",
    [switch]$SkipDump,
    [switch]$SkipRestore,
    [switch]$SkipValidate
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Msg) {
    Write-Host ""
    Write-Host "==> $Msg" -ForegroundColor Cyan
}

function Assert-Container([string]$Name) {
    $id = docker ps -q -f "name=^${Name}$"
    if (-not $id) { throw "Container '$Name' não está rodando." }
}

$SrcHost = $env:SRC_HOST
$SrcPort = if ($env:SRC_PORT) { $env:SRC_PORT } else { "5432" }
$SrcDb   = if ($env:SRC_DB) { $env:SRC_DB } else { "LeAction_SysF" }
$SrcUser = if ($env:SRC_USER) { $env:SRC_USER } else { "postgres" }
$SrcPass = $env:SRC_PASS
$SrcSsl  = if ($env:SRC_SSL) { $env:SRC_SSL } else { "prefer" }

$DumpDir = Split-Path -Parent $DumpFile
if (-not (Test-Path $DumpDir)) {
    New-Item -ItemType Directory -Force -Path $DumpDir | Out-Null
}

if (-not $SkipDump) {
    if (-not $SrcHost) {
        throw @"
Defina a fonte do dump via variáveis de ambiente:
  SRC_HOST  (ex: paneldx-database....rds.amazonaws.com ou host.docker.internal)
  SRC_PORT  (padrão 5432)
  SRC_DB    (padrão LeAction_SysF)
  SRC_USER
  SRC_PASS
  SRC_SSL   (require para RDS; prefer/disable para local)

Ou use -SkipDump se já tiver um .dump UTF-8 em -DumpFile.
"@
    }
    if (-not $SrcPass) { throw "SRC_PASS não definido." }

    Write-Step "Dump UTF-8 de ${SrcHost}:${SrcPort}/${SrcDb} -> $DumpFile"

    $dumpArgs = @(
        "run", "--rm",
        "-e", "PGPASSWORD=$SrcPass",
        "-e", "PGCLIENTENCODING=UTF8",
        "-v", "${DumpDir}:/out",
        "--add-host=host.docker.internal:host-gateway",
        $PgImage,
        "pg_dump",
        "-h", $SrcHost,
        "-p", $SrcPort,
        "-U", $SrcUser,
        "-d", $SrcDb,
        "-Fc",
        "--no-owner",
        "--no-acl",
        "--encoding=UTF8",
        "-f", "/out/$(Split-Path -Leaf $DumpFile)"
    )
    if ($SrcSsl -and $SrcSsl -ne "disable") {
        $dumpArgs = @(
            "run", "--rm",
            "-e", "PGPASSWORD=$SrcPass",
            "-e", "PGCLIENTENCODING=UTF8",
            "-e", "PGSSLMODE=$SrcSsl",
            "-v", "${DumpDir}:/out",
            "--add-host=host.docker.internal:host-gateway",
            $PgImage,
            "pg_dump",
            "-h", $SrcHost,
            "-p", $SrcPort,
            "-U", $SrcUser,
            "-d", $SrcDb,
            "-Fc",
            "--no-owner",
            "--no-acl",
            "--encoding=UTF8",
            "-f", "/out/$(Split-Path -Leaf $DumpFile)"
        )
    }

    & docker @dumpArgs
    if ($LASTEXITCODE -ne 0) { throw "pg_dump falhou (exit $LASTEXITCODE)." }

    $item = Get-Item $DumpFile
    Write-Host ("Dump OK: {0:N0} bytes" -f $item.Length) -ForegroundColor Green
}

if (-not $SkipRestore) {
    if (-not (Test-Path $DumpFile)) { throw "Dump não encontrado: $DumpFile" }
    Assert-Container $TargetContainer

    Write-Step "Recriando banco local $TargetDb no container $TargetContainer"
    docker exec $TargetContainer psql -U $TargetUser -d postgres -v ON_ERROR_STOP=1 -c `
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TargetDb' AND pid <> pg_backend_pid();" | Out-Null
    docker exec $TargetContainer psql -U $TargetUser -d postgres -v ON_ERROR_STOP=1 -c `
        "DROP DATABASE IF EXISTS `"$TargetDb`";" | Out-Null
    docker exec $TargetContainer psql -U $TargetUser -d postgres -v ON_ERROR_STOP=1 -c `
        "CREATE DATABASE `"$TargetDb`" ENCODING 'UTF8' TEMPLATE template0;" | Out-Null

    $leaf = Split-Path -Leaf $DumpFile
    Write-Step "Copiando dump para o container e restaurando (pg_restore)"
    docker cp $DumpFile "${TargetContainer}:/tmp/$leaf"
    docker exec $TargetContainer pg_restore -U $TargetUser -d $TargetDb --no-owner --no-privileges --exit-on-error "/tmp/$leaf"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "pg_restore retornou $LASTEXITCODE — revisando erros não fatais..." -ForegroundColor Yellow
    }
}

if (-not $SkipValidate) {
    Assert-Container $TargetContainer
    Write-Step "Validando encoding (não deve haver literais ?? em catálogos)"
    $sql = @"
SELECT 'leaf_dime' AS t, count(*) FILTER (WHERE name_dime ~ '\?\?') AS broken, count(*) AS total FROM leaf_dime
UNION ALL SELECT 'leaf_doma', count(*) FILTER (WHERE name_doma ~ '\?\?'), count(*) FROM leaf_doma
UNION ALL SELECT 'leaf_bloc', count(*) FILTER (WHERE name_bloc ~ '\?\?'), count(*) FROM leaf_bloc
UNION ALL SELECT 'ctdi_quest', count(*) FILTER (WHERE desc_ques ~ '\?\?'), count(*) FROM ctdi_quest
UNION ALL SELECT 'dx_planos', count(*) FILTER (WHERE nome ~ '\?\?'), count(*) FROM dx_planos
ORDER BY 1;
"@
    docker exec $TargetContainer psql -U $TargetUser -d $TargetDb -c $sql

    Write-Host ""
    Write-Host "Amostra leaf_dime:" -ForegroundColor DarkGray
    docker exec $TargetContainer psql -U $TargetUser -d $TargetDb -c "SELECT id_dime, name_dime FROM leaf_dime ORDER BY id_dime;"
}

Write-Host ""
Write-Host "Concluído." -ForegroundColor Green
Write-Host "Dump: $DumpFile"
Write-Host "App:  http://localhost:3000  |  API: http://localhost:5000"
