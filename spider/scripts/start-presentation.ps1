#Requires -Version 5.1
<#
.SYNOPSIS
  Sobe backend (profile local-demo) e frontend para apresentação Mock.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$mvn = Join-Path $Root ".tools\apache-maven-3.9.16\bin\mvn.cmd"
if (-not (Test-Path $mvn)) { $mvn = "mvn" }
$npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npmCmd) { $npmCmd = "npm.cmd" }

$logDir = Join-Path $Root "scripts\.presentation-logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Write-Host "== start-presentation (MOCK_ONLY) =="
Write-Host "Logs: $logDir"

$backend = Start-Process -FilePath $mvn -ArgumentList @(
  "spring-boot:run",
  "-Dspring-boot.run.profiles=local-demo"
) -WorkingDirectory (Join-Path $Root "backend") `
  -RedirectStandardOutput (Join-Path $logDir "backend.out.log") `
  -RedirectStandardError (Join-Path $logDir "backend.err.log") `
  -PassThru -WindowStyle Hidden

$frontend = Start-Process -FilePath $npmCmd -ArgumentList @("run", "dev") -WorkingDirectory (Join-Path $Root "frontend") `
  -RedirectStandardOutput (Join-Path $logDir "frontend.out.log") `
  -RedirectStandardError (Join-Path $logDir "frontend.err.log") `
  -PassThru -WindowStyle Hidden

Set-Content -Path (Join-Path $logDir "pids.txt") -Value "backend=$($backend.Id)`nfrontend=$($frontend.Id)"
Write-Host "Backend PID $($backend.Id) | Frontend PID $($frontend.Id)"
Write-Host "Aguardando health..."

$ready = $false
for ($i = 0; $i -lt 90; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/actuator/health" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) { $ready = $true; break }
  } catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) {
  Write-Warning "Backend ainda não respondeu health. Veja logs em $logDir"
} else {
  Write-Host "Backend UP"
}

Write-Host "UI:  http://127.0.0.1:5180"
Write-Host "API: http://127.0.0.1:8080/v1/console/presentation/readiness"
Write-Host "Impl: http://127.0.0.1:8080/v1/console/implementation"
Write-Host "Para encerrar: Stop-Process -Id $($backend.Id),$($frontend.Id) -Force"
