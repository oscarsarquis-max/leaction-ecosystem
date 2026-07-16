<#
.SYNOPSIS
  Na máquina DESTINO: compara e atualiza os bancos Docker (leaction_db) a partir de outra
  estação na mesma rede.

.DESCRIPTION
  Rode na raiz do workspace (ou em infra/) na máquina que precisa receber os dados.

  Pré-requisito na ORIGEM (máquina com a base “boa”):
    cd C:\Projetos\infra
    .\open-leaction-db-lan.ps1   # libera TCP 5433 na LAN

  Fluxo:
    1) Testa conectividade com a origem
    2) Compara fingerprint (tamanho + tabelas + linhas estimadas) de cada banco
    3) Faz dump remoto só dos bancos diferentes (ou todos com -ForceAll)
    4) Restaura no leaction_db local (DROP/CREATE + psql)

  Não usa pipe PowerShell nos dumps (evita corrupção UTF-8).

.EXAMPLE
  cd C:\Projetos
  .\infra\sync-ecosystem-db-from-lan.ps1 -SourceHost 192.168.0.50 -CompareOnly

.EXAMPLE
  cd C:\Projetos
  .\infra\sync-ecosystem-db-from-lan.ps1 -SourceHost 192.168.0.50 -Force

.EXAMPLE
  .\infra\sync-ecosystem-db-from-lan.ps1 -SourceHost 192.168.0.50 -Database inove4us -Force
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceHost,

    [int]$SourcePort = 5433,

    [string]$DbUser = 'admin',

    [string]$DbPassword = 'password123',

    [string]$Container = 'leaction_db',

    [string]$PgImage = 'postgres:18',

    # Um ou mais bancos; se omitido, sincroniza o conjunto padrão do ecossistema
    [string[]]$Database,

    [string]$WorkDir,

    # Só imprime diferenças — não altera nada
    [switch]$CompareOnly,

    # Não pergunta confirmação
    [switch]$Force,

    # Atualiza todos os bancos listados, mesmo sem diferença detectada
    [switch]$ForceAll
)

$ErrorActionPreference = 'Stop'

$MonorepoRoot = Split-Path $PSScriptRoot -Parent
if (-not $WorkDir) {
    $WorkDir = Join-Path $MonorepoRoot 'db-pack\_lan-sync'
}
$DumpsDir = Join-Path $WorkDir 'dumps'

$DefaultDatabases = @(
    'leaction_hub',
    'LeAction_SysF',
    'MAtivas',
    'chamelleon',
    'inove4us',
    'prodinx',
    'LASim',
    'diario-obra'
)

$Databases = if ($Database -and $Database.Count -gt 0) { @($Database) } else { $DefaultDatabases }

function Get-QuotedDbName([string]$Name) {
    if ($Name -cmatch '^[a-z_][a-z0-9_]*$') { return $Name }
    return '"' + $Name + '"'
}

function Test-LeactionDbRunning([string]$Name) {
    $state = docker inspect -f '{{.State.Running}}' $Name 2>$null
    return $state -eq 'true'
}

function Invoke-RemotePsql {
    param(
        [string]$DatabaseName,
        [string]$Sql,
        [switch]$Quiet
    )
    $args = @(
        'run', '--rm',
        '-e', "PGPASSWORD=$DbPassword",
        $PgImage,
        'psql',
        '-h', $SourceHost,
        '-p', "$SourcePort",
        '-U', $DbUser,
        '-d', $DatabaseName,
        '-v', 'ON_ERROR_STOP=1',
        '-tAc', $Sql
    )
    $out = & docker @args 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha psql remoto ($DatabaseName): $out"
    }
    if (-not $Quiet) { return ($out | Out-String).Trim() }
}

