#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$evidence = Join-Path $root 'documents\evidencias\SPIDERBANK-IMP-002'
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
$logDir = Join-Path $PSScriptRoot '.logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

. (Join-Path $PSScriptRoot 'setup-local-secrets.ps1')
. (Join-Path $PSScriptRoot '_load-local-secrets.ps1')
Get-Content 'C:\Projetos\segsense\scripts\.mvp-secrets.env' | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
  $parts = $_.Split('=', 2)
  if ($parts.Count -eq 2) { Set-Item -Path ("Env:" + $parts[0]) -Value $parts[1] }
}
$env:SPIDER_CREDIT_MOCK_BASE_URL = 'http://127.0.0.1:8096'
$env:SPIDER_SPIDERBANK_PRODUCT_URL = 'http://127.0.0.1:5190/'
$env:SPIDER_SPIDERBANK_BFF_URL = 'http://127.0.0.1:8090/api/health'
$env:PORT = '8096'
$env:SPIDERBANK_BACKEND_PORT = '8090'
$env:SPIDERBANK_FRONTEND_ORIGIN = 'http://127.0.0.1:5190,http://localhost:5190'
$env:VITE_DEV_PORT = '5190'
$env:SPIDERBANK_BFF_URL = 'http://127.0.0.1:8090'
$env:SPIDERBANK_SPIDER_DEMO_BASE_URL = 'http://127.0.0.1:8080'

function Test-Listen([int]$Port) {
  return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-Http([string]$Url, [int]$Seconds, [string]$Name) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  $last = $null
  while ((Get-Date) -lt $deadline) {
    try {
      $req = [System.Net.HttpWebRequest]::Create($Url)
      $req.Timeout = 3000
      $req.ProtocolVersion = [Version]'1.1'
      $resp = $req.GetResponse()
      $code = [int]$resp.StatusCode
      $resp.Close()
      if ($code -ge 200 -and $code -lt 500) { return }
    } catch { $last = $_ }
    Start-Sleep -Seconds 2
  }
  throw "Timed out waiting for $Name. $last"
}

function Save-Json($Name, $Object) {
  ($Object | ConvertTo-Json -Depth 20) | Set-Content -Path (Join-Path $evidence $Name) -Encoding utf8
}

function Invoke-Json([string]$Method, [string]$Url, $Body, $Headers) {
  $params = @{ Uri = $Url; Method = $Method; TimeoutSec = 20 }
  if ($Headers) { $params.Headers = $Headers }
  if ($null -ne $Body) {
    $params.ContentType = 'application/json; charset=utf-8'
    $params.Body = ($Body | ConvertTo-Json -Compress -Depth 10)
  }
  return Invoke-RestMethod @params
}

Write-Output 'Loaded secrets without printing them.'
Write-Output "assertionConfigured=$([bool]$env:SPIDER_SPIDERBANK_CUSTOMER_ASSERTION_SECRET) creditConfigured=$([bool]$env:SPIDER_CREDIT_MOCK_CREDENTIAL)"

if (-not (Test-Listen 8096)) {
  $mock = Start-Process -FilePath 'node.exe' -ArgumentList @('server.js') -WorkingDirectory 'C:\Projetos\mock-sistemas-credito' -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'credit-mock.out.log') -RedirectStandardError (Join-Path $logDir 'credit-mock.err.log')
  Write-Output "started credit mock pid=$($mock.Id)"
} else {
  Write-Output 'credit mock already listening on 8096'
}

$engineMaven = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'SpiderOrchestratorApplication|spring-boot.run.profiles=local-demo' -and $_.CommandLine -match 'maven.multiModuleProjectDirectory=C:\\Projetos\\spider\\backend' }
$engineJava = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'br.com.banco.spider.SpiderOrchestratorApplication' }
foreach ($proc in @($engineJava) + @($engineMaven)) {
  if ($proc) {
    Write-Output "stopping engine pid=$($proc.ProcessId) to load credit-demo registry"
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
  }
}
Start-Sleep -Seconds 2

$bffMaven = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'spider-bank\\backend' -and $_.CommandLine -match 'spring-boot:run' }
$bffJava = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'br.com.spiderbank.SpiderBankApplication' }
foreach ($proc in @($bffJava) + @($bffMaven)) {
  if ($proc) {
    Write-Output "stopping BFF pid=$($proc.ProcessId) to load session and parameters"
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
  }
}
$fe = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'spider-bank\\frontend' -and $_.CommandLine -match 'vite' }
foreach ($proc in $fe) {
  Write-Output "stopping frontend pid=$($proc.ProcessId)"
  Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

$mvn = 'C:\Projetos\spider\.tools\apache-maven-3.9.16\bin\mvn.cmd'
$engine = Start-Process -FilePath $mvn -ArgumentList @('-q', 'spring-boot:run', '-Dspring-boot.run.profiles=local-demo') -WorkingDirectory 'C:\Projetos\spider\backend' -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'engine.out.log') -RedirectStandardError (Join-Path $logDir 'engine.err.log')
Write-Output "started engine launcherPid=$($engine.Id)"
$bff = Start-Process -FilePath $mvn -ArgumentList @('-q', 'spring-boot:run') -WorkingDirectory 'C:\Projetos\spider-bank\backend' -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'bff.out.log') -RedirectStandardError (Join-Path $logDir 'bff.err.log')
Write-Output "started BFF launcherPid=$($bff.Id)"
if (-not (Test-Listen 5190)) {
  $front = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run', 'dev') -WorkingDirectory 'C:\Projetos\spider-bank\frontend' -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'fe.out.log') -RedirectStandardError (Join-Path $logDir 'fe.err.log')
  Write-Output "started frontend launcherPid=$($front.Id)"
} else {
  Write-Output 'frontend still listening on 5190'
}

