$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location (Join-Path $root "frontend")
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
& $npm run dev
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