function Invoke-LocalPsql {
    param(
        [string]$DatabaseName,
        [string]$Sql
    )
    $out = docker exec -e "PGPASSWORD=$DbPassword" $Container `
        psql -U $DbUser -d $DatabaseName -v ON_ERROR_STOP=1 -tAc $Sql 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha psql local ($DatabaseName): $out"
    }
    return ($out | Out-String).Trim()
}

function Get-DbFingerprintSql {
    # Fingerprint barato e estável o bastante para decidir sync.
    # size|tables|live_rows|fingerprint
    return @"
SELECT
  COALESCE(pg_database_size(current_database()),0)::text || '|' ||
  COALESCE((SELECT count(*)::text FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'),'0') || '|' ||
  COALESCE((SELECT sum(n_live_tup)::bigint::text FROM pg_stat_user_tables),'0') || '|' ||
  COALESCE((
    SELECT md5(string_agg(schemaname || '.' || relname || ':' || n_live_tup::text, ',' ORDER BY schemaname, relname))
    FROM pg_stat_user_tables
  ),'empty')
"@
}

function Parse-Fingerprint([string]$Raw) {
    $parts = ($Raw -replace '\s', '') -split '\|'
    if ($parts.Count -lt 4) {
        return [pscustomobject]@{
            Raw      = $Raw
            SizeBytes = 0
            Tables    = 0
            LiveRows  = 0
            Hash      = 'missing'
            Ok        = $false
        }
    }
    return [pscustomobject]@{
        Raw       = $Raw.Trim()
        SizeBytes = [long]$parts[0]
        Tables    = [int]$parts[1]
        LiveRows  = [long]$parts[2]
        Hash      = $parts[3]
        Ok        = $true
    }
}

function Format-Size([long]$Bytes) {
    if ($Bytes -ge 1MB) { return ('{0:N1} MB' -f ($Bytes / 1MB)) }
    if ($Bytes -ge 1KB) { return ('{0:N1} KB' -f ($Bytes / 1KB)) }
    return "$Bytes B"
}

function Test-SourceReachable {
    Write-Host "`n==> Testando origem ${SourceHost}:${SourcePort} ..." -ForegroundColor Cyan
    try {
        $tnc = Test-NetConnection -ComputerName $SourceHost -Port $SourcePort -WarningAction SilentlyContinue
        if (-not $tnc.TcpTestSucceeded) {
            throw "TCP ${SourceHost}:${SourcePort} inacessível."
        }
    } catch {
        throw "Não consegui conectar em ${SourceHost}:${SourcePort}. Na origem rode: .\infra\open-leaction-db-lan.ps1"
    }

    $ver = Invoke-RemotePsql -DatabaseName 'postgres' -Sql 'SHOW server_version;'
    Write-Host "    Origem OK — PostgreSQL $ver" -ForegroundColor Green
}

function Ensure-LocalDb {
    if (-not (Test-LeactionDbRunning $Container)) {
        $composeDir = Join-Path $MonorepoRoot 'leaction-platform'
        Write-Host "==> Subindo $Container ..." -ForegroundColor Cyan
        Push-Location $composeDir
        try {
            docker compose up -d db | Out-Null
        } finally {
            Pop-Location
        }
        Start-Sleep -Seconds 3
        if (-not (Test-LeactionDbRunning $Container)) {
            throw "Container '$Container' não subiu. Verifique: cd leaction-platform; docker compose up -d db"
        }
    }
    $ver = Invoke-LocalPsql -DatabaseName 'postgres' -Sql 'SHOW server_version;'
    Write-Host "    Destino OK — $Container (PG $ver)" -ForegroundColor Green
}

function Get-LocalDbExists([string]$Name) {
    $q = "SELECT 1 FROM pg_database WHERE datname = '$Name'"
    $r = Invoke-LocalPsql -DatabaseName 'postgres' -Sql $q
    return [bool]$r
}

function Get-SourceDbExists([string]$Name) {
    $q = "SELECT 1 FROM pg_database WHERE datname = '$Name'"
    try {
        $r = Invoke-RemotePsql -DatabaseName 'postgres' -Sql $q
        return [bool]$r
    } catch {
        return $false
    }
}

function Sync-OneDatabase {
    param([string]$DbName)

    $safeName = $DbName -replace '[^a-zA-Z0-9_-]', '_'
    $outFile = Join-Path $DumpsDir "$safeName.sql"
    Write-Host "    dump remoto -> $DbName" -ForegroundColor Gray

    New-Item -ItemType Directory -Force -Path $DumpsDir | Out-Null

    # Dump via volume Docker (UTF-8 seguro)
    $dumpArgs = @(
        'run', '--rm',
        '-e', "PGPASSWORD=$DbPassword",
        '-v', "${DumpsDir}:/backup",
        $PgImage,
        'pg_dump',
        '-h', $SourceHost,
        '-p', "$SourcePort",
        '-U', $DbUser,
        '-d', $DbName,
        '--no-owner', '--no-acl', '--clean', '--if-exists',
        '-f', "/backup/$safeName.sql"
    )
    & docker @dumpArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $outFile)) {
        throw "pg_dump falhou para $DbName"
    }

    $quoted = Get-QuotedDbName $DbName
    Write-Host "    restore local <- $DbName" -ForegroundColor Gray

    docker exec $Container psql -U $DbUser -d postgres -v ON_ERROR_STOP=1 -c `
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DbName' AND pid <> pg_backend_pid();" | Out-Null
    docker exec $Container psql -U $DbUser -d postgres -v ON_ERROR_STOP=1 -c `
        "DROP DATABASE IF EXISTS $quoted;" | Out-Null
    docker exec $Container psql -U $DbUser -d postgres -v ON_ERROR_STOP=1 -c `
        "CREATE DATABASE $quoted;" | Out-Null

    $containerDump = "/tmp/lan-sync-$safeName.sql"
    docker cp $outFile "${Container}:${containerDump}"
    docker exec $Container psql -U $DbUser -d $DbName -v ON_ERROR_STOP=0 -q -f $containerDump | Out-Null
    docker exec $Container rm -f $containerDump | Out-Null

    $sizeKb = [math]::Round((Get-Item $outFile).Length / 1KB, 1)
    Write-Host "    OK $DbName ($sizeKb KB)" -ForegroundColor Green
}

# --- main ---

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Sync ecossistema DB (LAN → destino)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Origem : ${SourceHost}:${SourcePort}"
Write-Host "Destino: local/$Container"
Write-Host "Bancos : $($Databases -join ', ')"

Ensure-LocalDb
Test-SourceReachable

$fpSql = Get-DbFingerprintSql
$rows = @()

Write-Host "`n==> Comparando fingerprints..." -ForegroundColor Cyan