Wait-Http 'http://127.0.0.1:8096/health' 30 'credit mock'
Wait-Http 'http://127.0.0.1:8080/actuator/health' 180 'Spider engine'
Wait-Http 'http://127.0.0.1:8090/api/health' 120 'SpiderBank BFF'
Wait-Http 'http://127.0.0.1:5190/' 90 'SpiderBank frontend'
Write-Output 'services ready'

$mockHealth = Invoke-Json GET 'http://127.0.0.1:8096/health' $null $null
Save-Json 'mock-health.json' $mockHealth
$engineHealth = Invoke-Json GET 'http://127.0.0.1:8080/actuator/health' $null $null
Save-Json 'engine-health.json' $engineHealth
$bffHealth = Invoke-Json GET 'http://127.0.0.1:8090/api/health' $null $null
Save-Json 'bff-health.json' $bffHealth

$session = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/demo-session' @{ persona = 'ok' } $null
Save-Json 'demo-session.json' $session
$corr = [guid]::NewGuid().ToString()
$idem = 'idem-' + [guid]::NewGuid().ToString()
$success = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = $corr
  idempotencyKey = $idem
  sessionAssertion = $session.assertion
  principalCents = 1000000
  termMonths = 12
} @{ 'X-Correlation-ID' = $corr; 'Idempotency-Key' = $idem }
Save-Json 'journey-success.json' $success

$replay = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = $corr
  idempotencyKey = $idem
  sessionAssertion = $session.assertion
  principalCents = 1000000
  termMonths = 12
} @{ 'X-Correlation-ID' = $corr; 'Idempotency-Key' = $idem }
Save-Json 'journey-replay.json' $replay

$noSessionCorr = [guid]::NewGuid().ToString()
$noSession = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = $noSessionCorr
  idempotencyKey = 'idem-' + [guid]::NewGuid().ToString()
} @{ 'X-Correlation-ID' = $noSessionCorr; 'Idempotency-Key' = ('idem-' + [guid]::NewGuid().ToString()) }
Save-Json 'journey-no-session.json' $noSession

$pendingSession = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/demo-session' @{ persona = 'pending-registration' } $null
$pending = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = [guid]::NewGuid().ToString()
  idempotencyKey = 'idem-' + [guid]::NewGuid().ToString()
  sessionAssertion = $pendingSession.assertion
  principalCents = 1000000
  termMonths = 12
} $null
Save-Json 'journey-pending-registration.json' $pending

$missing = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = [guid]::NewGuid().ToString()
  idempotencyKey = 'idem-' + [guid]::NewGuid().ToString()
  sessionAssertion = $session.assertion
} $null
Save-Json 'journey-missing-params.json' $missing

try {
  Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
    objectiveConfirmed = $true
    correlationId = [guid]::NewGuid().ToString()
    idempotencyKey = 'idem-' + [guid]::NewGuid().ToString()
    sessionAssertion = $session.assertion
    principalCents = -1
    termMonths = 12
  } $null
  throw 'expected invalid amount to fail'
} catch {
  Save-Json 'journey-invalid-amount.json' @{ message = $_.Exception.Message }
}

$ineligibleSession = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/demo-session' @{ persona = 'ineligible' } $null
$ineligible = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = [guid]::NewGuid().ToString()
  idempotencyKey = 'idem-' + [guid]::NewGuid().ToString()
  sessionAssertion = $ineligibleSession.assertion
  principalCents = 1000000
  termMonths = 12
} $null
Save-Json 'journey-ineligible.json' $ineligible

$events = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/v1/console/monitor/events' -Headers @{ 'X-Spider-Credential-Ref' = 'local-demo-console' } -TimeoutSec 20
Save-Json 'monitor-success-events.json' $events
$simulation = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/v1/console/monitor/simulation' -Headers @{ 'X-Spider-Credential-Ref' = 'local-demo-console' } -TimeoutSec 20
Save-Json 'monitor-simulation.json' $simulation

Write-Output ("successStatus=" + $success.status)
Write-Output ("successDecision=" + $success.decisionId)
Write-Output ("successCorrelation=" + $success.correlationId)
Write-Output ("replayDecision=" + $replay.decisionId)
Write-Output ("noSessionStatus=" + $noSession.status)
Write-Output ("pendingStatus=" + $pending.status)
Write-Output ("missingStatus=" + $missing.status)
Write-Output ("ineligibleStatus=" + $ineligible.status)
Write-Output ("cardAvailable=" + (($simulation.satellites | Where-Object { $_.id -eq 'spiderbank' }).available))
Write-Output ("cardUrl=" + (($simulation.satellites | Where-Object { $_.id -eq 'spiderbank' }).url))
Write-Output 'proof files written'
