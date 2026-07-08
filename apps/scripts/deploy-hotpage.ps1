<#
.SYNOPSIS
  Publica Diário de Obra como hotpage do Chamelleon (URL direta, sem link no menu).

.EXAMPLE
  .\scripts\deploy-hotpage.ps1
  .\scripts\deploy-hotpage.ps1 -ServerHost 18.227.125.118
#>
[CmdletBinding()]
param(
    [string]$ServerHost,
    [string]$KeyFile = 'C:\Projetos\Chaves\paneldx-bastion-key.pem'
)

$ErrorActionPreference = 'Stop'
$AppsRoot = Split-Path -Parent $PSScriptRoot
$ApiDir = Join-Path $AppsRoot 'diario-obra-api'
$WebDir = Join-Path $AppsRoot 'diario-obra-web'
$InfraDir = Join-Path $AppsRoot 'infra'

if (-not $ServerHost) {
    $stateFile = 'C:\Projetos\chamelleon\infra\aws\state.json'
    if (Test-Path $stateFile) {
        $state = Get-Content $stateFile | ConvertFrom-Json
        $ServerHost = $state.public_ip
    }
}
if (-not $ServerHost) { throw 'Informe -ServerHost ou provisione o Chamelleon primeiro.' }
if (-not (Test-Path $KeyFile)) { throw "Chave SSH nao encontrada: $KeyFile" }

$sshOpts = @('-o', 'StrictHostKeyChecking=accept-new')
$remote = "ubuntu@$ServerHost"
$hotpageRoot = '/opt/chamelleon/hotpages/diario-obra'
$apiRoot = '/opt/chamelleon/hotpages/diario-obra-api'

Write-Host "`n==> Deploy hotpage Diario de Obra -> $ServerHost" -ForegroundColor Cyan

Write-Host 'Build frontend (base /diario-obra/)...' -ForegroundColor Yellow
Push-Location $WebDir
if (-not (Test-Path 'node_modules')) { npm ci }
$env:VITE_BASE_PATH = '/diario-obra/'
$env:VITE_CHAMELLEON_URL = 'https://chamelleon.com.br'
npm run build
Remove-Item Env:VITE_BASE_PATH -ErrorAction SilentlyContinue
Remove-Item Env:VITE_CHAMELLEON_URL -ErrorAction SilentlyContinue
Pop-Location

Write-Host 'Enviando API...' -ForegroundColor Yellow
ssh @sshOpts -i $KeyFile $remote "mkdir -p ${apiRoot} ${hotpageRoot}"
scp @sshOpts -i $KeyFile -r `
    (Join-Path $ApiDir 'app') `
    (Join-Path $ApiDir 'run.py') `
    (Join-Path $ApiDir 'requirements.txt') `
    (Join-Path $ApiDir '.env.production') `
    "${remote}:${apiRoot}/"

Write-Host 'Enviando frontend...' -ForegroundColor Yellow
$distDir = Join-Path $WebDir 'dist'
scp @sshOpts -i $KeyFile -r "${distDir}/." "${remote}:${hotpageRoot}/"

$toUnix = {
    param($src, $dst)
    $content = (Get-Content -Path $src -Raw) -replace "`r`n", "`n"
    $tmp = Join-Path $env:TEMP (Split-Path $src -Leaf)
    [System.IO.File]::WriteAllText($tmp, $content, [System.Text.UTF8Encoding]::new($false))
    scp @sshOpts -i $KeyFile $tmp "${remote}:$dst"
}

& $toUnix (Join-Path $InfraDir 'remote-deploy-diario-obra.sh') '/tmp/remote-deploy-diario-obra.sh'
& $toUnix (Join-Path $InfraDir 'nginx-diario-obra-snippet.conf') '/tmp/nginx-diario-obra-snippet.conf'
& $toUnix (Join-Path $InfraDir 'diario-obra-api.service') '/tmp/diario-obra-api.service'

ssh @sshOpts -i $KeyFile $remote "chmod +x /tmp/remote-deploy-diario-obra.sh && bash /tmp/remote-deploy-diario-obra.sh"
if ($LASTEXITCODE -ne 0) { throw "Deploy remoto falhou (exit $LASTEXITCODE)." }

Write-Host "`n==> Hotpage publicada" -ForegroundColor Green
Write-Host '  https://chamelleon.com.br/diario-obra/'
Write-Host '  (sem link no menu — acesso somente por URL)'
