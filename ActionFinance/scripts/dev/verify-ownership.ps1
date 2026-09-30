$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_lib.ps1")

$root = Get-ActionFinanceRoot
$runId = "own-" + [guid]::NewGuid().ToString("N").Substring(0, 12)
$work = Join-Path $root ".local\verify-runs\$runId"
New-Item -ItemType Directory -Force -Path $work | Out-Null
$decoy = $null
$alive = New-Object System.Collections.Generic.List[System.Diagnostics.Process]

function Start-BoundScript([string]$path) {
  $proc = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile","-File",$path) -WorkingDirectory $work -WindowStyle Hidden -PassThru
  $alive.Add($proc) | Out-Null
  return $proc
}

function Assert-ProcessAlive([int]$processId, [string]$label) {
  if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
    throw "$label pid=$processId was terminated but must survive."
  }
}

function Assert-ProcessGone([int]$processId, [string]$label) {
  $deadline = (Get-Date).AddSeconds(8)
  do {
    if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) { return }
    Start-Sleep -Milliseconds 200
  } while ((Get-Date) -lt $deadline)
  throw "$label pid=$processId is still running after stop."
}

try {
  $childScript = Join-Path $work "child.ps1"
  Set-Content -Path $childScript -Value "Start-Sleep -Seconds 90" -Encoding ascii

  $wrapStay = Join-Path $work "wrap-stay.ps1"
  Set-Content -Path $wrapStay -Value @"
`$child = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-File','$childScript') -WorkingDirectory '$work' -WindowStyle Hidden -PassThru
Set-Content -Path '$work\stay-child.pid' `$child.Id
Start-Sleep -Seconds 80
"@ -Encoding ascii

  $wrapExit = Join-Path $work "wrap-exit.ps1"
  Set-Content -Path $wrapExit -Value @"
`$child = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-File','$childScript') -WorkingDirectory '$work' -WindowStyle Hidden -PassThru
Set-Content -Path '$work\exit-child.pid' `$child.Id
Start-Sleep -Seconds 2
"@ -Encoding ascii

  $decoy = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile","-Command","Start-Sleep -Seconds 90; # actionfinance java npm vite") -WindowStyle Hidden -PassThru
  $alive.Add($decoy) | Out-Null

  $stay = Start-BoundScript $wrapStay
  $deadline = (Get-Date).AddSeconds(8)
  do {
    if (Test-Path (Join-Path $work "stay-child.pid")) { break }
    Start-Sleep -Milliseconds 200
  } while ((Get-Date) -lt $deadline)
  $stayRecord = New-ActionFinanceLaunchRecord -Kind "own-stay" -LaunchId $runId -CheckoutRoot $root -WrapperPid $stay.Id -Port 0 -BoundPath $wrapStay
  $stayRecord = Update-ActionFinanceLaunchChildren $stayRecord
  Save-ActionFinanceLaunchRecord $stayRecord
  $stayChildPid = [int](Get-Content (Join-Path $work "stay-child.pid")).Trim()
  if (-not ($stayRecord.children | Where-Object { [int]$_.pid -eq $stayChildPid })) {
    throw "Stay wrapper did not record child pid=$stayChildPid while parentage was provable."
  }
  Stop-ActionFinanceOwnedTree -Metadata $stayRecord
  Assert-ProcessGone $stay.Id "stay-wrapper"
  Assert-ProcessGone $stayChildPid "stay-child"
  Assert-ProcessAlive $decoy.Id "decoy-after-owned-stop"
  Remove-ActionFinancePidMetadata "own-stay"

  $exitWrap = Start-BoundScript $wrapExit
  $deadline = (Get-Date).AddSeconds(8)
  do {
    if (Test-Path (Join-Path $work "exit-child.pid")) { break }
    Start-Sleep -Milliseconds 200
  } while ((Get-Date) -lt $deadline)
  $exitRecord = New-ActionFinanceLaunchRecord -Kind "own-exit" -LaunchId "$runId-exit" -CheckoutRoot $root -WrapperPid $exitWrap.Id -Port 0 -BoundPath $wrapExit
  $exitRecord = Update-ActionFinanceLaunchChildren $exitRecord
  Save-ActionFinanceLaunchRecord $exitRecord
  $exitChildPid = [int](Get-Content (Join-Path $work "exit-child.pid")).Trim()
  if (-not ($exitRecord.children | Where-Object { [int]$_.pid -eq $exitChildPid })) {
    throw "Exit wrapper did not record child pid=$exitChildPid before leaving."
  }
  $deadline = (Get-Date).AddSeconds(10)
  do {
    if (-not (Get-Process -Id $exitWrap.Id -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Milliseconds 200
  } while ((Get-Date) -lt $deadline)
  if (Get-Process -Id $exitWrap.Id -ErrorAction SilentlyContinue) {
    throw "Exit wrapper did not leave before the stop proof."
  }
  Assert-ProcessAlive $exitChildPid "child-after-wrapper-exit"
  $reloaded = Read-ActionFinancePidMetadata "own-exit"
  Stop-ActionFinanceOwnedTree -Metadata $reloaded
  Assert-ProcessGone $exitChildPid "child-after-wrapper-gone-stop"
  Assert-ProcessAlive $decoy.Id "decoy-after-wrapper-gone-stop"
  Remove-ActionFinancePidMetadata "own-exit"

  $dummy = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile","-Command","Start-Sleep -Seconds 60") -WindowStyle Hidden -PassThru
  $alive.Add($dummy) | Out-Null
  $wrongName = [pscustomobject]@{
    kind = "own-reuse"
    launchId = "$runId-reuse"
    checkoutRoot = $root
    wrapper = [pscustomobject]@{
      pid = $dummy.Id
      processName = "java"
      path = $dummy.Path
      commandLine = "actionfinance java npm vite"
      creationUtc = $dummy.StartTime.ToUniversalTime().ToString("o")
    }
    server = $null
    children = @()
    port = 0
  }
  $refusedName = $false
  try { Stop-ActionFinanceOwnedTree -Metadata $wrongName } catch {
    if ($_.Exception.Message -match "REFUSED_STOP") { $refusedName = $true } else { throw }
  }
  if (-not $refusedName) { throw "Wrong processName metadata must be refused." }
  Assert-ProcessAlive $dummy.Id "dummy-after-wrong-name"

  $wrongTime = [pscustomobject]@{
    kind = "own-reuse"
    launchId = "$runId-reuse"
    checkoutRoot = $root
    wrapper = [pscustomobject]@{
      pid = $dummy.Id
      processName = $dummy.ProcessName
      path = $dummy.Path
      commandLine = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
      creationUtc = ([datetime]::UtcNow).AddHours(-5).ToString("o")
    }
    server = $null
    children = @()
    port = 0
  }
  $refusedTime = $false
  try { Stop-ActionFinanceOwnedTree -Metadata $wrongTime } catch {
    if ($_.Exception.Message -match "REFUSED_STOP") { $refusedTime = $true } else { throw }
  }
  if (-not $refusedTime) { throw "Reused-PID/stale creationUtc metadata must be refused." }
  Assert-ProcessAlive $dummy.Id "dummy-after-stale-creation"
  Assert-ProcessAlive $decoy.Id "decoy-final"

  $similar = Join-Path (Split-Path $root -Parent) "ActionFinanceR1Similar"
  $similarBound = Test-ActionFinanceCheckoutBound "$similar\scripts\run.ps1" $root
  if ($similarBound) { throw "Similar checkout path must not bind to this execution." }
  $exactBound = Test-ActionFinanceCheckoutBound (Join-Path $root "scripts\dev\run-backend.ps1") $root
  if (-not $exactBound) { throw "Exact checkout path must bind." }

  $noDate = [pscustomobject]@{
    kind = "own-nodate"
    launchId = "$runId-nodate"
    checkoutRoot = $root
    wrapper = [pscustomobject]@{
      pid = $dummy.Id
      processName = $dummy.ProcessName
      path = $dummy.Path
      commandLine = $dummy.Path
      creationUtc = $null
    }
    server = $null
    children = @()
    port = 0
  }
  $refusedNoDate = $false
  try { Stop-ActionFinanceOwnedTree -Metadata $noDate } catch {
    if ($_.Exception.Message -match "REFUSED_STOP") { $refusedNoDate = $true } else { throw }
  }
  if (-not $refusedNoDate) { throw "Record without creationUtc must be refused." }
  Assert-ProcessAlive $dummy.Id "dummy-after-missing-creation"

  $wrongCheckout = [pscustomobject]@{
    kind = "own-path"
    launchId = "$runId-path"
    checkoutRoot = $similar
    wrapper = [pscustomobject]@{
      pid = $dummy.Id
      processName = $dummy.ProcessName
      path = $dummy.Path
      commandLine = $dummy.Path
      creationUtc = $dummy.StartTime.ToUniversalTime().ToString("o")
    }
    server = $null
    children = @()
    port = 0
  }
  $refusedPath = $false
  try { Stop-ActionFinanceOwnedTree -Metadata $wrongCheckout } catch {
    if ($_.Exception.Message -match "REFUSED_STOP") { $refusedPath = $true } else { throw }
  }
  if (-not $refusedPath) { throw "Similar checkoutRoot must be refused." }
  Assert-ProcessAlive $dummy.Id "dummy-after-similar-checkout"

  Write-Output "OWNERSHIP_VERIFY_OK stay-tree=stopped wrapper-exit-child=stopped decoy=survived reused-pid=refused invalid-name=refused missing-date=refused similar-path=refused"
} finally {
  foreach ($proc in $alive) {
    if ($proc -and -not $proc.HasExited) {
      Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
  }
  foreach ($pidFile in @("stay-child.pid", "exit-child.pid")) {
    $path = Join-Path $work $pidFile
    if (Test-Path $path) {
      $childPid = [int](Get-Content $path).Trim()
      if ($childPid -gt 0) {
        Stop-Process -Id $childPid -Force -ErrorAction SilentlyContinue
      }
    }
  }
  Remove-ActionFinancePidMetadata "own-stay"
  Remove-ActionFinancePidMetadata "own-exit"
  $resolvedWork = [IO.Path]::GetFullPath($work)
  $allowedRoot = [IO.Path]::GetFullPath((Join-Path $root ".local\verify-runs"))
  if ((Get-ActionFinanceNormalizedPath $resolvedWork) -ne (Get-ActionFinanceNormalizedPath $allowedRoot) -and (Test-ActionFinancePathInside $resolvedWork $allowedRoot) -and ((Split-Path $resolvedWork -Leaf) -eq $runId)) {
    Remove-Item $resolvedWork -Recurse -Force -ErrorAction SilentlyContinue
  }
}
