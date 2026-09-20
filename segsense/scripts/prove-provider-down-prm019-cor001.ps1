# Isolated mock-down proof for PRM_019_COR_001. Does not touch meeting :8095/:8080/:8088/:5178.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_mvp-process-safety.ps1')
. (Join-Path $PSScriptRoot '_load-mvp-secrets.ps1')
. (Join-Path $PSScriptRoot '_mvp-preflight.ps1')

$outDir = Join-Path $PSScriptRoot '..\documents\evidencias\SEGSENSE_PRM_019_COR_001'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$meeting = @{
  mock = Get-MvpListenPid -Port 8095
  spider = Get-MvpListenPid -Port 8080
  bff = Get-MvpListenPid -Port 8088
  fe = Get-MvpListenPid -Port 5178
}
Write-Output ("meetingBefore mock=$($meeting.mock) spider=$($meeting.spider) bff=$($meeting.bff) fe=$($meeting.fe)")

$env:MVP_MOCK_BASE_URL = 'http://127.0.0.1:19095'
$env:MVP_SPIDER_BASE_URL = 'http://127.0.0.1:19080'
$env:MVP_SEGSENSE_BASE_URL = 'http://127.0.0.1:19088'
Test-MvpMockIdentity
Test-MvpSpiderSatelliteAuth
Test-MvpSegSenseIdentity
Write-Output 'preflight-isolated=ok'

$mockPid = Get-MvpListenPid -Port 19095
if (-not $mockPid) { throw 'isolated mock :19095 is not listening' }
if ($mockPid -eq $meeting.mock) { throw 'refusing to stop: isolated mock pid equals meeting mock pid' }
Write-Output "stopping isolated mock pid=$mockPid (meeting mock $($meeting.mock) untouched)"
Stop-Process -Id $mockPid -Force
Start-Sleep -Seconds 2
if (Get-MvpListenPid -Port 19095) { throw 'isolated mock still listening after stop' }

$tmp = Join-Path $env:TEMP ("cor001-down-" + [guid]::NewGuid().ToString('N') + '.json')
$body = '{"declaredObjective":"SIMULATE_HOME_QUOTE","declaredIntention":"Quero contratar um seguro residencial","declaredContext":"Houve incêndios nas proximidades","intentionConfirmed":"true","dwellingType":"APARTMENT","insuredAmountCents":"30000000","coverPeriodMonths":"12"}'
[System.IO.File]::WriteAllText($tmp, $body, (New-Object System.Text.UTF8Encoding $false))
$out = Join-Path $env:TEMP ("cor001-down-out-" + [guid]::NewGuid().ToString('N') + '.json')
$corr = [guid]::NewGuid().ToString()
$key = [guid]::NewGuid().ToString()
& curl.exe -sS -o $out -w '%{http_code}' -X POST 'http://127.0.0.1:19088/api/v1/public/demo/protection-journeys' -H 'Content-Type: application/json; charset=utf-8' -H "Idempotency-Key: $key" -H "X-Correlation-ID: $corr" --data-binary "@$tmp" | Out-Null
$payload = Get-Content -LiteralPath $out -Raw -Encoding UTF8 | ConvertFrom-Json
if ($payload.status -ne 'MOCK_UNAVAILABLE') { throw "expected MOCK_UNAVAILABLE, got $($payload.status)" }
if ($payload.simulatedQuote) { throw 'provider-down response contained simulatedQuote' }
Write-Output "providerDownHttp=MOCK_UNAVAILABLE premiumAbsent=$([string]::IsNullOrWhiteSpace([string]$payload.simulatedQuote))"
node (Join-Path $PSScriptRoot 'capture-provider-down-prm019-cor001.mjs')

$env:PORT = '19095'
$root = 'C:\Projetos'
$logDir = Join-Path $PSScriptRoot '.mvp-logs'
$outLog = Join-Path $logDir 'cor016-mock-restart-cor001.out.log'
$errLog = Join-Path $logDir 'cor016-mock-restart-cor001.err.log'
$restart = Start-Process -FilePath 'node' -ArgumentList 'server.js' -WorkingDirectory (Join-Path $root 'segsense-provider-mock') -PassThru -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
$deadline = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $deadline) {
  if (Get-MvpListenPid -Port 19095) { break }
  Start-Sleep -Seconds 1
}
if (-not (Get-MvpListenPid -Port 19095)) { throw "isolated mock did not return on :19095 after restart launcherPid=$($restart.Id)" }
Test-MvpMockIdentity
Write-Output ("mockRestarted pid=$(Get-MvpListenPid -Port 19095)")

$after = @{
  mock = Get-MvpListenPid -Port 8095
  spider = Get-MvpListenPid -Port 8080
  bff = Get-MvpListenPid -Port 8088
  fe = Get-MvpListenPid -Port 5178
}
foreach ($role in @('mock','spider','bff','fe')) {
  if ($meeting[$role] -ne $after[$role]) {
    throw "meeting $role changed: $($meeting[$role]) -> $($after[$role])"
  }
}
Write-Output 'meetingUnchanged=true'

$proof = @{
  status = $payload.status
  mockCalled = $payload.mockCalled
  simulatedQuote = $payload.simulatedQuote
  quoteReference = $payload.quoteReference
  meetingUnchanged = $true
} | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $outDir 'provider-down-http.json'), $proof, (New-Object System.Text.UTF8Encoding $false))
Remove-Item -LiteralPath $tmp, $out -Force -ErrorAction SilentlyContinue
Write-Output 'provider-down proof complete'
