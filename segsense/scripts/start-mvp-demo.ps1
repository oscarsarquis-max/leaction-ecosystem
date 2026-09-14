# Starts the three local runtimes if their ports are free. Does not docker compose down.
# Does not kill a process already listening. Reused processes must pass identity preflight
# and are never recorded as stop targets. Only listeners proven to belong to this start
# are written to the gitignored owned-run ledger.
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $root 'segsense-provider-mock'))) {
  $root = 'C:\Projetos'
}
$logDir = Join-Path $root 'segsense\scripts\.mvp-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

. (Join-Path $PSScriptRoot '_mvp-process-safety.ps1')
. (Join-Path $PSScriptRoot '_load-mvp-secrets.ps1')
. (Join-Path $PSScriptRoot '_mvp-preflight.ps1')

$runId = [guid]::NewGuid().ToString('N')
$marker = "segsense.mvp.run=$runId"
$ledgerPath = Get-MvpOwnedLedgerPath
$script:ledger = Read-MvpOwnedLedger -Path $ledgerPath
if (-not $script:ledger) {
  $script:ledger = New-MvpOwnedLedger -RunId $runId
} else {
  $script:ledger.runId = $runId
  $script:ledger.startedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
  $script:ledger.targets = @($script:ledger.targets)
}

function Test-Listen([int]$Port) {
  return [bool](Get-MvpListenPid -Port $Port)
}

function Start-LoggedProcess($Name, $WorkDir, $File, $ArgList) {
  $out = Join-Path $logDir "$Name.out.log"
  $err = Join-Path $logDir "$Name.err.log"
  $proc = Start-Process -FilePath $File -ArgumentList $ArgList -WorkingDirectory $WorkDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
  Write-Output "started $Name launcherPid=$($proc.Id) (launcher is not a stop target)"
  return $proc
}

function Wait-ForCheck {
  param([scriptblock]$Check, [int]$Seconds, [string]$Name)
  $deadline = (Get-Date).AddSeconds($Seconds)
  $last = $null
  while ((Get-Date) -lt $deadline) {
    try {
      & $Check
      return
    } catch {
      $last = $_
    }
    Start-Sleep -Seconds 2
  }
  throw "Timed out waiting for $Name. $($last.Exception.Message)"
}

function Keep-ReusedLedgerTarget {
  param([string]$Role, [int]$Port)
  $existing = @($script:ledger.targets | Where-Object { $_.role -eq $Role })
  if ($existing.Count -eq 0) {
    Write-Output "port $Port already in use — $Role is reused and is NOT a stop target of this start"
    return
  }
  $check = Test-MvpOwnedLedgerTarget -Target $existing[0]
  if ($check.Owned) {
    Write-Output "port $Port already in use — previous owned $Role remains a stop target (pid=$($existing[0].listenerPid))"
  } else {
    Write-Output "port $Port already in use — previous ledger entry for $Role no longer verifies ($($check.Reason)); dropping it as a stop target and leaving the process intact"
    $script:ledger.targets = @($script:ledger.targets | Where-Object { $_.role -ne $Role })
  }
}

$env:SPIDER_SEGSENSE_MOCK_BASE_URL = 'http://127.0.0.1:8095'
$env:SPIDER_SEGSENSE_DEMO_CREDENTIAL_REF = 'local-demo-segsense'
$env:SEGSENSE_SPIDER_DEMO_BASE_URL = 'http://127.0.0.1:8080'
$env:SEGSENSE_SPIDER_DEMO_CREDENTIAL_REF = 'local-demo-segsense'

if (Test-Listen 5437) { Write-Output 'port 5437 already in use — reusing SegSense Postgres' }
else {
  Write-Output 'starting SegSense Postgres via compose up -d postgres (no down, no volume wipe)'
  Push-Location (Join-Path $root 'segsense')
  docker compose --env-file .env up -d postgres
  Pop-Location
  $deadline = (Get-Date).AddSeconds(40)
  while (-not (Test-Listen 5437) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
  }
  if (-not (Test-Listen 5437)) { Write-Output 'WARNING: Postgres :5437 still not listening after compose up' }
}

