# Sobe inove4us local e, SEMPRE, o Action Hub (+ gateway/marketplace/Postgres).
#
# Uso:
#   .\scripts\dev\start-inove.ps1
#   .\scripts\dev\start-inove.ps1 -SkipHub
#   .\scripts\dev\start-inove.ps1 -ForceRestartHub
#   .\scripts\dev\start-inove.ps1 -SkipFrontend
#
# Portas tipicas:
#   Hub FE :4000 | Gateway :4001 | Marketplace :4012
#   inove API :5011 | inove FE :5174

param(
    [switch]$SkipHub,
    [switch]$ForceRestartHub,
    [switch]$SkipFrontend,
    [switch]$SkipBackend
)

$ErrorActionPreference = 'Stop'

$InoveRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$HubRoot = (Resolve-Path (Join-Path $InoveRoot '..\leaction-platform')).Path
$StartHub = Join-Path $HubRoot 'scripts\dev\start-hub.ps1'
$DevLogs = Join-Path $InoveRoot '.dev-logs'
$ToolsNode = Join-Path $InoveRoot '..\.tools\node'

function Write-InoveInfo([string]$Message) {
    Write-Host "[inove-dev] $Message" -ForegroundColor Cyan
}
function Write-InoveOk([string]$Message) {
    Write-Host "[inove-dev] $Message" -ForegroundColor Green
}
function Write-InoveWarn([string]$Message) {
    Write-Host "[inove-dev] $Message" -ForegroundColor Yellow
}
function Write-InoveErr([string]$Message) {
    Write-Host "[inove-dev] $Message" -ForegroundColor Red
}

function Test-HttpOk([string]$Url, [int]$TimeoutSec = 3) {
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return ([int]$resp.StatusCode -ge 200 -and [int]$resp.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Wait-HttpOk([string]$Url, [int]$TimeoutSec = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk -Url $Url -TimeoutSec 3) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Stop-PortListeners([int[]]$Ports) {
    foreach ($port in $Ports) {
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object {
                try {
                    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
                } catch {}
            }
    }
}

function Ensure-NodeOnPath {
    $resolved = Resolve-Path $ToolsNode -ErrorAction SilentlyContinue
    if ($resolved) {
        $env:Path = "$($resolved.Path);$env:Path"
    }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        throw 'Node.js nao encontrado. Use .tools/node do monorepo ou instale Node 20+.'
    }
}

if (-not (Test-Path -LiteralPath $DevLogs)) {
    New-Item -ItemType Directory -Path $DevLogs | Out-Null
}

Write-Host ''
Write-InoveInfo '=== inove4us local ==='
Write-InoveInfo "Root: $InoveRoot"

# --- Action Hub (obrigatorio salvo -SkipHub) ---
if (-not $SkipHub) {
    if (-not (Test-Path -LiteralPath $StartHub)) {
        throw "start-hub.ps1 nao encontrado: $StartHub"
    }

    $hubUp = (Test-HttpOk 'http://127.0.0.1:4001/health') -and (Test-HttpOk 'http://127.0.0.1:4000/api/health')
    if ($ForceRestartHub -or -not $hubUp) {
        Write-InoveInfo 'Subindo Action Hub (gateway + marketplace + FE)...'
        $hubArgs = @()
        if ($ForceRestartHub) { $hubArgs += '-ForceRestart' }
        & $StartHub @hubArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao subir Action Hub (exit $LASTEXITCODE)."
        }
    } else {
        Write-InoveOk 'Action Hub ja respondendo - mantendo processos atuais'
        Write-InoveInfo '  Gateway http://127.0.0.1:4001/health'
        Write-InoveInfo '  FE      http://127.0.0.1:4000'
    }
} else {
    Write-InoveWarn 'SkipHub: inove sobe sem garantir Action Hub (CMS/billing/tracking podem falhar).'
}

Ensure-NodeOnPath

# --- Backend Flask :5011 (env FLASK_PORT) ---
if (-not $SkipBackend) {
    $venvPython = Join-Path $InoveRoot 'backend\.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw "Venv ausente: $venvPython"
    }

    Write-InoveInfo 'Reiniciando API inove4us...'
    Stop-PortListeners -Ports @(5010, 5011)

    $beOut = Join-Path $DevLogs 'backend.out.log'
    $beErr = Join-Path $DevLogs 'backend.err.log'
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $beOut -Value "`n==== start $stamp ====`n"
    Add-Content -LiteralPath $beErr -Value "`n==== start $stamp ====`n"

    $beDir = Join-Path $InoveRoot 'backend'
    $proc = Start-Process -FilePath $venvPython `
        -ArgumentList @('app.py') `
        -WorkingDirectory $beDir `
        -RedirectStandardOutput $beOut `
        -RedirectStandardError $beErr `
        -PassThru `
        -WindowStyle Hidden

    Write-InoveInfo "backend PID $($proc.Id) -> .dev-logs/backend.*.log"

    $apiUrl = 'http://127.0.0.1:5011/api/health'
    if (-not (Wait-HttpOk -Url $apiUrl -TimeoutSec 45)) {
        $apiUrl = 'http://127.0.0.1:5010/api/health'
        if (-not (Wait-HttpOk -Url $apiUrl -TimeoutSec 15)) {
            Write-InoveErr 'API inove nao subiu. Veja .dev-logs/backend.err.log'
            exit 1
        }
    }
    Write-InoveOk "API OK -> $apiUrl"
}

# --- Frontend Vite :5174 ---
if (-not $SkipFrontend) {
    $feDir = Join-Path $InoveRoot 'frontend'
    if (-not (Test-Path (Join-Path $feDir 'node_modules'))) {
        Write-InoveWarn 'Instalando deps do frontend...'
        Push-Location $feDir
        try { npm install } finally { Pop-Location }
    }

    Write-InoveInfo 'Reiniciando FE inove4us :5174...'
    Stop-PortListeners -Ports @(5174)

    $feOut = Join-Path $DevLogs 'frontend.out.log'
    $feErr = Join-Path $DevLogs 'frontend.err.log'
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $feOut -Value "`n==== start $stamp ====`n"
    Add-Content -LiteralPath $feErr -Value "`n==== start $stamp ====`n"
    $feCmd = 'npm run dev 1>>"' + $feOut + '" 2>>"' + $feErr + '"'
    $null = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList @('/c', $feCmd) `
        -WorkingDirectory $feDir `
        -WindowStyle Hidden

    if (-not (Wait-HttpOk -Url 'http://127.0.0.1:5174/' -TimeoutSec 90)) {
        Write-InoveErr 'Frontend nao subiu. Veja .dev-logs/frontend.err.log'
        exit 1
    }
    Write-InoveOk 'Frontend OK -> http://localhost:5174'
}

Write-Host ''
Write-InoveOk 'inove4us pronto (com Action Hub).'
Write-Host '  inove FE:    http://localhost:5174/acesso'
Write-Host '  inove API:   http://127.0.0.1:5011/api/health'
Write-Host '  Hub FE:      http://localhost:4000'
Write-Host '  Gateway:     http://127.0.0.1:4001/health'
Write-Host '  Marketplace: http://127.0.0.1:4012/api/marketplace/health'
Write-Host '  Hub status:  leaction-platform\scripts\dev\status-hub.ps1'
Write-Host '  Logs inove:  .dev-logs/'
Write-Host ''
