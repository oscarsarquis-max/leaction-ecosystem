# Reinicia só a engine Spider já identificada (local-demo) com borda FORWARD :8098.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\_lib.ps1")
$afRoot = Get-ActionFinanceRoot
$secrets = Read-ActionFinanceEnvFile (Join-Path $afRoot ".local\secrets.env")
$spiderRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\spider")
$logDir = Join-Path $afRoot "documents\reviews\evidence\prm-009-continuidade-001\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$listener = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    if ($cim.CommandLine -notmatch "SpiderOrchestratorApplication") {
        throw "Porta 8080 não é a engine Spider local. Recusando parar pid=$($listener.OwningProcess)"
    }
    Stop-Process -Id $listener.OwningProcess -ErrorAction Stop
    Write-Output "STOPPED_SPIDER pid=$($listener.OwningProcess)"
}

$env:SPIDER_ACTIONHUB_PAY_EDGE_URL = "http://127.0.0.1:8098"
$env:SPIDER_ACTIONHUB_PAY_EDGE_SECRET = "prm009-edge-forward"
$env:SPIDER_ACTIONFINANCE_APPLICATION_SECRET = $secrets.ACTIONFINANCE_SPIDER_SECRET
$mvn = Join-Path $spiderRoot ".tools\apache-maven-3.9.16\bin\mvn.cmd"
if (-not (Test-Path $mvn)) { $mvn = "mvn" }
$proc = Start-Process -FilePath $mvn -ArgumentList @("spring-boot:run", "-Dspring-boot.run.profiles=local-demo") `
    -WorkingDirectory (Join-Path $spiderRoot "backend") `
    -RedirectStandardOutput (Join-Path $logDir "spider-engine.out.log") `
    -RedirectStandardError (Join-Path $logDir "spider-engine.err.log") `
    -PassThru -WindowStyle Hidden
Write-Output "STARTED_SPIDER wrapper_pid=$($proc.Id)"
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        $h = Invoke-RestMethod "http://127.0.0.1:8080/actuator/health" -TimeoutSec 2
        if ($h.status -eq "UP") { $ready = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) { throw "Spider engine não respondeu em :8080" }
Write-Output "SPIDER_UP http://127.0.0.1:8080"
