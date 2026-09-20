#Requires -Version 5.1
<#
.SYNOPSIS
  Starts SpiderBank BFF/frontend and, if needed, the credit mock. Leaves Monitor, engine and SegSense untouched when already healthy.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$workspace = Split-Path $root -Parent
$mockRoot = Join-Path $workspace 'mock-sistemas-credito'
$logDir = Join-Path $PSScriptRoot '.logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
. (Join-Path $PSScriptRoot 'setup-local-secrets.ps1')
. (Join-Path $PSScriptRoot '_load-local-secrets.ps1')

function Test-Listen([int]$Port) {
  $found = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  return [bool]$found
}

function Wait-Http([string]$Url, [int]$Seconds, [string]$Name) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  $last = $null
  while ((Get-Date) -lt $deadline) {
    try {
      $req = [System.Net.HttpWebRequest]::Create($Url)
      $req.Timeout = 2000
      $req.ProtocolVersion = [Version]'1.1'
      $resp = $req.GetResponse()
      $code = [int]$resp.StatusCode
      $resp.Close()
      if ($code -ge 200 -and $code -lt 500) { return }
    } catch {
      $last = $_
    }
    Start-Sleep -Seconds 2
  }
  throw "Timed out waiting for $Name. $last"
}

Write-Output "Shell suportado: Windows PowerShell 5.1+. Portas do produto: BFF 8090, frontend 5190, mock de credito 8096."

$owned = @{ bff = $null; fe = $null; mock = $null }
$ledger = Join-Path $logDir 'owned.json'

if (-not (Test-Listen 8080)) {
  Write-Output "WARN Spider engine is not listening on :8080. Start local-demo with the same assertion and credit-mock secrets before proving the journey."
} else {
  Write-Output "Spider engine already listening on :8080 — leaving it untouched"
}

if (Test-Listen 5180) {
  Write-Output "Monitor already listening on :5180 — leaving it untouched"
}

$env:SPIDERBANK_SPIDER_DEMO_BASE_URL = 'http://127.0.0.1:8080'
$env:SPIDERBANK_BACKEND_PORT = '8090'
$env:SPIDERBANK_FRONTEND_ORIGIN = 'http://127.0.0.1:5190,http://localhost:5190'
$env:VITE_DEV_PORT = '5190'
$env:SPIDERBANK_BFF_URL = 'http://127.0.0.1:8090'
$env:PORT = '8096'

if (Test-Listen 8096) {
  Write-Output "port 8096 already in use — reusing credit mock and NOT recording it as a stop target"
} elseif (Test-Path (Join-Path $mockRoot 'server.js')) {
  $mockOut = Join-Path $logDir 'credit-mock.out.log'
  $mockErr = Join-Path $logDir 'credit-mock.err.log'
  $mock = Start-Process -FilePath 'node.exe' -ArgumentList @('server.js') -WorkingDirectory $mockRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $mockOut -RedirectStandardError $mockErr
  $owned.mock = $mock.Id
  Write-Output "started credit mock launcherPid=$($mock.Id)"
} else {
  Write-Output "WARN mock-sistemas-credito not found at $mockRoot"
}

if (Test-Listen 8090) {
  Write-Output "port 8090 already in use — reusing BFF and NOT recording it as a stop target"
} else {
  $bffOut = Join-Path $logDir 'bff.out.log'
  $bffErr = Join-Path $logDir 'bff.err.log'
  $bff = Start-Process -FilePath 'mvn.cmd' -ArgumentList @('-f', (Join-Path $root 'backend\pom.xml'), '-q', 'spring-boot:run') -WorkingDirectory (Join-Path $root 'backend') -PassThru -WindowStyle Hidden -RedirectStandardOutput $bffOut -RedirectStandardError $bffErr
  $owned.bff = $bff.Id
  Write-Output "started BFF launcherPid=$($bff.Id)"
}

if (Test-Listen 5190) {
  Write-Output "port 5190 already in use — reusing frontend and NOT recording it as a stop target"
} else {
  $feOut = Join-Path $logDir 'fe.out.log'
  $feErr = Join-Path $logDir 'fe.err.log'
  $fe = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run', 'dev') -WorkingDirectory (Join-Path $root 'frontend') -PassThru -WindowStyle Hidden -RedirectStandardOutput $feOut -RedirectStandardError $feErr
  $owned.fe = $fe.Id
  Write-Output "started frontend launcherPid=$($fe.Id)"
}

($owned | ConvertTo-Json) | Set-Content -Path $ledger -Encoding ascii
if (Test-Path (Join-Path $mockRoot 'server.js')) {
  Wait-Http 'http://127.0.0.1:8096/health' 30 'credit mock'
}
Wait-Http 'http://127.0.0.1:8090/api/health' 90 'SpiderBank BFF'
Wait-Http 'http://127.0.0.1:5190/' 90 'SpiderBank frontend'
Write-Output "SpiderBank ready: frontend http://127.0.0.1:5190/  BFF http://127.0.0.1:8090/api/health"
Write-Output "Simulation card readiness is determined by Spider. Product URL is http://127.0.0.1:5190/ — not Monitor /spiderbank."
