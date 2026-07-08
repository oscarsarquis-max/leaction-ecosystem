<#
 Chamelleon — reinicia backend Flask + frontend Vite.
 Encerra processos nas portas configuradas e executa start-local.ps1.

 Uso (obrigatorio o prefixo .\ no PowerShell):
   .\restart-local.ps1

 Portas customizadas:
   $env:FLASK_PORT = "5010"; $env:VITE_PORT = "5173"; .\restart-local.ps1
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$FlaskPort = if ($env:FLASK_PORT) { [int]$env:FLASK_PORT } else { 5010 }
$NodePort = if ($env:VITE_PORT) { [int]$env:VITE_PORT } else { 5173 }

function Get-PortListenerIds {
    param([int]$Port)

    $ids = @()
    try {
        $ids += @(
            Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique
        )
    } catch {
        # fallback sem privilegios elevados
    }

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
            taskkill /PID $procId /F /T 2>$null | Out-Null
            if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Host "  Falha ao encerrar PID $procId na porta ${Port}: $_" -ForegroundColor Red
        }
    }
}

function Wait-PortFree {
    param(
        [int]$Port,
        [int]$TimeoutSec = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Get-PortListenerIds -Port $Port).Count -eq 0) {
            return $true
        }
        Start-Sleep -Milliseconds 400
    }
    return $false
}

Write-Host ""
Write-Host ">> Reiniciando Chamelleon..." -ForegroundColor Cyan
Write-Host ">> Liberando portas $FlaskPort (backend) e $NodePort (frontend)..." -ForegroundColor Cyan

Stop-PortListener -Port $FlaskPort
Stop-PortListener -Port $NodePort

$backendFree = Wait-PortFree -Port $FlaskPort
$frontendFree = Wait-PortFree -Port $NodePort

if (-not $backendFree) {
    Write-Host "AVISO: porta $FlaskPort ainda ocupada. Tentando encerrar novamente..." -ForegroundColor Yellow
    Stop-PortListener -Port $FlaskPort
    $backendFree = Wait-PortFree -Port $FlaskPort -TimeoutSec 10
}
if (-not $frontendFree) {
    Write-Host "AVISO: porta $NodePort ainda ocupada. Tentando encerrar novamente..." -ForegroundColor Yellow
    Stop-PortListener -Port $NodePort
    $frontendFree = Wait-PortFree -Port $NodePort -TimeoutSec 10
}

if (-not $backendFree -or -not $frontendFree) {
    Write-Host ""
    Write-Host "ERRO: nao foi possivel liberar todas as portas." -ForegroundColor Red
    if (-not $backendFree) { Write-Host "  - Backend: porta $FlaskPort" -ForegroundColor Red }
    if (-not $frontendFree) { Write-Host "  - Frontend: porta $NodePort" -ForegroundColor Red }
    Write-Host "  Feche manualmente as janelas do Flask/Vite ou encerre os PIDs no Gerenciador de Tarefas." -ForegroundColor Yellow
    exit 1
}

Start-Sleep -Seconds 1

$startScript = Join-Path $Root "start-local.ps1"
if (-not (Test-Path $startScript)) {
    Write-Host "ERRO: start-local.ps1 nao encontrado em $Root" -ForegroundColor Red
    exit 1
}

& $startScript
