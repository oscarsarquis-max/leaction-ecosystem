# Isolated PROVIDER_UNAVAILABLE proof. Does not stop the meeting mock/Spider/SegSense.
# Starts a throwaway Spider on 18080 whose provider URL points at a closed port.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_load-mvp-secrets.ps1')
. (Join-Path $PSScriptRoot '_mvp-process-safety.ps1')
. (Join-Path $PSScriptRoot '_mvp-preflight.ps1')

function New-IsolatedCanonicalBody($Objective, $Correlation, $Key) {
  @{
    contractVersion = '1.0'
    messageId = 'msg-' + [guid]::NewGuid().ToString()
    correlationId = $Correlation
    satelliteId = 'segsense'
    satelliteRole = 'EXPERIENCE'
    interactionType = 'REQUEST_DECISION'
    createdAt = '2026-09-13T12:00:00Z'
    idempotencyKey = $Key
    purpose = 'INSURANCE_PROTECTION_ASSESSMENT'
    objective = @{
      text = $Objective
      origin = 'SATELLITE_GOVERNED'
      declaredAt = '2026-09-13T12:00:00Z'
    }
    context = @{
      snapshot = @{
        schemaVersion = '1.0'
        classification = 'INTERNAL'
        nonPersonal = $true
        provenance = @{
          sourceType = 'SATELLITE_GOVERNED'
          sourceId = 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1'
          sourceTimestamp = '2026-09-13T12:00:00Z'
          captureMethod = 'SERVER_REGISTRY'
          trustLevel = 'GOVERNED'
        }
        attributes = @{
          channel = 'SEGSENSE_PUBLIC_DEMO'
          editorialPieceVersion = 'demo-editorial-v1'
          purposeVersion = 'demo-purpose-v1'
        }
      }
    }
    dataClassification = 'INTERNAL'
    responseChannel = 'SYNC'
    metadata = @{}
  } | ConvertTo-Json -Depth 8
}

$isolatedPort = 18080
$closedProviderPort = 18765
$marker = 'segsense.isolated.proof=' + [guid]::NewGuid().ToString('N')
$spiderDir = 'C:\Projetos\spider\backend'
$logDir = Join-Path $PSScriptRoot '.mvp-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outLog = Join-Path $logDir 'isolated-spider.out.log'
$errLog = Join-Path $logDir 'isolated-spider.err.log'

$meetingMockPid = Get-MvpListenPid -Port 8095
$meetingSpiderPid = Get-MvpListenPid -Port 8080
$meetingBffPid = Get-MvpListenPid -Port 8088
if (-not $meetingMockPid -or -not $meetingSpiderPid -or -not $meetingBffPid) {
  Write-Output 'providerUnavailableProof=NÃO COMPROVADO'
  Write-Output 'providerUnavailableReason=meeting stack is not fully listening; isolated proof requires the three meeting processes to remain identifiable'
  return
}

if (Get-MvpListenPid -Port $isolatedPort) {
  Write-Output 'providerUnavailableProof=NÃO COMPROVADO'
  Write-Output "providerUnavailableReason=port $isolatedPort already in use; refusing to start a second Spider there"
  return
}
if (Get-MvpListenPid -Port $closedProviderPort) {
  Write-Output 'providerUnavailableProof=NÃO COMPROVADO'
  Write-Output "providerUnavailableReason=closed-provider port $closedProviderPort is unexpectedly listening"
  return
}

Write-Output ("meetingMockPid=$meetingMockPid meetingSpiderPid=$meetingSpiderPid meetingBffPid=$meetingBffPid")
Write-Output ("isolatedProviderTarget=http://127.0.0.1:$closedProviderPort (not listening)")

$startedAfter = Get-Date
$previousMockUrl = $env:SPIDER_SEGSENSE_MOCK_BASE_URL
$env:SPIDER_SEGSENSE_MOCK_BASE_URL = "http://127.0.0.1:$closedProviderPort"
$argList = @(
  '/c',
  "mvn -q spring-boot:run -Dspring-boot.run.profiles=local-demo -Dspring-boot.run.arguments=--server.port=$isolatedPort -Dspring-boot.run.jvmArguments=-D$marker"
)
$isolated = Start-Process -FilePath 'cmd.exe' -ArgumentList $argList -WorkingDirectory $spiderDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
Write-Output ("isolatedLauncherPid=$($isolated.Id)")

$isolatedJava = $null
$deadline = (Get-Date).AddSeconds(120)
$ready = $false
while ((Get-Date) -lt $deadline) {
  $listen = Get-MvpListenPid -Port $isolatedPort
  if ($listen) {
    $isolatedJava = $listen
    try {
      $health = Invoke-RestMethod "http://127.0.0.1:$isolatedPort/actuator/health" -TimeoutSec 3
      if ($health.status -eq 'UP') { $ready = $true; break }
    } catch { }
  }
  Start-Sleep -Seconds 2
}