$segsenseMvnw = Join-Path $root 'segsense\backend\mvnw.cmd'
$feScript = Join-Path $PSScriptRoot 'mvp-fe-dev.mjs'

if (Test-Listen 8095) {
  Write-Output 'port 8095 already in use — verifying mock identity'
  Test-MvpMockIdentity
  Keep-ReusedLedgerTarget -Role 'mock' -Port 8095
} else {
  $startedAfter = Get-Date
  Start-LoggedProcess 'mock' (Join-Path $root 'segsense-provider-mock') 'node' @('server.js', "--$marker") | Out-Null
  Wait-ForCheck -Check { Test-MvpMockIdentity } -Seconds 20 -Name 'mock'
  Register-MvpOwnedListener -Ledger $script:ledger -Role 'mock' -Port 8095 -ExpectedName 'node.exe' -Marker $marker -StartedAfter $startedAfter | Out-Null
}

if (Test-Listen 8080) {
  Write-Output 'port 8080 already in use — verifying Spider Satellite Contract'
  Test-MvpSpiderSatelliteAuth
  Keep-ReusedLedgerTarget -Role 'spider' -Port 8080
} else {
  $startedAfter = Get-Date
  Start-LoggedProcess 'spider' (Join-Path $root 'spider\backend') 'cmd.exe' @('/c', "mvn -q spring-boot:run -Dspring-boot.run.profiles=local-demo -Dspring-boot.run.jvmArguments=-D$marker") | Out-Null
  Wait-ForCheck -Check { Test-MvpSpiderSatelliteAuth } -Seconds 90 -Name 'spider'
  Register-MvpOwnedListener -Ledger $script:ledger -Role 'spider' -Port 8080 -ExpectedName 'java.exe' -Marker $marker -StartedAfter $startedAfter | Out-Null
}

if (Test-Listen 8088) {
  Write-Output 'port 8088 already in use — verifying SegSense BFF'
  Test-MvpSegSenseIdentity
  Keep-ReusedLedgerTarget -Role 'segsense-bff' -Port 8088
} else {
  $startedAfter = Get-Date
  Start-LoggedProcess 'segsense-bff' (Join-Path $root 'segsense\backend') 'cmd.exe' @('/c', "`"$segsenseMvnw`" -q spring-boot:run `"-Dspring-boot.run.jvmArguments=-D$marker`"") | Out-Null
  Wait-ForCheck -Check { Test-MvpSegSenseIdentity } -Seconds 90 -Name 'segsense-bff'
  Register-MvpOwnedListener -Ledger $script:ledger -Role 'segsense-bff' -Port 8088 -ExpectedName 'java.exe' -Marker $marker -StartedAfter $startedAfter | Out-Null
}

if (Test-Listen 5178) {
  Write-Output 'port 5178 already in use — reusing SegSense FE'
  Keep-ReusedLedgerTarget -Role 'segsense-fe' -Port 5178
} else {
  $startedAfter = Get-Date
  Start-LoggedProcess 'segsense-fe' (Join-Path $root 'segsense\frontend') 'node' @($feScript, "--$marker") | Out-Null
  Wait-ForCheck -Check { if (-not (Get-MvpListenPid -Port 5178)) { throw 'frontend is not listening' } } -Seconds 40 -Name 'segsense-fe'
  Register-MvpOwnedListener -Ledger $script:ledger -Role 'segsense-fe' -Port 5178 -ExpectedName 'node.exe' -Marker $marker -StartedAfter $startedAfter | Out-Null
}

Save-MvpOwnedLedger -Path $ledgerPath -Ledger $script:ledger
Write-Output "owned-run ledger written (gitignored) runId=$runId targets=$(@($script:ledger.targets).Count)"
Write-Output 'pids.txt is not written and is not a stop source'

Invoke-MvpPreflight
Write-Output 'Open http://127.0.0.1:5178/demonstracao/mvp-integrado'
Write-Output 'Health: mock :8095/health | Spider :8080/actuator/health | SegSense :8088/api/v1/system/info'
