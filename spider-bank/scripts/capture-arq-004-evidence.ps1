#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$evidence = 'C:\Projetos\spider-bank\documents\evidencias\SPIDERBANK-IMP-002'
New-Item -ItemType Directory -Force -Path $evidence | Out-Null

function Save-Json($Name, $Object) {
  ($Object | ConvertTo-Json -Depth 20) | Set-Content -Path (Join-Path $evidence $Name) -Encoding utf8
}

function Invoke-Json([string]$Method, [string]$Url, $Body, $Headers) {
  $params = @{ Uri = $Url; Method = $Method; TimeoutSec = 30 }
  if ($Headers) { $params.Headers = $Headers }
  if ($null -ne $Body) {
    $params.ContentType = 'application/json; charset=utf-8'
    $params.Body = ($Body | ConvertTo-Json -Compress -Depth 10)
  }
  try {
    return Invoke-RestMethod @params
  } catch {
    $raw = ''
    if ($_.Exception.Response) {
      $raw = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream()).ReadToEnd()
    }
    return @{ error = $_.Exception.Message; body = $raw }
  }
}

Save-Json 'mock-health.json' (Invoke-Json GET 'http://127.0.0.1:8096/health' $null $null)
Save-Json 'engine-health.json' (Invoke-Json GET 'http://127.0.0.1:8080/actuator/health' $null $null)
Save-Json 'bff-health.json' (Invoke-Json GET 'http://127.0.0.1:8090/api/health' $null $null)

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

$noCorr = [guid]::NewGuid().ToString()
$noIdem = 'idem-' + [guid]::NewGuid().ToString()
$noSession = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = $noCorr
  idempotencyKey = $noIdem
} @{ 'X-Correlation-ID' = $noCorr; 'Idempotency-Key' = $noIdem }
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

$missing = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = [guid]::NewGuid().ToString()
  idempotencyKey = 'idem-' + [guid]::NewGuid().ToString()
  sessionAssertion = $session.assertion
} $null
Save-Json 'journey-missing-params.json' $missing

$invalid = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = [guid]::NewGuid().ToString()
  idempotencyKey = 'idem-' + [guid]::NewGuid().ToString()
  sessionAssertion = $session.assertion
  principalCents = -1
  termMonths = 12
} $null
Save-Json 'journey-invalid-amount.json' $invalid

$reviewSession = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/demo-session' @{ persona = 'review' } $null
$review = Invoke-Json POST 'http://127.0.0.1:8090/api/credit/journeys' @{
  objectiveConfirmed = $true
  correlationId = [guid]::NewGuid().ToString()
  idempotencyKey = 'idem-' + [guid]::NewGuid().ToString()
  sessionAssertion = $reviewSession.assertion
  principalCents = 1000000
  termMonths = 12
} $null
Save-Json 'journey-human-review.json' $review

$events = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/v1/console/monitor/events' -Headers @{ 'X-Spider-Credential-Ref' = 'local-demo-console' } -TimeoutSec 20
Save-Json 'monitor-events.json' $events
$simulation = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/v1/console/monitor/simulation' -Headers @{ 'X-Spider-Credential-Ref' = 'local-demo-console' } -TimeoutSec 20
Save-Json 'monitor-simulation.json' $simulation

Write-Output ("success=" + $success.status + " decision=" + $success.decisionId + " corr=" + $success.correlationId)
Write-Output ("replay=" + $replay.decisionId)
Write-Output ("noSession=" + $noSession.status)
Write-Output ("pending=" + $pending.status)
Write-Output ("ineligible=" + $ineligible.status)
Write-Output ("missing=" + $missing.status)
Write-Output ("invalidError=" + $invalid.errorCode)
Write-Output ("review=" + $review.status)
$bank = $simulation.satellites | Where-Object { $_.id -eq 'spiderbank' }
Write-Output ("cardAvailable=" + $bank.available + " url=" + $bank.url)
Write-Output ("cardMissing=" + ($bank.missing -join '; '))
