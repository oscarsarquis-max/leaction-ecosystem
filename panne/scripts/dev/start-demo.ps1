#Requires -Version 5.1
# Sobe API e Vite só contra panne_demo. Não lê .env. Não toca no banco panne.
param(
    [string]$DatabaseUrl = $env:PANNE_SEED_DATABASE_URL
)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Tmp = Join-Path $Root ".tmp-demo"
$PidFile = Join-Path $Tmp "pids.json"

function Test-LocalHttp([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Resolve-DemoUrl([string]$Given) {
    if ($Given) { return $Given }
    if ($env:PANNE_ENV -eq "production") { throw "Recusado: ambiente production." }
    $portLine = @(docker port leaction_db 5432 2>$null | Where-Object { $_ })
    if (-not $portLine -or $portLine.Count -lt 1) {
        throw "Informe PANNE_SEED_DATABASE_URL com o banco panne_demo."
    }
    $first = [string]$portLine[0]
    if ($first -notmatch ":(\d+)\s*$") {
        throw "Não foi possível ler a porta do container leaction_db."
    }
    $port = $Matches[1]
    $user = (docker exec leaction_db printenv POSTGRES_USER).Trim()
    $pass = (docker exec leaction_db printenv POSTGRES_PASSWORD).Trim()
    if (-not $user -or -not $pass) {
        throw "Informe PANNE_SEED_DATABASE_URL com o banco panne_demo."
    }
    return "postgresql+asyncpg://${user}:${pass}@127.0.0.1:${port}/panne_demo"
}

if ($env:PANNE_ENV -eq "production") {
    throw "Recusado: ambiente production."
}

$Resolved = Resolve-DemoUrl $DatabaseUrl
if ($Resolved -match "/panne(\?|$)") {
    throw "Recusado: banco lógico panne."
}
if ($Resolved -notmatch "_demo(\?|$)") {
    throw "Recusado: start-demo exige sufixo _demo."
}

$env:PANNE_ENV = "demo"
$env:PANNE_DATABASE_URL = $Resolved
$env:PANNE_RUNTIME_DATABASE_URL = $Resolved
$env:PANNE_AUTH_VERIFIER = "fake"
$env:PANNE_FAKE_ISSUER = "https://panne.local/fake"
$env:PANNE_AI_GATEWAY = "fake"
$env:VITE_DEMO_MODE = "1"
$env:PANNE_SEED_DATABASE_URL = $Resolved

$Py = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
$NodeDir = Join-Path (Split-Path $Root -Parent) ".tools\node"
if (Test-Path (Join-Path $NodeDir "npm.cmd")) {
    $env:Path = "$NodeDir;$env:Path"
}

New-Item -ItemType Directory -Force -Path $Tmp | Out-Null

$apiUp = Test-LocalHttp "http://127.0.0.1:5080/health"
$feUp = Test-LocalHttp "http://127.0.0.1:5180/"
if (-not $apiUp) {
    $api = Start-Process -FilePath $Py -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "5080") -WorkingDirectory $Backend -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Tmp "api.out") -RedirectStandardError (Join-Path $Tmp "api.err")
} else {
    $api = $null
}
if (-not $feUp) {
    $fe = Start-Process -FilePath "npm" -ArgumentList @("run", "dev") -WorkingDirectory $Frontend -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Tmp "fe.out") -RedirectStandardError (Join-Path $Tmp "fe.err")
} else {
    $fe = $null
}

@{
    api = if ($api) { $api.Id } else { $null }
    fe = if ($fe) { $fe.Id } else { $null }
    started_at = (Get-Date).ToString("s")
} | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

$deadline = (Get-Date).AddSeconds(60)
do {
    $apiOk = Test-LocalHttp "http://127.0.0.1:5080/health"
    $readyOk = Test-LocalHttp "http://127.0.0.1:5080/ready"
    $feOk = Test-LocalHttp "http://127.0.0.1:5180/"
    if ($apiOk -and $readyOk -and $feOk) { break }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)

if (-not $apiOk -or -not $readyOk -or -not $feOk) {
    throw "Demo não respondeu a tempo. API=$apiOk ready=$readyOk FE=$feOk. Veja $Tmp."
}

Write-Host "Ambiente de demonstração."
Write-Host "Alvo lógico: panne_demo"
Write-Host "Aplicação: http://127.0.0.1:5180/entrar"
Write-Host "Saúde da API: http://127.0.0.1:5080/health"
Write-Host "Prontidão: http://127.0.0.1:5080/ready"
Write-Host "Para encerrar: powershell -File `"$PSScriptRoot\stop-demo.ps1`""
