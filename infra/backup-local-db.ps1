<#
.SYNOPSIS
  Exporta bancos do PostgreSQL LOCAL (:5432) para db-pack/ (transferir a outra maquina).

.DESCRIPTION
  Somente leitura na origem. Dump via arquivo no Docker - sem pipe PowerShell.
  Na maquina destino: .\infra\restore-ecosystem-db.ps1 -Force

.EXAMPLE
  .\backup-local-db.ps1
  .\backup-local-db.ps1 -OutputRoot D:\db-pack-leaction
#>
[CmdletBinding()]
param(
    [string]$OutputRoot,
    [string]$SourceHost = 'host.docker.internal',
    [int]$SourcePort = 5432,
    [string]$SourceUser = 'postgres',
    [string]$SourcePass = 'Cmgv6190!@',
    [string]$PgImage = 'postgres:18'
)

$ErrorActionPreference = 'Stop'

$MonorepoRoot = Split-Path $PSScriptRoot -Parent
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $MonorepoRoot 'db-pack'
}
$DumpsDir = Join-Path $OutputRoot 'dumps'

$Databases = @(
    'LeAction_SysF',
    'MAtivas',
    'chamelleon',
    'inove4us',
    'prodinx',
    'LASim'
)

New-Item -ItemType Directory -Force -Path $DumpsDir | Out-Null

$pgVersion = docker run --rm `
    -e "PGPASSWORD=$SourcePass" `
    --add-host=host.docker.internal:host-gateway `
    $PgImage `
    psql -h $SourceHost -p $SourcePort -U $SourceUser -d postgres -tAc "SHOW server_version;"

Write-Host "`n==> Backup PG local :5432 (PG $pgVersion) -> $DumpsDir" -ForegroundColor Cyan
Write-Host "    Origem: somente leitura. Nada e alterado no PG local." -ForegroundColor DarkGray

$manifest = [ordered]@{
    created_at = (Get-Date -Format 'o')
    pg_version = $pgVersion.Trim()
    source     = "local:$SourcePort"
    source_user = $SourceUser
    databases  = @()
}

foreach ($db in $Databases) {
    $safeName = $db -replace '[^a-zA-Z0-9_-]', '_'
    $outFile = Join-Path $DumpsDir "$safeName.sql"
    Write-Host "    -> $db" -ForegroundColor Gray

    docker run --rm `
        -e "PGPASSWORD=$SourcePass" `
        --add-host=host.docker.internal:host-gateway `
        -v "${DumpsDir}:/backup" `
        $PgImage `
        pg_dump -h $SourceHost -p $SourcePort -U $SourceUser -d $db --no-owner --no-acl --clean --if-exists `
        -f "/backup/$safeName.sql"

    $sizeKb = [math]::Round((Get-Item $outFile).Length / 1KB, 1)
    $manifest.databases += [ordered]@{
        name    = $db
        file    = "dumps/$safeName.sql"
        size_kb = $sizeKb
    }
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $OutputRoot 'manifest.json') -Encoding utf8

Write-Host "`n==> Arquivos:" -ForegroundColor Cyan
Get-ChildItem $DumpsDir -Filter '*.sql' | ForEach-Object {
    Write-Host ("    {0,-22} {1,8:N1} KB" -f $_.Name, ($_.Length / 1KB))
}

Write-Host "`n==> Copie db-pack/ para a outra maquina (zip/USB)." -ForegroundColor Green
Write-Host "    Destino: cd infra; .\restore-ecosystem-db.ps1 -Force`n" -ForegroundColor Green
