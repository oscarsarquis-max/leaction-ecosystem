<#
.SYNOPSIS
  Copia bancos do PostgreSQL local (:5432 / PG18) para leaction_db Docker (:5433).
#>
$ErrorActionPreference = 'Stop'

$SourceHost = 'host.docker.internal'
$SourcePort = '5432'
$SourceUser = 'postgres'
$SourcePass = 'Cmgv6190!@'
$TargetContainer = 'leaction_db'
$TargetUser = 'admin'
$PgImage = 'postgres:18'

$Databases = @(
    'LeAction_SysF',
    'MAtivas',
    'chamelleon',
    'inove4us',
    'prodinx',
    'LASim'
)

function Get-QuotedDbName([string]$Name) {
    if ($Name -cmatch '^[a-z_][a-z0-9_]*$') { return $Name }
    return '"' + $Name + '"'
}

function Invoke-TargetPsql([string]$Sql) {
    docker exec $TargetContainer psql -U $TargetUser -d postgres -v ON_ERROR_STOP=1 -c "$Sql" | Out-Null
}

Write-Host "`n==> Migrando :5432 (PG18) -> leaction_db (:5433)" -ForegroundColor Cyan

foreach ($db in $Databases) {
    Write-Host "    -> $db" -ForegroundColor Gray
    $quoted = Get-QuotedDbName $db

    Invoke-TargetPsql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db' AND pid <> pg_backend_pid();"
    Invoke-TargetPsql "DROP DATABASE IF EXISTS $quoted;"
    Invoke-TargetPsql "CREATE DATABASE $quoted;"

    docker run --rm `
        -e "PGPASSWORD=$SourcePass" `
        --add-host=host.docker.internal:host-gateway `
        $PgImage `
        pg_dump -h $SourceHost -p $SourcePort -U $SourceUser -d $db --no-owner --no-acl `
        | docker exec -i $TargetContainer psql -U $TargetUser -d $db -v ON_ERROR_STOP=0 -q | Out-Null
}

Write-Host "`n==> Bancos no leaction_db:" -ForegroundColor Cyan
docker exec $TargetContainer psql -U $TargetUser -d postgres -t -c `
    "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY 1;"

Write-Host "`n==> Migracao concluida." -ForegroundColor Green
