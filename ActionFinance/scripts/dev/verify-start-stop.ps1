$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_lib.ps1")

$root = Get-ActionFinanceRoot
$script = Join-Path $PSScriptRoot "start-local.ps1"
$stop = Join-Path $PSScriptRoot "stop-local.ps1"
$ports = Get-ActionFinancePorts
$ownership = Join-Path $PSScriptRoot "verify-ownership.ps1"

function Invoke-Script([string]$path) {
  $output = & $path 2>&1 | Out-String
  return [pscustomobject]@{ ExitCode = $LASTEXITCODE; Output = $output }
}

$first = Invoke-Script $script
if ($first.ExitCode -ne 0) { throw "First start failed: $($first.Output)" }
if ($first.Output -notmatch "STARTED|ALREADY_RUNNING") { throw "First start did not report readiness." }

$second = Invoke-Script $script
if ($second.ExitCode -ne 0) { throw "Second start failed: $($second.Output)" }
if ($second.Output -notmatch "ALREADY_RUNNING") { throw "Second start must reuse the healthy instance." }

$stop1 = Invoke-Script $stop
if ($stop1.ExitCode -ne 0) { throw "First stop failed: $($stop1.Output)" }
$stop2 = Invoke-Script $stop
if ($stop2.ExitCode -ne 0) { throw "Second stop failed: $($stop2.Output)" }
if ($stop2.Output -notmatch "STOPPED_ALREADY") { throw "Second stop must be idempotent." }

$staleDir = Join-Path $PSScriptRoot ".pids"
New-Item -ItemType Directory -Force -Path $staleDir | Out-Null
$dummy = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile","-Command","Start-Sleep -Seconds 20" -WindowStyle Hidden -PassThru
$stale = [pscustomobject]@{
  kind = "backend"
  pid = $dummy.Id
  processName = $dummy.ProcessName
  commandLine = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
  creationUtc = [datetime]::UtcNow.ToString("o")
  port = $ports.Backend
}
($stale | ConvertTo-Json) | Set-Content (Join-Path $staleDir "backend.json") -Encoding utf8
Set-Content (Join-Path $staleDir "backend.pid") $dummy.Id
$staleStop = Invoke-Script $stop
Stop-Process -Id $dummy.Id -Force -ErrorAction SilentlyContinue
if ($staleStop.Output -notmatch "REFUSED_STOP") {
  throw "Stale/reused PID must be refused. Output=$($staleStop.Output)"
}

$occupied = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile","-Command","`$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $($ports.Backend)); `$listener.Start(); Start-Sleep -Seconds 25; `$listener.Stop()" -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 1
try {
  $busy = Invoke-Script $script
  if ($busy.ExitCode -eq 0 -or $busy.Output -notmatch "occupied") {
    throw "Occupied port must fail without kill. Output=$($busy.Output)"
  }
} finally {
  Stop-Process -Id $occupied.Id -Force -ErrorAction SilentlyContinue
}

$ownershipResult = & $ownership
$ownershipResult | Write-Output
if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "Ownership proofs failed exit=$LASTEXITCODE" }

Write-Output "LIFECYCLE_VERIFY_OK start-twice=reuse stop-twice=idempotent stale-pid=refused occupied-port=refused"
