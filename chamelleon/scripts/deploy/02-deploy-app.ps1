<#
.SYNOPSIS
  Publica backend + frontend do Chamelleon na EC2 (rsync via SCP).

.EXAMPLE
  .\scripts\deploy\02-deploy-app.ps1
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

if (-not $ServerHost -and (Test-Path $StateFile)) {
    $state = Get-Content $StateFile | ConvertFrom-Json
    $ServerHost = $state.public_ip
}
if (-not $ServerHost) {
    throw "Informe -ServerHost ou rode 01-provision-ec2.ps1 primeiro."
}
if (-not (Test-Path $KeyFile)) {
    throw "Chave SSH nao encontrada: $KeyFile"
}

$sshOpts = @('-o', 'StrictHostKeyChecking=accept-new')
$remote = "ubuntu@$ServerHost"
$appRoot = $cfg.AppRoot

Write-Host "`n==> Deploy Chamelleon -> $ServerHost" -ForegroundColor Cyan

# Build frontend local
Write-Host "Build frontend..." -ForegroundColor Yellow
Push-Location (Join-Path $RepoRoot 'frontend')
if (-not (Test-Path 'node_modules')) { npm ci }
$env:VITE_DIARIO_OBRA_URL = "https://$($cfg.Domain)/diario-obra"
npm run build
Remove-Item Env:VITE_DIARIO_OBRA_URL -ErrorAction SilentlyContinue
Pop-Location

# Sync codigo (exclui venv, node_modules)
Write-Host "Enviando arquivos..." -ForegroundColor Yellow
$exclude = @('node_modules', '.venv', '__pycache__', '.git', 'dist')
$backendSrc = Join-Path $RepoRoot 'backend'
$frontendSrc = Join-Path $RepoRoot 'frontend'

scp @sshOpts -i $KeyFile -r `
    (Join-Path $backendSrc 'app') `
    (Join-Path $backendSrc 'run.py') `
    (Join-Path $backendSrc 'requirements.txt') `
    "${remote}:${appRoot}/backend/"

scp @sshOpts -i $KeyFile -r `
    (Join-Path $frontendSrc 'dist') `
    "${remote}:${appRoot}/frontend/"

scp @sshOpts -i $KeyFile -r `
    (Join-Path $backendSrc 'scripts') `
    "${remote}:${appRoot}/backend/"

$remoteScriptLocal = Join-Path $RepoRoot 'infra/aws/remote-deploy.sh'
$remoteScriptUnix = Join-Path $env:TEMP 'chamelleon-deploy-unix.sh'
$scriptContent = (Get-Content -Path $remoteScriptLocal -Raw) -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($remoteScriptUnix, $scriptContent, [System.Text.UTF8Encoding]::new($false))
scp @sshOpts -i $KeyFile $remoteScriptUnix "${remote}:/tmp/chamelleon-deploy.sh"
ssh @sshOpts -i $KeyFile $remote "chmod +x /tmp/chamelleon-deploy.sh && bash /tmp/chamelleon-deploy.sh"

Write-Host "`n==> Deploy concluido (dados preservados, sem seed/reset)" -ForegroundColor Green
Write-Host "  https://$($cfg.Domain)"
Write-Host "  Nao executar seed em producao salvo pedido explicito."
