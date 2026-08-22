#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$NodeDir = Join-Path (Split-Path $Root -Parent) '.tools\node'
if (Test-Path (Join-Path $NodeDir 'npm.cmd')) {
    $env:Path = "$NodeDir;$env:Path"
}
$Frontend = Join-Path $Root 'frontend'
Set-Location $Frontend
npm run dev
