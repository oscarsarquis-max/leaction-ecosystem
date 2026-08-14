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
        ML_REQUEST_TIMEOUT_S       = '12'
        ML_LISTING_ENRICH_MAX      = '0'
        MARKETPLACE_LIVE_BUDGET_S  = '18'
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

# Mesmo criterio do monitor (/api/sys/status): health sozinho mente — UI usa offers/vitrine.
# Live ML pode levar >5s; request timeout alto para nao marcar falso negativo.
Write-HubInfo "Validando rotas funcionais do Marketplace (offers + vitrine)..."
if (-not (Wait-HttpOk -Url 'http://127.0.0.1:4012/api/marketplace/offers' -TimeoutSec 90 -RequestTimeoutSec 45)) {
    Write-HubErr "Marketplace health OK, mas /offers falhou (criterio do monitor). Veja .dev-logs/marketplace.*.log"
    exit 1
}
if (-not (Wait-HttpOk -Url 'http://127.0.0.1:4012/api/marketplace/vitrine' -TimeoutSec 90 -RequestTimeoutSec 45)) {
    Write-HubErr "Marketplace health OK, mas /vitrine falhou (criterio do monitor). Veja .dev-logs/marketplace.*.log"
    exit 1
}
Write-HubOk "Marketplace OK -> health + curation + offers + vitrine"

# --- Frontend :4000 ---
if (-not $SkipFrontend) {
    Write-HubInfo "Iniciando Action Hub FE :4000"
    Start-ActionHubFrontendDev

    if (-not (Wait-HttpOk -Url 'http://127.0.0.1:4000/api/health' -TimeoutSec 90)) {
        Write-HubErr "Frontend nao subiu. Veja .dev-logs/action-hub.err.log"
        exit 1
    }
    Write-HubOk "Frontend OK -> http://localhost:4000"

    # Mesmo criterio da UI /dashboard/monitor — detecta 404 por cache Turbopack e recupera.
    if (-not (Assert-HubMonitorStatus -AllowHealFrontend)) {
        Write-HubErr "Monitor do Hub falhou apos o start."
        exit 1
    }
}

Write-Host ""
Write-HubOk "Hub pronto."
Write-Host "  FE:          http://localhost:4000"
Write-Host "  Monitor:     http://localhost:4000/dashboard/monitor"
Write-Host "  Gateway:     http://127.0.0.1:4001/health"
Write-Host "  Marketplace: http://127.0.0.1:4012/api/marketplace/health"
Write-Host "  Status:      .\scripts\dev\status-hub.ps1"
Write-Host "  Parar:       .\scripts\dev\stop-hub.ps1"
Write-Host "  Logs:        .dev-logs\"
Write-Host ""
