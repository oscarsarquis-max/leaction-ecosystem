$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:ISA_ENV = "production"
$env:ISA_DATA = Join-Path $root "data\prod-rehearsal"
$env:ISA_PORT = "8099"
$env:ISA_ORIGIN = "http://127.0.0.1:8099"
Write-Host "Ensaio local de producao em http://127.0.0.1:8099"
Write-Host "Nao publica, nao cria recurso e nao autentica uma pessoa real."
python (Join-Path $root "server\prod_serve.py")
