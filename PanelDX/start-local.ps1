<#
=====================================================================
 PanelDX - Inicialização local (Flask + Node)
=====================================================================
 Sobe o ecossistema de desenvolvimento local em duas janelas separadas:
   1. Backend Flask  (porta 5002) + workers IA (Master e Modulador)
   2. Frontend Node  (porta 3000)

 Por padrão LIBERA as portas e FECHA janelas PanelDX anteriores
 antes de abrir novas (evita acumular PowerShell mortos).

 EXEMPLOS
   .\start-local.ps1
   .\start-local.ps1 -Only backend
   .\start-local.ps1 -Only frontend
   .\start-local.ps1 -InstallDeps
   .\start-local.ps1 -OpenBrowser
   .\start-local.ps1 -NoKill   # não encerra processos/janelas existentes
=====================================================================
#>

[CmdletBinding()]
param(
    [ValidateSet("backend", "frontend")]
    [string[]]$Only,

    [switch]$InstallDeps,
    [switch]$OpenBrowser,
    [switch]$NoKill,
    [int]$FlaskPort = 5002,
    [int]$NodePort = 3000,
    [int]$PostgresPort = 5432
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "LeAction_SysF"
$FrontendDir = Join-Path $Root "LeAction_Sys_FE"
$VenvPython = Join-Path $Root "venv_action\Scripts\python.exe"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host ">> $Message" -ForegroundColor Cyan
}

