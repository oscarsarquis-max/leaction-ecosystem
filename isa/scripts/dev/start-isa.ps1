$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:ISA_ENV = "lab"
$env:ISA_DATA = Join-Path $root "data\lab"
$env:ISA_BACKUP_ROOT = Join-Path $root "data\backups"
$env:ISA_PORT = "8098"
Write-Host "ISA local em http://127.0.0.1:8098  (identidade sintetica de laboratorio, nao e producao)"
python (Join-Path $root "server\serve.py")
