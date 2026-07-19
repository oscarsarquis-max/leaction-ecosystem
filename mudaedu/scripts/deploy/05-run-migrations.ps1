<#
.SYNOPSIS
  Aplica migrations SQL pendentes no RDS PanelDX (LeAction_SysF).

  Requer psql no PATH. Use ANTES ou DEPOIS do deploy conforme a migration.

.PARAMETER DatabaseUrl
  URL completa postgresql://user:pass@host:5432/LeAction_SysF?sslmode=require
  Se omitida, le de $env:PANELDX_DATABASE_URL ou LeAction_SysF/.env (DB_*)

.EXAMPLE
  $env:PANELDX_DATABASE_URL = "postgresql://user:pass@endpoint:5432/LeAction_SysF?sslmode=require"
  .\scripts\deploy\05-run-migrations.ps1

  .\scripts\deploy\05-run-migrations.ps1 -Only 003_ctdi_clie_moderacao_contexto.sql
#>
[CmdletBinding()]
param(
    [string]$DatabaseUrl,
    [string[]]$Only
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$MigrationsDir = Join-Path $RepoRoot 'migrations'

function Get-DatabaseUrl {
    if ($DatabaseUrl) { return $DatabaseUrl }
    if ($env:PANELDX_DATABASE_URL) { return $env:PANELDX_DATABASE_URL }

    $envFile = Join-Path $RepoRoot 'LeAction_SysF/.env'
    if (-not (Test-Path $envFile)) {
        throw 'Defina -DatabaseUrl ou $env:PANELDX_DATABASE_URL ou LeAction_SysF/.env'
    }
    $vars = @{}
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $vars[$matches[1].Trim()] = $matches[2].Trim()
        }
    }
    $dbHost = $vars['DB_HOST']
    $port = if ($vars['DB_PORT']) { $vars['DB_PORT'] } else { '5432' }
    $db   = $vars['DB_NAME']
    $user = $vars['DB_USER']
    $pass = $vars['DB_PASS']
    $ssl  = if ($vars['DB_SSLMODE']) { $vars['DB_SSLMODE'] } else { 'require' }
    if (-not ($dbHost -and $db -and $user)) { throw 'DB_HOST, DB_NAME e DB_USER obrigatorios no .env' }
    $encPass = [uri]::EscapeDataString($pass)
    return "postgresql://${user}:${encPass}@${dbHost}:${port}/${db}?sslmode=${ssl}"
}

if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    throw 'psql nao encontrado. Instale PostgreSQL client ou use WSL.'
}

$url = Get-DatabaseUrl
$files = Get-ChildItem $MigrationsDir -Filter '*.sql' | Sort-Object Name
if ($Only) {
    $files = $files | Where-Object { $Only -contains $_.Name }
}
if (-not $files) {
    Write-Host 'Nenhuma migration para aplicar.' -ForegroundColor Yellow
    exit 0
}

Write-Host "`n==> Migrations PanelDX ($($files.Count) arquivo(s))" -ForegroundColor Cyan
foreach ($f in $files) {
    Write-Host "    -> $($f.Name)" -ForegroundColor Gray
    & psql $url -v ON_ERROR_STOP=1 -f $f.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Migration falhou: $($f.Name)"
    }
}
Write-Host "`n==> Migrations aplicadas com sucesso." -ForegroundColor Green