try {
  if (-not $ready -or -not $isolatedJava) {
    Write-Output 'providerUnavailableProof=NÃO COMPROVADO'
    Write-Output 'providerUnavailableReason=isolated Spider did not become healthy in time'
    return
  }

  $afterMock = Get-MvpListenPid -Port 8095
  $afterSpider = Get-MvpListenPid -Port 8080
  if ($afterMock -ne $meetingMockPid -or $afterSpider -ne $meetingSpiderPid) {
    Write-Output 'providerUnavailableProof=NÃO COMPROVADO'
    Write-Output 'providerUnavailableReason=meeting listeners changed while starting isolated Spider; aborting without canonical call'
    return
  }

  $owned = Test-MvpOwnedProcess -ProcessId $isolatedJava -ExpectedPort $isolatedPort -ExpectedName 'java.exe' -CommandLineMustContain $marker -StartedAfter $startedAfter
  if (-not $owned.Owned) {
    Write-Output 'providerUnavailableProof=NÃO COMPROVADO'
    Write-Output ("providerUnavailableReason=isolated listener is not the JVM we launched: $($owned.Reason)")
    return
  }

  if (Get-MvpListenPid -Port $closedProviderPort) {
    Write-Output 'providerUnavailableProof=NÃO COMPROVADO'
    Write-Output 'providerUnavailableReason=provider target became reachable; cannot claim unavailability'
    return
  }
  Write-Output "isolatedProviderUnreachable=true closedPort=$closedProviderPort"

  $secret = $env:SPIDER_SEGSENSE_DEMO_APPLICATION_SECRET
  $corr = [guid]::NewGuid().ToString()
  $key = [guid]::NewGuid().ToString()
  $headers = @{
    'X-Spider-Satellite-Id' = 'segsense'
    'X-Spider-Satellite-Secret' = $secret
    'X-Correlation-ID' = $corr
    'Idempotency-Key' = $key
  }
  $down = Invoke-RestMethod "http://127.0.0.1:$isolatedPort/v1/satellites/interactions" -Method POST -Headers $headers -ContentType 'application/json' -Body (New-IsolatedCanonicalBody 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS' $corr $key)
  $reference = $null
  if ($down.resultSummary) { $reference = $down.resultSummary.providerReference }
  $itemCount = 0
  if ($down.resultSummary -and $down.resultSummary.items) { $itemCount = @($down.resultSummary.items).Count }

  Write-Output ("isolatedStatus=$($down.status) decisionId=$($down.decisionId) capabilityId=$($down.capabilityId) providerRequestId=$($down.providerRequestId) providerReference=$reference itemCount=$itemCount")
  Write-Output ("isolatedExplanation=$($down.explanation)")

  $ok = ($down.status -eq 'PROVIDER_UNAVAILABLE') -and [string]::IsNullOrWhiteSpace([string]$reference) -and [string]::IsNullOrWhiteSpace([string]$down.capabilityId) -and ($itemCount -eq 0)
  if ($ok) {
    Write-Output 'providerUnavailableProof=COMPROVADO'
    Write-Output 'providerUnavailableMeetingStack=untouched'
  } else {
    Write-Output 'providerUnavailableProof=NÃO COMPROVADO'
    Write-Output 'providerUnavailableReason=isolated canonical response was not PROVIDER_UNAVAILABLE without providerReference/items'
  }
}
finally {
  if ($previousMockUrl) { $env:SPIDER_SEGSENSE_MOCK_BASE_URL = $previousMockUrl }
  else { Remove-Item Env:SPIDER_SEGSENSE_MOCK_BASE_URL -ErrorAction SilentlyContinue }
  $stillMock = Get-MvpListenPid -Port 8095
  $stillSpider = Get-MvpListenPid -Port 8080
  Write-Output ("afterProofMeetingMockPid=$stillMock meetingMockUnchanged=$($stillMock -eq $meetingMockPid)")
  Write-Output ("afterProofMeetingSpiderPid=$stillSpider meetingSpiderUnchanged=$($stillSpider -eq $meetingSpiderPid)")
  $jvmStopped = $false
  if ($isolatedJava) {
    try {
      Stop-MvpOwnedProcess -ProcessId $isolatedJava -ExpectedPort $isolatedPort -ExpectedName 'java.exe' -CommandLineMustContain $marker -StartedAfter $startedAfter
      $jvmStopped = $true
      Write-Output "isolatedJvmStopped=$isolatedJava"
    } catch {
      Write-Output "isolatedJvmStopRefused=$($_.Exception.Message)"
    }
  }
  if ($isolated -and -not $isolated.HasExited) {
    if ($isolatedJava -and -not $jvmStopped) {
      Write-Output "isolatedLauncherLeftIntact=true reason=JVM stop was refused; not forcing launcher pid=$($isolated.Id)"
    } else {
      $launcherCheck = Test-MvpOwnedLauncherProcess -ProcessId $isolated.Id -ExpectedName 'cmd.exe' -CommandLineMustContain $marker -StartedAfter $startedAfter
      if ($launcherCheck.Owned) {
        try {
          Stop-Process -Id $isolated.Id -Force -ErrorAction Stop
          Write-Output "isolatedLauncherStopped=$($isolated.Id)"
        } catch {
          Write-Output "isolatedLauncherLeftIntact=true reason=Stop-Process failed on verified launcher"
        }
      } else {
        Write-Output "isolatedLauncherLeftIntact=true reason=$($launcherCheck.Reason)"
      }
    }
  }
  $deadlineStop = (Get-Date).AddSeconds(15)
  while ((Get-Date) -lt $deadlineStop -and (Get-MvpListenPid -Port $isolatedPort)) {
    Start-Sleep -Seconds 1
  }
}
