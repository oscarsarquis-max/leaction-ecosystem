<#
.SYNOPSIS
  Exporta bundles locais e importa na EC2 (telecom + construcao civil).

.EXAMPLE
  .\scripts\deploy\03-sync-sector-frameworks.ps1
#>
[CmdletBinding()]
param(
    [string]$ServerHost,
    [string]$KeyFile = 'C:\Projetos\Chaves\paneldx-bastion-key.pem'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../infra/aws/_config.ps1')

$cfg = $script:ChamelleonAws
$RepoRoot = Get-ChamelleonRepoRoot
$StateFile = Join-Path $RepoRoot 'infra/aws/state.json'
$Python = Join-Path $RepoRoot 'backend\.venv\Scripts\python.exe'
$BundleDir = Join-Path $RepoRoot 'infra\data\bundles'

if (-not $ServerHost -and (Test-Path $StateFile)) {
    $state = Get-Content $StateFile | ConvertFrom-Json
    $ServerHost = $state.public_ip
}
if (-not $ServerHost) { throw "Informe -ServerHost ou rode 01-provision-ec2.ps1." }
if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile" }

Write-Host "`n==> Exportando bundles locais..." -ForegroundColor Cyan
& $Python (Join-Path $RepoRoot 'backend\scripts\export_framework_bundle.py') --gzip

Write-Host "`n==> Enviando bundles para EC2..." -ForegroundColor Cyan
ssh -o StrictHostKeyChecking=accept-new -i $KeyFile "ubuntu@$ServerHost" "mkdir -p /opt/chamelleon/infra/data/bundles"
scp -i $KeyFile "$BundleDir\telecomunicacoes-v1.json.gz" "ubuntu@${ServerHost}:/opt/chamelleon/infra/data/bundles/"
scp -i $KeyFile "$BundleDir\construcao-civil-v1.json.gz" "ubuntu@${ServerHost}:/opt/chamelleon/infra/data/bundles/"

Write-Host "`n==> Importando no servidor..." -ForegroundColor Cyan
$importCmd = 'cd /opt/chamelleon/backend && . .venv/bin/activate && export PYTHONPATH=/opt/chamelleon/backend && python scripts/import_framework_bundle.py /opt/chamelleon/infra/data/bundles/telecomunicacoes-v1.json.gz /opt/chamelleon/infra/data/bundles/construcao-civil-v1.json.gz'
ssh -i $KeyFile "ubuntu@$ServerHost" $importCmd

Write-Host "`n==> Seed MVP + diagnostico estagio 3..." -ForegroundColor Cyan
curl.exe -s -X POST "https://$($cfg.Domain)/api/seed/sector-frameworks" | Write-Host
curl.exe -s -X POST "https://$($cfg.Domain)/api/seed/mvp" | Write-Host
curl.exe -s -X POST "https://$($cfg.Domain)/api/seed/dev-client/3" -H "Content-Type: application/json" -d '{\"sector\":\"telecom\"}' | Write-Host
curl.exe -s -X POST "https://$($cfg.Domain)/api/seed/dev-client/3" -H "Content-Type: application/json" -d '{\"sector\":\"construcao\"}' | Write-Host

Write-Host "`n==> Setores prontos em https://$($cfg.Domain)" -ForegroundColor Green
