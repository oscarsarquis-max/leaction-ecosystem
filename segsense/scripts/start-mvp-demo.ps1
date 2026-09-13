# Starts the three local runtimes if their ports are free. Does not docker compose down.
# Does not kill a process already listening. Reused processes must pass identity preflight.
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $root 'segsense-provider-mock'))) {
  $root = 'C:\Projetos'
}
$logDir = Join-Path $root 'segsense\scripts\.mvp-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$pidsFile = Join-Path $logDir 'pids.txt'

function Test-Listen([int]$Port) {
  return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Start-LoggedProcess($Name, $WorkDir, $File, $ArgList) {
  $out = Join-Path $logDir "$Name.out.log"
  $err = Join-Path $logDir "$Name.err.log"
  $proc = Start-Process -FilePath $File -ArgumentList $ArgList -WorkingDirectory $WorkDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
  Add-Content -Path $pidsFile -Value "$Name=$($proc.Id)"
  Write-Output "started $Name pid=$($proc.Id)"
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

if (-not (Test-Path $pidsFile)) { New-Item -ItemType File -Path $pidsFile | Out-Null }

. (Join-Path $PSScriptRoot '_load-mvp-secrets.ps1')
. (Join-Path $PSScriptRoot '_mvp-preflight.ps1')
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

if (Test-Listen 8095) {
  Write-Output 'port 8095 already in use — verifying mock identity'
  Test-MvpMockIdentity
} else {
  Start-LoggedProcess 'mock' (Join-Path $root 'segsense-provider-mock') 'node' 'server.js'
  Wait-ForCheck -Check { Test-MvpMockIdentity } -Seconds 20 -Name 'mock'
}

if (Test-Listen 8080) {
  Write-Output 'port 8080 already in use — verifying Spider Satellite Contract'
  Test-MvpSpiderSatelliteAuth
} else {
  Start-LoggedProcess 'spider' (Join-Path $root 'spider\backend') 'cmd.exe' '/c mvn -q spring-boot:run -Dspring-boot.run.profiles=local-demo'
  Wait-ForCheck -Check { Test-MvpSpiderSatelliteAuth } -Seconds 90 -Name 'spider'
}

if (Test-Listen 8088) {
  Write-Output 'port 8088 already in use — verifying SegSense BFF'
  Test-MvpSegSenseIdentity
} else {
  Start-LoggedProcess 'segsense-bff' (Join-Path $root 'segsense\backend') 'cmd.exe' "/c `"$segsenseMvnw`" -q spring-boot:run"
  Wait-ForCheck -Check { Test-MvpSegSenseIdentity } -Seconds 90 -Name 'segsense-bff'
}

if (Test-Listen 5178) { Write-Output 'port 5178 already in use — reusing SegSense FE' }
else {
  Start-LoggedProcess 'segsense-fe' (Join-Path $root 'segsense\frontend') 'cmd.exe' '/c npm run dev'
}

Invoke-MvpPreflight
Write-Output 'Open http://127.0.0.1:5178/demonstracao/mvp-integrado'
Write-Output 'Health: mock :8095/health | Spider :8080/actuator/health | SegSense :8088/api/v1/system/info'
