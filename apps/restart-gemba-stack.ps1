<#
.SYNOPSIS
  Reinicia o stack Chamelleon + Diário de Obra (Gemba) em ambiente local.

.DESCRIPTION
  Encerra processos nas portas:
    - 5010  Chamelleon API
    - 5173  Chamelleon Web (Vite)
    - 6010  Diário de Obra API
    - 6173  Diário de Obra Web (Vite)

  Em seguida executa start-local.ps1 (Chamelleon) e start-diario-obra.ps1.

.EXAMPLE
  .\restart-gemba-stack.ps1

.EXAMPLE
  # Portas customizadas (opcional)
  $env:FLASK_PORT = "5010"
  $env:VITE_PORT = "5173"
  $env:PORT = "6010"
  .\restart-gemba-stack.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$AppsRoot = $PSScriptRoot
$RepoRoot = Split-Path -Parent $AppsRoot
$ChamelleonRoot = Join-Path $RepoRoot "chamelleon"

$FlaskPort = if ($env:FLASK_PORT) { [int]$env:FLASK_PORT } else { 5010 }
$ChamelleonWebPort = if ($env:VITE_PORT) { [int]$env:VITE_PORT } else { 5173 }
$DiarioApiPort = if ($env:PORT) { [int]$env:PORT } else { 6010 }
$DiarioWebPort = if ($env:DIARIO_WEB_PORT) { [int]$env:DIARIO_WEB_PORT } else { 6173 }

$Ports = @($FlaskPort, $ChamelleonWebPort, $DiarioApiPort, $DiarioWebPort)

$DevShellMarkers = @(
    'chamelleon\backend',
    'chamelleon\frontend',
    'diario-obra-api',
    'diario-obra-web',
    'run.py',
    'npm run dev'
)

function Get-ProcessParentChain {
    param([int]$ProcessId)

    $chain = @()
    $current = $ProcessId
    while ($current -gt 0) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$current" -ErrorAction SilentlyContinue
        if (-not $proc) { break }
        $chain += $proc
        $current = $proc.ParentProcessId
    }
    return $chain
}

function Get-HostShellPid {
    param([int]$ProcessId)

    foreach ($proc in (Get-ProcessParentChain -ProcessId $ProcessId)) {
        $name = ($proc.Name -replace '\.exe$', '').ToLower()
        if ($name -in @('powershell', 'pwsh') -and $proc.ProcessId -ne $PID) {
            return $proc.ProcessId
        }
    }
    return $null
}

function Stop-DevPowerShellWindows {
    param(
        [int[]]$Ports,
        [string[]]$Markers
    )

    $hostShellPids = @()
    foreach ($port in $Ports) {
        foreach ($procId in (Get-PortListenerIds -Port $port)) {
            $hostShellPid = Get-HostShellPid -ProcessId $procId
            if ($hostShellPid) {
                $hostShellPids += $hostShellPid
            }
        }
    }

    foreach ($hostShellPid in ($hostShellPids | Sort-Object -Unique)) {
        if ($hostShellPid -eq $PID) { continue }
        Write-Host "  Fechando janela PowerShell PID $hostShellPid..." -ForegroundColor Yellow
        taskkill /PID $hostShellPid /F /T 2>$null | Out-Null
        if (Get-Process -Id $hostShellPid -ErrorAction SilentlyContinue) {
            Stop-Process -Id $hostShellPid -Force -ErrorAction SilentlyContinue
        }
    }

    foreach ($proc in (Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction SilentlyContinue)) {
        if ($proc.ProcessId -eq $PID) { continue }
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }
        $matched = $false
        foreach ($marker in $Markers) {
            if ($cmd -like "*$marker*") {
                $matched = $true
                break
            }
        }
        if (-not $matched) { continue }
        Write-Host "  Fechando janela PowerShell orfa PID $($proc.ProcessId)..." -ForegroundColor Yellow
        taskkill /PID $proc.ProcessId /F /T 2>$null | Out-Null
        if (Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue) {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
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
Write-Host ">> Reiniciando stack Chamelleon + Diario de Obra (Gemba)..." -ForegroundColor Cyan
Write-Host ">> Fechando janelas PowerShell dos servicos..." -ForegroundColor Cyan
Stop-DevPowerShellWindows -Ports $Ports -Markers $DevShellMarkers

Write-Host ">> Liberando portas: $($Ports -join ', ')" -ForegroundColor Cyan

foreach ($port in $Ports) {
    Stop-PortListener -Port $port
}

$blocked = @()
foreach ($port in $Ports) {
    if (-not (Wait-PortFree -Port $port)) {
        Stop-PortListener -Port $port
        if (-not (Wait-PortFree -Port $port -TimeoutSec 10)) {
            $blocked += $port
        }
    }
}

if ($blocked.Count -gt 0) {
    Write-Host ""
    Write-Host "ERRO: nao foi possivel liberar as portas: $($blocked -join ', ')" -ForegroundColor Red
    Write-Host "  Feche manualmente as janelas Flask/Vite ou encerre os PIDs no Gerenciador de Tarefas." -ForegroundColor Yellow
    exit 1
}

Stop-DevPowerShellWindows -Ports $Ports -Markers $DevShellMarkers

Start-Sleep -Seconds 1

$chamelleonStart = Join-Path $ChamelleonRoot "start-local.ps1"
$diarioStart = Join-Path $AppsRoot "start-diario-obra.ps1"

if (-not (Test-Path $chamelleonStart)) {
    Write-Host "ERRO: Chamelleon nao encontrado em $ChamelleonRoot" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $diarioStart)) {
    Write-Host "ERRO: start-diario-obra.ps1 nao encontrado em $AppsRoot" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host ">> Subindo Chamelleon..." -ForegroundColor Green
& $chamelleonStart

Start-Sleep -Seconds 2

Write-Host ""
Write-Host ">> Subindo Diario de Obra..." -ForegroundColor Green
& $diarioStart

Write-Host ""
Write-Host "== Stack reiniciado ==" -ForegroundColor Green
Write-Host "  Chamelleon:     http://localhost:$ChamelleonWebPort  (API :$FlaskPort)" -ForegroundColor White
Write-Host "  Diario de Obra: http://localhost:$DiarioWebPort  (API :$DiarioApiPort)" -ForegroundColor White
Write-Host "  Portal:         http://localhost:$ChamelleonWebPort/portal" -ForegroundColor DarkGray
Write-Host ""
