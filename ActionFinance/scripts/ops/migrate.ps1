#Requires -Version 5.1
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string] $JdbcUrl,
  [Parameter(Mandatory = $true)][string] $MigratorUser,
  [Parameter(Mandatory = $true)][string] $MigratorPassword
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location (Join-Path $root "backend")
$env:ACTIONFINANCE_DATASOURCE_URL = $JdbcUrl
$env:ACTIONFINANCE_MIGRATOR_USERNAME = $MigratorUser
$env:ACTIONFINANCE_MIGRATOR_PASSWORD = $MigratorPassword
$env:ACTIONFINANCE_RUNTIME_USERNAME = $MigratorUser
$env:ACTIONFINANCE_RUNTIME_PASSWORD = $MigratorPassword
& .\mvnw -q flyway:migrate "-Dflyway.url=$JdbcUrl" "-Dflyway.user=$MigratorUser" "-Dflyway.password=$MigratorPassword" "-Dflyway.defaultSchema=actionfinance" "-Dflyway.locations=filesystem:../database/migrations"
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
Write-Host "Flyway migrate finished. Runtime should use actionfinance_runtime, not these migrator credentials."
