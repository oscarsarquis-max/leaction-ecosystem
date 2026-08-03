# Single-command API client generation for the QMind monorepo.
# Reads committed openapi.json only (tag openapi-v1-initial).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Test-Path "node_modules")) {
  npm install
}
npm run generate:api-client
Write-Host "OK — regenerated packages/api-client/src/generated"