foreach ($db in $Databases) {
    $srcExists = Get-SourceDbExists $db
    $dstExists = Get-LocalDbExists $db

    $srcFp = $null
    $dstFp = $null
    $action = 'skip'
    $reason = ''

    if (-not $srcExists) {
        $reason = 'ausente na origem'
        $action = 'skip'
    } else {
        $srcFp = Parse-Fingerprint (Invoke-RemotePsql -DatabaseName $db -Sql $fpSql)
        if ($dstExists) {
            $dstFp = Parse-Fingerprint (Invoke-LocalPsql -DatabaseName $db -Sql $fpSql)
        } else {
            $dstFp = Parse-Fingerprint '0|0|0|missing'
            $reason = 'ausente no destino'
        }

        if ($ForceAll) {
            $action = 'sync'
            $reason = if ($reason) { $reason } else { 'ForceAll' }
        } elseif (-not $dstExists) {
            $action = 'sync'
        } elseif ($srcFp.Hash -ne $dstFp.Hash -or $srcFp.SizeBytes -ne $dstFp.SizeBytes) {
            $action = 'sync'
            $reason = 'diferença'
        } else {
            $action = 'ok'
            $reason = 'igual'
        }
    }

    $rows += [pscustomobject]@{
        Database   = $db
        SrcSize    = if ($srcFp) { Format-Size $srcFp.SizeBytes } else { '—' }
        DstSize    = if ($dstFp -and $dstExists) { Format-Size $dstFp.SizeBytes } else { '—' }
        SrcTables  = if ($srcFp) { $srcFp.Tables } else { '—' }
        DstTables  = if ($dstFp -and $dstExists) { $dstFp.Tables } else { '—' }
        SrcRows    = if ($srcFp) { $srcFp.LiveRows } else { '—' }
        DstRows    = if ($dstFp -and $dstExists) { $dstFp.LiveRows } else { '—' }
        Action     = $action
        Reason     = $reason
        SrcHash    = if ($srcFp) { $srcFp.Hash.Substring(0, [Math]::Min(8, $srcFp.Hash.Length)) } else { '—' }
        DstHash    = if ($dstFp -and $dstExists) { $dstFp.Hash.Substring(0, [Math]::Min(8, $dstFp.Hash.Length)) } else { '—' }
    }
}

$rows | Format-Table Database, SrcSize, DstSize, SrcTables, DstTables, SrcRows, DstRows, Action, Reason -AutoSize

$toSync = @($rows | Where-Object { $_.Action -eq 'sync' })

if ($CompareOnly) {
    Write-Host "==> CompareOnly: nada foi alterado. $($toSync.Count) banco(s) precisariam de sync.`n" -ForegroundColor Yellow
    exit 0
}

if ($toSync.Count -eq 0) {
    Write-Host "==> Destino já está alinhado com a origem. Nada a fazer.`n" -ForegroundColor Green
    exit 0
}

Write-Host "==> Serão atualizados $($toSync.Count) banco(s): $($toSync.Database -join ', ')" -ForegroundColor Yellow

if (-not $Force) {
    $answer = Read-Host "Sobrescrever esses bancos no destino? [s/N]"
    if ($answer -notmatch '^[sS]') {
        Write-Host "Cancelado.`n" -ForegroundColor Yellow
        exit 0
    }
}

New-Item -ItemType Directory -Force -Path $DumpsDir | Out-Null

foreach ($item in $toSync) {
    Write-Host "`n==> Sync $($item.Database)" -ForegroundColor Cyan
    Sync-OneDatabase -DbName $item.Database
}

Write-Host "`n==> Bancos no destino agora:" -ForegroundColor Cyan
docker exec $Container psql -U $DbUser -d postgres -c `
    "SELECT datname, pg_size_pretty(pg_database_size(datname)) AS size FROM pg_database WHERE datistemplate = false AND datname <> 'postgres' ORDER BY 1;"

Write-Host "`n==> Sync concluído. Dumps temporários em: $DumpsDir" -ForegroundColor Green
Write-Host "    (pode apagar a pasta db-pack\_lan-sync se quiser)`n" -ForegroundColor DarkGray
