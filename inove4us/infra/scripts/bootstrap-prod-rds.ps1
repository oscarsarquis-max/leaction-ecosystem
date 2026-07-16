#Requires -Version 5.1
param(
  [string]$DumpFile = "",
  [string]$AwsRegion = "us-east-2",
  [string]$SecretId = "inove4us/prod/db"
)

$ErrorActionPreference = "Stop"
if (-not $DumpFile) {
  $DumpFile = Join-Path $PSScriptRoot "..\db\inove4us-prod-bootstrap.sql"
}
$DumpFile = [System.IO.Path]::GetFullPath($DumpFile)
if (-not (Test-Path $DumpFile)) { throw "Dump nao encontrado: $DumpFile" }

Write-Host "==> Lendo secret $SecretId"
$secretJson = aws secretsmanager get-secret-value --secret-id $SecretId --region $AwsRegion --query SecretString --output text
if ($LASTEXITCODE -ne 0) { throw "Falha ao ler secret" }
$sec = $secretJson | ConvertFrom-Json

$dbHost = [string]$sec.host
$dbPort = [string]$sec.port
$dbName = [string]$sec.dbname
$dbUser = [string]$sec.username
$dbPass = [string]$sec.password
$conn = "host=$dbHost port=$dbPort dbname=$dbName user=$dbUser sslmode=require"

Write-Host "==> Restore em ${dbHost}:${dbPort}/${dbName} (user=$dbUser)"
$env:PGPASSWORD = $dbPass

$psqlCmd = Get-Command psql -ErrorAction SilentlyContinue
if ($null -ne $psqlCmd) {
  & psql $conn -v ON_ERROR_STOP=1 -f $DumpFile
  if ($LASTEXITCODE -ne 0) { throw "psql restore falhou" }
} else {
  Write-Host "    psql local ausente - usando docker postgres:16"
  $dumpDir = Split-Path $DumpFile -Parent
  $dumpLeaf = Split-Path $DumpFile -Leaf
  docker run --rm `
    -e PGPASSWORD=$dbPass `
    -v "${dumpDir}:/dump:ro" `
    postgres:16 `
    psql $conn -v ON_ERROR_STOP=1 -f "/dump/$dumpLeaf"
  if ($LASTEXITCODE -ne 0) { throw "docker psql restore falhou" }
}

Write-Host "==> Validando seed"
$query = "SELECT c.mail_clie, a.access_code FROM ctdi_clie c JOIN ctdi_lead_access a ON a.id_clie=c.id_clie WHERE LOWER(TRIM(c.mail_clie))='inovador@inove4us.com.br';"
if ($null -ne $psqlCmd) {
  & psql $conn -c $query
} else {
  docker run --rm -e PGPASSWORD=$dbPass postgres:16 psql $conn -c $query
}

Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
Write-Host "==> OK"
