#Requires -Version 5.1
<#
.SYNOPSIS
  Dump completo do DB local inove4us (Docker) para bootstrap do RDS de produção.
#>
param(
  [string]$Container = "leaction_db",
  [string]$DbName = "inove4us",
  [string]$DbUser = "admin",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
if (-not $OutFile) {
  $OutFile = Join-Path $PSScriptRoot "..\db\inove4us-prod-bootstrap.sql"
}
$OutFile = [System.IO.Path]::GetFullPath($OutFile)
$dir = Split-Path $OutFile -Parent
New-Item -ItemType Directory -Force -Path $dir | Out-Null

Write-Host "==> Dump $DbName -> $OutFile"
docker exec $Container pg_dump -U $DbUser -d $DbName --no-owner --no-acl --clean --if-exists -f /tmp/inove4us-prod.sql
if ($LASTEXITCODE -ne 0) { throw "pg_dump falhou" }
docker cp "${Container}:/tmp/inove4us-prod.sql" $OutFile
docker exec $Container rm -f /tmp/inove4us-prod.sql | Out-Null
$size = [math]::Round((Get-Item $OutFile).Length / 1KB, 1)
Write-Host "==> OK ($size KB)"
