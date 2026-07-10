<#
 Chamelleon — sobe backend Flask + frontend Vite em janelas separadas.
 Uso: .\start-local.ps1
#>

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

function Read-DotEnvValue([string]$FilePath, [string]$Key) {
    if (-not (Test-Path $FilePath)) { return $null }
    foreach ($line in Get-Content $FilePath) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.+?)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

# Porta do backend: prioriza backend\.env (evita FLASK_PORT=5002 de outro projeto no shell)
$EnvFile = Join-Path $BackendDir ".env"
$FlaskPort = Read-DotEnvValue $EnvFile "FLASK_PORT"
if (-not $FlaskPort) { $FlaskPort = $env:FLASK_PORT }
if (-not $FlaskPort) { $FlaskPort = "5010" }
$NodePort = if ($env:VITE_PORT) { $env:VITE_PORT } else { "5173" }

function Test-Port([int]$Port) {
    $connections = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if ($connections.Count -eq 0) { return $false }
    $live = $connections.OwningProcess | Sort-Object -Unique | Where-Object {
        $_ -gt 0 -and (Get-Process -Id $_ -ErrorAction SilentlyContinue)
    }
    return $live.Count -gt 0
}

if (-not (Test-Path $VenvPython)) {
    Write-Host ">> Criando venv em backend\.venv ..." -ForegroundColor Cyan
    python -m venv (Join-Path $BackendDir ".venv")
    & $VenvPython -m pip install -r (Join-Path $BackendDir "requirements.txt")
}

if (Test-Port $FlaskPort) {
    Write-Host "AVISO: porta $FlaskPort ja em uso." -ForegroundColor Yellow
    $pids = @(Get-NetTCPConnection -LocalPort $FlaskPort -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        Where-Object { $_ -gt 0 })
    foreach ($procId in $pids) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  -> PID $($proc.Id) ($($proc.ProcessName))" -ForegroundColor DarkYellow
        }
    }
    Write-Host "  Encerre esse processo ou altere FLASK_PORT em backend\.env" -ForegroundColor Yellow
}
if (Test-Port $NodePort) {
    Write-Host "AVISO: porta $NodePort ja em uso. O Vite pode escolher outra porta." -ForegroundColor Yellow
}

$python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

Write-Host ">> Backend Flask (porta $FlaskPort)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$BackendDir'; `$env:PYTHONPATH='$BackendDir'; `$env:FLASK_PORT='$FlaskPort'; Remove-Item Env:PORT -ErrorAction SilentlyContinue; & '$python' run.py"
)

Start-Sleep -Seconds 2

$healthUrl = "http://127.0.0.1:$FlaskPort/api/health"
$backendOk = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $backendOk = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $backendOk) {
    Write-Host ""
    Write-Host "ERRO: backend nao respondeu em $healthUrl." -ForegroundColor Red
    Write-Host "  - Verifique a janela do Flask (erros de import/DB)." -ForegroundColor Yellow
    Write-Host "  - Se a porta $FlaskPort estiver ocupada sem servidor, encerre o processo e rode de novo." -ForegroundColor Yellow
    Write-Host "  - Login e cadastro retornarao HTTP 500 ate o backend subir." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ">> Frontend Vite (porta $NodePort)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$FrontendDir'; npm run dev -- --port $NodePort --host 127.0.0.1"
)

Write-Host ""
Write-Host "Chamelleon iniciado:" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:$NodePort"
Write-Host "  Backend:  http://localhost:$FlaskPort"
