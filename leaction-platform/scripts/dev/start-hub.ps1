# Sobe Action Hub local de forma estável (ordem + healthchecks).
#
# Uso:
#   .\scripts\dev\start-hub.ps1
#   .\scripts\dev\start-hub.ps1 -SkipFrontend
#   .\scripts\dev\start-hub.ps1 -ForceRestart
#
# servicos:
#   Postgres (docker leaction_db) -> Gateway :4001 -> Marketplace :4012 -> Next :4000

param(
    [switch]$SkipFrontend,
    [switch]$ForceRestart,
    [switch]$KeepExisting
)

. "$PSScriptRoot\_hub-dev-common.ps1"

Write-Host ""
Write-HubInfo "=== Action Hub local ==="
Write-HubInfo "Root: $HubRoot"

Ensure-HubNodeOnPath
Ensure-DevLogsDir

$dbUrl = Ensure-HubPostgres

if ($ForceRestart -or -not $KeepExisting) {
    Write-HubInfo "Limpando portas 4000/4001/4012 (evita Flask/Node orfaos)..."
    Stop-PortListeners -Ports $script:HubPorts
}

$venvPython = Join-Path $HubRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Venv do Marketplace ausente: $venvPython`nCrie com: cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
}

# --- Gateway :4001 ---
$gatewayDir = Join-Path $HubRoot 'services\gateway-api'
if (-not (Test-Path (Join-Path $gatewayDir 'node_modules'))) {
    Write-HubWarn "Instalando deps do gateway..."
    Push-Location $gatewayDir
    try { npm install } finally { Pop-Location }
}

Write-HubInfo "Iniciando Gateway :4001"
$null = Start-HubLoggedProcess -Name 'gateway' `
    -WorkingDirectory $gatewayDir `
    -FilePath 'node' `
    -ArgumentList @('server.js') `
    -Environment @{
        NODE_ENV = 'development'
    }

if (-not (Wait-HttpOk -Url 'http://127.0.0.1:4001/health' -TimeoutSec 40)) {
    Write-HubErr "Gateway nao subiu. Veja .dev-logs/gateway.err.log"
    exit 1
}
Write-HubOk "Gateway OK -> http://127.0.0.1:4001/health"

# --- Marketplace :4012 ---
Write-HubInfo "Iniciando Marketplace :4012"
$null = Start-HubLoggedProcess -Name 'marketplace' `
    -WorkingDirectory $HubRoot `
    -FilePath $venvPython `
    -ArgumentList @((Join-Path $HubRoot 'backend\run.py')) `
    -Environment @{
        MARKETPLACE_PORT           = '4012'
        DATABASE_URL               = $dbUrl
        MARKETPLACE_DATABASE_URL   = $dbUrl
        ML_PUBLIC_BASE_URL         = 'http://127.0.0.1:4000'
        FLASK_DEBUG                = '1'
        MARKETPLACE_USE_RELOADER   = '0'
    }

if (-not (Wait-HttpOk -Url 'http://127.0.0.1:4012/api/marketplace/health' -TimeoutSec 45)) {
    Write-HubErr "Marketplace nao subiu. Veja .dev-logs/marketplace.err.log"
    exit 1
}

# Curation precisa responder (200) - sem auth no Flask direto
if (-not (Wait-HttpOk -Url 'http://127.0.0.1:4012/api/marketplace/curation' -TimeoutSec 20)) {
    Write-HubErr "Marketplace health OK, mas /curation falhou. Veja .dev-logs/marketplace.*.log"
    exit 1
}
Write-HubOk "Marketplace OK -> http://127.0.0.1:4012/api/marketplace/health"

# --- Frontend :4000 ---
if (-not $SkipFrontend) {
    $feDir = Join-Path $HubRoot 'frontend\action-hub'
    if (-not (Test-Path (Join-Path $feDir 'node_modules'))) {
        Write-HubWarn "Instalando deps do frontend..."
        Push-Location $feDir
        try { npm install } finally { Pop-Location }
    }

    Write-HubInfo "Iniciando Action Hub FE :4000"
    # npm.cmd + redirect via cmd evita hang do Start-Process com npm no Windows
    Ensure-DevLogsDir
    $feOut = Join-Path $script:DevLogs 'action-hub.out.log'
    $feErr = Join-Path $script:DevLogs 'action-hub.err.log'
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $feOut -Value "`n==== start $stamp ====`n"
    Add-Content -LiteralPath $feErr -Value "`n==== start $stamp ====`n"
    $feCmd = "npm run dev 1>>`"$feOut`" 2>>`"$feErr`""
    $null = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList @('/c', $feCmd) `
        -WorkingDirectory $feDir `
        -WindowStyle Hidden
    Write-HubInfo "action-hub -> logs .dev-logs/action-hub.*.log"

    if (-not (Wait-HttpOk -Url 'http://127.0.0.1:4000/api/health' -TimeoutSec 90)) {
        Write-HubErr "Frontend nao subiu. Veja .dev-logs/action-hub.err.log"
        exit 1
    }
    Write-HubOk "Frontend OK -> http://localhost:4000"
}

Write-Host ""
Write-HubOk "Hub pronto."
Write-Host "  FE:          http://localhost:4000"
Write-Host "  Gateway:     http://127.0.0.1:4001/health"
Write-Host "  Marketplace: http://127.0.0.1:4012/api/marketplace/health"
Write-Host "  Status:      .\scripts\dev\status-hub.ps1"
Write-Host "  Parar:       .\scripts\dev\stop-hub.ps1"
Write-Host "  Logs:        .dev-logs\"
Write-Host ""
