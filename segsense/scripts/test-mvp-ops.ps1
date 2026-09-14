# Operational tests for ACL and preflight identity. Does not print secret values.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
. (Join-Path $here '_mvp-secrets-acl.ps1')
. (Join-Path $here '_mvp-preflight.ps1')

$failed = $false
function Assert-True($Condition, $Message) {
  if (-not $Condition) {
    Write-Output "FAIL $Message"
    $script:failed = $true
  } else {
    Write-Output "ok $Message"
  }
}

$tmp = Join-Path $env:TEMP ("mvp-acl-" + [guid]::NewGuid().ToString() + '.env')
Set-Content -LiteralPath $tmp -Value 'DUMMY=1' -Encoding ascii
try {
  Set-MvpRestrictedAcl -Path $tmp
  Assert-True (Test-MvpRestrictedAcl -Path $tmp) 'restricted ACL accepted'
  & icacls $tmp /grant:r '*S-1-5-32-545:R' | Out-Null
  Assert-True (-not (Test-MvpRestrictedAcl -Path $tmp)) 'wide ACL rejected'
} finally {
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

$wrongJs = Join-Path $env:TEMP ("mvp-wrong-mock-" + [guid]::NewGuid().ToString() + '.js')
@'
const http = require('http');
http.createServer((q, s) => {
  s.writeHead(200, { 'Content-Type': 'application/json' });
  s.end(JSON.stringify({ status: 'ok' }));
}).listen(18995, '127.0.0.1');
'@ | Set-Content -LiteralPath $wrongJs -Encoding ascii
$proc = Start-Process -FilePath 'node' -ArgumentList $wrongJs -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 1
$env:MVP_MOCK_BASE_URL = 'http://127.0.0.1:18995'
try {
  Test-MvpMockIdentity
  Assert-True $false 'preflight accepted a process without Test Double identity'
} catch {
  Assert-True $true 'preflight rejected a process without Test Double identity'
} finally {
  if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
  Remove-Item -LiteralPath $wrongJs -Force -ErrorAction SilentlyContinue
  Remove-Item Env:MVP_MOCK_BASE_URL -ErrorAction SilentlyContinue
}

. (Join-Path $here '_mvp-process-safety.ps1')
$alien = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile -Command Start-Sleep -Seconds 45' -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 1
try {
  Assert-MvpRefusesStalePid -AlienPid $alien.Id -ExpectedPort 8095
  $still = Get-Process -Id $alien.Id -ErrorAction SilentlyContinue
  Assert-True ($null -ne $still) 'stale/recycled PID was not killed'
} catch {
  Write-Output "FAIL stale pid safety: $($_.Exception.Message)"
  $script:failed = $true
} finally {
  if ($alien -and -not $alien.HasExited) { Stop-Process -Id $alien.Id -Force -ErrorAction SilentlyContinue }
}

function Get-MvpTestFreePort {
  param([int[]]$Candidates)
  foreach ($port in $Candidates) {
    if (-not (Get-MvpListenPid -Port $port)) { return $port }
  }
  return $null
}

$stopScript = Join-Path $here 'stop-mvp-demo.ps1'
$realLedger = Get-MvpOwnedLedgerPath
$realLedgerStamp = $null
if (Test-Path -LiteralPath $realLedger) {
  $realLedgerStamp = (Get-Item -LiteralPath $realLedger).LastWriteTimeUtc
}
$meetingMockPid = Get-MvpListenPid -Port 8095
$meetingSpiderPid = Get-MvpListenPid -Port 8080
$meetingBffPid = Get-MvpListenPid -Port 8088
Write-Output "meeting-before mock=$meetingMockPid spider=$meetingSpiderPid bff=$meetingBffPid"

$staleDir = Join-Path $env:TEMP ("mvp-stop-stale-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $staleDir | Out-Null
$staleLedger = Join-Path $staleDir 'owned-run.json'
$staleAlien = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile -Command Start-Sleep -Seconds 90' -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 1
try {
  $staleRun = [guid]::NewGuid().ToString('N')
  $staleMarker = "segsense.mvp.run=$staleRun"
  $staleBook = New-MvpOwnedLedger -RunId $staleRun
  Add-MvpOwnedLedgerTarget -Ledger $staleBook -Role 'mock' -Port 8095 -ListenerPid $staleAlien.Id -Executable 'node.exe' -Marker $staleMarker -StartedAfter (Get-Date).AddMinutes(-1) -CommandLineExcerpt 'stale-recycled-pid' | Out-Null
  Save-MvpOwnedLedger -Path $staleLedger -Ledger $staleBook
  $staleOut = & $stopScript -LedgerPath $staleLedger
  $staleOut | ForEach-Object { Write-Output $_ }
  $staleAlive = Get-Process -Id $staleAlien.Id -ErrorAction SilentlyContinue
  Assert-True ($null -ne $staleAlive) 'real stop script left recycled/stale PID running'
  $staleLine = ($staleOut | Where-Object { $_ -like 'stop-result *action=refused*still-running=True*' } | Select-Object -First 1)
  Assert-True ($null -ne $staleLine) 'real stop script refused the stale PID'
  $mockAfterStale = Get-MvpListenPid -Port 8095
  Assert-True ($mockAfterStale -eq $meetingMockPid) 'meeting mock listener unchanged after stale-pid stop'
} catch {
  Write-Output "FAIL real stop stale pid: $($_.Exception.Message)"
  $script:failed = $true
} finally {
  if ($staleAlien -and -not $staleAlien.HasExited) { Stop-Process -Id $staleAlien.Id -Force -ErrorAction SilentlyContinue }
  Remove-Item -LiteralPath $staleDir -Recurse -Force -ErrorAction SilentlyContinue
}

$decoyJs = Join-Path $env:TEMP ("mvp-stop-decoy-" + [guid]::NewGuid().ToString('N') + '.js')
@'
setInterval(() => {}, 1000);
'@ | Set-Content -LiteralPath $decoyJs -Encoding ascii
$decoyDir = Join-Path $env:TEMP ("mvp-stop-decoy-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $decoyDir | Out-Null
$decoyLedger = Join-Path $decoyDir 'owned-run.json'
$decoy = Start-Process -FilePath 'node' -ArgumentList @($decoyJs, 'segsense-provider-mock', 'spring-boot.run.profiles=local-demo') -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 1
try {
  $decoyRun = [guid]::NewGuid().ToString('N')
  $decoyMarker = "segsense.mvp.run=$decoyRun"
  $decoyBook = New-MvpOwnedLedger -RunId $decoyRun
  Add-MvpOwnedLedgerTarget -Ledger $decoyBook -Role 'mock' -Port 8095 -ListenerPid $decoy.Id -Executable 'node.exe' -Marker $decoyMarker -StartedAfter (Get-Date).AddMinutes(-1) -CommandLineExcerpt 'segsense-provider-mock' | Out-Null
  Save-MvpOwnedLedger -Path $decoyLedger -Ledger $decoyBook
  $decoyOut = & $stopScript -LedgerPath $decoyLedger
  $decoyOut | ForEach-Object { Write-Output $_ }
  $decoyAlive = Get-Process -Id $decoy.Id -ErrorAction SilentlyContinue
  Assert-True ($null -ne $decoyAlive) 'similar node process outside this run remained running'
  $mockAfterDecoy = Get-MvpListenPid -Port 8095
  Assert-True ($mockAfterDecoy -eq $meetingMockPid) 'meeting mock listener unchanged after similar-process stop'
} catch {
  Write-Output "FAIL real stop similar process: $($_.Exception.Message)"
  $script:failed = $true
} finally {
  if ($decoy -and -not $decoy.HasExited) { Stop-Process -Id $decoy.Id -Force -ErrorAction SilentlyContinue }
  Remove-Item -LiteralPath $decoyJs -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $decoyDir -Recurse -Force -ErrorAction SilentlyContinue
}

$ownPort = Get-MvpTestFreePort -Candidates @(18998, 18999, 19001, 19002)
if (-not $ownPort) {
  Write-Output 'FAIL own-process stop: no free high port; not claiming stop validated'
  $script:failed = $true
} else {
  $ownJs = Join-Path $env:TEMP ("mvp-stop-own-" + [guid]::NewGuid().ToString('N') + '.js')
  @"
const http = require('http');
const port = $ownPort;
if (!process.argv.some((a) => a.startsWith('--segsense.mvp.run='))) process.exit(1);
http.createServer((q, s) => { s.writeHead(200); s.end('ok'); }).listen(port, '127.0.0.1');
"@ | Set-Content -LiteralPath $ownJs -Encoding ascii
  $ownDir = Join-Path $env:TEMP ("mvp-stop-own-" + [guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Force -Path $ownDir | Out-Null
  $ownLedger = Join-Path $ownDir 'owned-run.json'
  $ownRun = [guid]::NewGuid().ToString('N')
  $ownMarker = "segsense.mvp.run=$ownRun"
  $ownStarted = Get-Date
  $own = Start-Process -FilePath 'node' -ArgumentList @($ownJs, "--$ownMarker") -PassThru -WindowStyle Hidden
  $ownedReady = $false
  try {
    $deadline = (Get-Date).AddSeconds(8)
    while ((Get-Date) -lt $deadline) {
      $listen = Get-MvpListenPid -Port $ownPort
      if ($listen -eq $own.Id) { $ownedReady = $true; break }
      Start-Sleep -Milliseconds 200
    }
    $ownCheck = $null
    if ($ownedReady) {
      $ownCheck = Test-MvpOwnedProcess -ProcessId $own.Id -ExpectedPort $ownPort -ExpectedName 'node.exe' -CommandLineMustContain $ownMarker -StartedAfter $ownStarted
    }
    if (-not $ownedReady -or -not $ownCheck -or -not $ownCheck.Owned) {
      Write-Output "FAIL own-process stop could not be mounted safely: listen=$ownedReady reason=$($ownCheck.Reason)"
      $script:failed = $true
    } else {
      $ownBook = New-MvpOwnedLedger -RunId $ownRun
      Add-MvpOwnedLedgerTarget -Ledger $ownBook -Role 'own-test' -Port $ownPort -ListenerPid $own.Id -Executable 'node.exe' -Marker $ownMarker -StartedAfter $ownStarted -CommandLineExcerpt (Convert-MvpCommandLineExcerpt $ownCheck.Snapshot.CommandLine) | Out-Null
      Save-MvpOwnedLedger -Path $ownLedger -Ledger $ownBook
      $ownOut = & $stopScript -LedgerPath $ownLedger
      $ownOut | ForEach-Object { Write-Output $_ }
      Start-Sleep -Milliseconds 400
      $ownAlive = Get-Process -Id $own.Id -ErrorAction SilentlyContinue
      Assert-True ($null -eq $ownAlive) 'real stop script stopped the unequivocally owned test process'
      $ownStoppedLine = ($ownOut | Where-Object { $_ -like "stop-result role=own-test pid=$($own.Id) action=stopped*" } | Select-Object -First 1)
      Assert-True ($null -ne $ownStoppedLine) 'real stop script reported stopped for the owned test process'
      Assert-True (-not (Get-MvpListenPid -Port $ownPort)) 'owned test port is no longer listening'
    }
  } catch {
    Write-Output "FAIL real stop owned process: $($_.Exception.Message)"
    $script:failed = $true
  } finally {
    if ($own -and -not $own.HasExited) { Stop-Process -Id $own.Id -Force -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $ownJs -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ownDir -Recurse -Force -ErrorAction SilentlyContinue
  }
}

$meetingMockAfter = Get-MvpListenPid -Port 8095
$meetingSpiderAfter = Get-MvpListenPid -Port 8080
$meetingBffAfter = Get-MvpListenPid -Port 8088
Write-Output "meeting-after mock=$meetingMockAfter spider=$meetingSpiderAfter bff=$meetingBffAfter"
Assert-True ($meetingMockAfter -eq $meetingMockPid) 'meeting mock :8095 untouched by stop tests'
Assert-True ($meetingSpiderAfter -eq $meetingSpiderPid) 'meeting Spider :8080 untouched by stop tests'
Assert-True ($meetingBffAfter -eq $meetingBffPid) 'meeting BFF :8088 untouched by stop tests'

$realLedgerStampAfter = $null
if (Test-Path -LiteralPath $realLedger) {
  $realLedgerStampAfter = (Get-Item -LiteralPath $realLedger).LastWriteTimeUtc
}
Assert-True ($realLedgerStamp -eq $realLedgerStampAfter) 'stop tests did not rewrite the meeting owned-run ledger'

if ($failed) { throw 'test-mvp-ops failed' }
Write-Output 'test-mvp-ops=ok'