function Test-CommandExists([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-TcpPort([int]$Port) {
    try {
        return (Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded
    } catch {
        return $false
    }
}

function Get-PortListenerIds {
    param([int]$Port)

    $ids = @()
    try {
        $ids += @(
            Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique
        )
    } catch { }

    if ($ids.Count -eq 0) {
        $lines = netstat -ano | Select-String ":$Port\s+.*LISTENING"
        foreach ($line in $lines) {
            $parts = ($line -replace '\s+', ' ').ToString().Trim().Split(' ')
            $pidText = $parts[-1]
            if ($pidText -match '^\d+$') {
                $ids += [int]$pidText
            }
        }
    }

    return $ids |
        Sort-Object -Unique |
        Where-Object {
            $_ -gt 0 -and (Get-Process -Id $_ -ErrorAction SilentlyContinue)
        }
}

function Stop-PortListener {
    param([int]$Port)

    $procIds = Get-PortListenerIds -Port $Port
    if ($procIds.Count -eq 0) {
        Write-Host "  Porta ${Port}: livre." -ForegroundColor DarkGray
        return
    }

    foreach ($procId in $procIds) {
        if ($procId -le 0) { continue }
        try {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { "pid" }
            Write-Host "  Encerrando PID $procId ($name) na porta $Port..." -ForegroundColor Yellow
            # /T mata a árvore (python workers / filhos do node)
            taskkill /PID $procId /F /T 2>$null | Out-Null
            if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Host "  Falha ao encerrar PID $procId na porta ${Port}: $_" -ForegroundColor Red
        }
    }
}

function Stop-PanelDxConsoleWindows {
    $titles = @('PanelDX - Flask', 'PanelDX - Node')
    $shells = @('powershell', 'pwsh', 'WindowsTerminal', 'cmd')
    foreach ($name in $shells) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
            $title = ""
            try { $title = [string]$_.MainWindowTitle } catch { }
            if (-not $title) { return }
            foreach ($prefix in $titles) {
                if ($title.StartsWith($prefix)) {
                    Write-Host "  Fechando janela: $title (PID $($_.Id))" -ForegroundColor Yellow
                    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                    break
                }
            }
        }
    }
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSec = 45,
        [ValidateSet("GET", "POST")]
        [string]$Method = "GET",
        [string]$Body = $null
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $params = @{
                Uri             = $Url
                Method          = $Method
                UseBasicParsing = $true
                TimeoutSec      = 3
            }
            if ($Body) {
                $params.ContentType = "application/json"
                $params.Body = $Body
            }
            $resp = Invoke-WebRequest @params
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

$startBackend = -not $Only -or $Only -contains "backend"
$startFrontend = -not $Only -or $Only -contains "frontend"

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host " PanelDX - Start Local" -ForegroundColor Magenta
Write-Host "=====================================================" -ForegroundColor Magenta

Write-Step "Verificando pré-requisitos..."

if ($startBackend -and -not (Test-CommandExists "python") -and -not (Test-Path $VenvPython)) {
    throw "Python não encontrado no PATH. Instale Python 3 e tente novamente."
}

if ($startFrontend -and -not (Test-CommandExists "node")) {
    throw "Node.js não encontrado no PATH. Instale Node.js e tente novamente."
}

if ($startFrontend -and -not (Test-CommandExists "npm")) {
    throw "npm não encontrado no PATH."
}

if (-not (Test-Path $BackendDir)) {
    throw "Pasta do backend não encontrada: $BackendDir"
}

if (-not (Test-Path $FrontendDir)) {
    throw "Pasta do frontend não encontrada: $FrontendDir"
}

if ($startBackend -and -not (Test-Path (Join-Path $BackendDir ".env"))) {
    Write-Host "AVISO: LeAction_SysF/.env não encontrado. Copie de .env.example e configure o banco." -ForegroundColor Yellow
}

if ($startFrontend -and -not (Test-Path (Join-Path $FrontendDir ".env.development"))) {
    Write-Host "AVISO: LeAction_Sys_FE/.env.development não encontrado." -ForegroundColor Yellow
}

if (-not (Test-TcpPort $PostgresPort)) {
    Write-Host "AVISO: PostgreSQL não responde em 127.0.0.1:$PostgresPort. O Flask pode falhar ao conectar." -ForegroundColor Yellow
}

if (-not $NoKill) {
    Write-Step "Liberando portas e fechando janelas PanelDX anteriores..."
    if ($startBackend) { Stop-PortListener -Port $FlaskPort }
    if ($startFrontend) { Stop-PortListener -Port $NodePort }
    Stop-PanelDxConsoleWindows
    Start-Sleep -Seconds 1
} else {
    if ($startBackend -and (Test-TcpPort $FlaskPort)) {
        Write-Host "AVISO: Porta $FlaskPort já está em uso (-NoKill). Use sem -NoKill para reiniciar limpo." -ForegroundColor Yellow
    }
    if ($startFrontend -and (Test-TcpPort $NodePort)) {
        Write-Host "AVISO: Porta $NodePort já está em uso (-NoKill)." -ForegroundColor Yellow
    }
}

if ($InstallDeps -and $startFrontend) {
    Write-Step "Instalando dependências npm do frontend..."
    Push-Location $FrontendDir
    try {
        npm install
    } finally {
        Pop-Location
    }
}

$pythonCmd = if (Test-Path $VenvPython) { "& '$VenvPython'" } else { "python" }

if ($startBackend) {
    Write-Step "Iniciando Backend Flask (porta $FlaskPort)..."

    $backendCmd = @"
`$Host.UI.RawUI.WindowTitle = 'PanelDX - Flask :$FlaskPort'
Set-Location '$BackendDir'
`$env:PYTHONIOENCODING = 'utf-8'
`$env:PYTHONUTF8 = '1'
`$env:FLASK_PORT = '$FlaskPort'
Write-Host 'PanelDX Backend - Flask + Workers IA' -ForegroundColor Green
Write-Host 'Porta: $FlaskPort' -ForegroundColor Green
Write-Host 'Ctrl+C para encerrar' -ForegroundColor DarkGray
$pythonCmd app.py
"@

    Start-Process powershell.exe -ArgumentList @("-NoExit", "-Command", $backendCmd) | Out-Null
}

if ($startFrontend) {
    Write-Step "Iniciando Frontend Node (porta $NodePort)..."

    $frontendCmd = @"
`$Host.UI.RawUI.WindowTitle = 'PanelDX - Node :$NodePort'
Set-Location '$FrontendDir'
`$env:NODE_ENV = 'development'
`$env:PORT = '$NodePort'
`$env:BACKEND_URL = 'http://localhost:$FlaskPort'
Write-Host 'PanelDX Frontend - Express + EJS' -ForegroundColor Green
Write-Host 'Porta: $NodePort' -ForegroundColor Green
Write-Host 'Backend: http://localhost:$FlaskPort' -ForegroundColor Green
Write-Host 'Ctrl+C para encerrar' -ForegroundColor DarkGray
npm start
"@

    Start-Process powershell.exe -ArgumentList @("-NoExit", "-Command", $frontendCmd) | Out-Null
}

Write-Step "Aguardando serviços ficarem prontos..."

$backendOk = -not $startBackend
$frontendOk = -not $startFrontend

if ($startBackend) {
    $backendOk = Wait-HttpOk `
        -Url "http://127.0.0.1:$FlaskPort/api/check-email" `
        -Method POST `
        -Body '{"email":"healthcheck@test.com"}' `
        -TimeoutSec 60
}

if ($startFrontend) {
    $frontendOk = Wait-HttpOk -Url "http://127.0.0.1:$NodePort/" -TimeoutSec 60
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Magenta
Write-Host " Resumo" -ForegroundColor Magenta
Write-Host "=====================================================" -ForegroundColor Magenta

if ($startBackend) {
    $status = if ($backendOk) { "OK" } else { "AGUARDANDO (verifique a janela do Flask)" }
    $color = if ($backendOk) { "Green" } else { "Yellow" }
    Write-Host (" Backend Flask : http://localhost:{0}  [{1}]" -f $FlaskPort, $status) -ForegroundColor $color
}

if ($startFrontend) {
    $status = if ($frontendOk) { "OK" } else { "AGUARDANDO (verifique a janela do Node)" }
    $color = if ($frontendOk) { "Green" } else { "Yellow" }
    Write-Host (" Frontend Node : http://localhost:{0}  [{1}]" -f $NodePort, $status) -ForegroundColor $color
}

Write-Host ""
Write-Host " Acesse: http://localhost:$NodePort" -ForegroundColor White

if ($OpenBrowser -and $startFrontend) {
    Start-Process "http://localhost:$NodePort"
}

Write-Host ""
Write-Host " Dica: rode .\start-local.ps1 de novo para reiniciar sem acumular janelas." -ForegroundColor DarkGray
Write-Host " Seed (sem abrir serviços): python seed_dev_client.py 4" -ForegroundColor DarkGray
Write-Host ""
