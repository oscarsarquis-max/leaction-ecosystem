$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:ISA_ENV = "production"
$env:ISA_DATABASE_URL = "postgresql://isa:isa_local_only@127.0.0.1:5442/isa"
$env:ISA_PORT = "8099"
$env:ISA_ORIGIN = "http://127.0.0.1:8099"
$env:ISA_OIDC_REHEARSAL = "1"
$env:ISA_OIDC_ISSUER = "http://127.0.0.1:8096"
$env:ISA_OIDC_DISCOVERY = "http://127.0.0.1:8096/.well-known/openid-configuration"
$env:ISA_OIDC_CLIENT_ID = "isa-ensaio"
$env:ISA_OIDC_REDIRECT = "http://127.0.0.1:8099/callback"
if (-not $env:ISA_OIDC_ALLOWED_SUBS) { $env:ISA_OIDC_ALLOWED_SUBS = "" }
Write-Host "Ensaio local de producao em http://127.0.0.1:8099"
Write-Host "PostgreSQL local na porta 5442. A senha deste URL so vale para esse container e nao e credencial do Finance."
Write-Host "Provedor de ensaio na porta 8096. Nao e Cognito e nao publica."
python (Join-Path $root "server\prod_serve.py")
