# Process ownership checks. Dot-source only. Never kill on PID-from-file alone.
$ErrorActionPreference = 'Stop'

function Get-MvpListenPid {
  param([int]$Port)
  try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
    if ($conn) { return [int]$conn.OwningProcess }
  } catch {
    $pattern = ':{0}\s+.*LISTENING\s+(\d+)\s*$' -f $Port
    $line = netstat -ano | Select-String -Pattern $pattern | Select-Object -First 1
    if ($line) { return [int]$line.Matches[0].Groups[1].Value }
  }
  return $null
}

function Convert-MvpCreationDate {
  param($DmtfDate)
  if ([string]::IsNullOrWhiteSpace([string]$DmtfDate)) { return $null }
  try {
    return [Management.ManagementDateTimeConverter]::ToDateTime($DmtfDate)
  } catch {
    return $null
  }
}

function Get-MvpProcessSnapshot {
  param([int]$ProcessId)
  $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  if (-not $proc) { return $null }
  return [pscustomobject]@{
    ProcessId = [int]$proc.ProcessId
    Name = [string]$proc.Name
    CommandLine = [string]$proc.CommandLine
    CreationDate = $proc.CreationDate
    ParentProcessId = [int]$proc.ParentProcessId
  }
}

function Test-MvpOwnershipMarker {
  param([string]$Marker)
  return [bool]($Marker -match '^segsense\.(mvp\.run|isolated\.proof|isolated\.stack)=[0-9a-fA-F]{32}$')
}

function Test-MvpOwnedProcess {
  param(
    [Parameter(Mandatory)][int]$ProcessId,
    [Parameter(Mandatory)][int]$ExpectedPort,
    [Parameter(Mandatory)][string]$ExpectedName,
    [Parameter(Mandatory)][string]$CommandLineMustContain,
    [datetime]$StartedAfter = [datetime]::MinValue
  )
  if ($ExpectedName -match '[\*\?]' -or $ExpectedName -notmatch '^[A-Za-z0-9._-]+\.exe$') {
    return [pscustomobject]@{ Owned = $false; Reason = 'expected executable is missing or too broad' }
  }
  $listenPid = Get-MvpListenPid -Port $ExpectedPort
  if ($listenPid -ne $ProcessId) {
    return [pscustomobject]@{ Owned = $false; Reason = "pid $ProcessId is not the listener on port $ExpectedPort (listener=$listenPid)" }
  }
  $snap = Get-MvpProcessSnapshot -ProcessId $ProcessId
  if (-not $snap) {
    return [pscustomobject]@{ Owned = $false; Reason = "pid $ProcessId no longer exists" }
  }
  if ($snap.Name -ne $ExpectedName) {
    return [pscustomobject]@{ Owned = $false; Reason = "executable is '$($snap.Name)', expected $ExpectedName" }
  }
  if ([string]::IsNullOrWhiteSpace($snap.CommandLine) -or ($snap.CommandLine -notlike "*$CommandLineMustContain*")) {
    return [pscustomobject]@{ Owned = $false; Reason = 'command line does not contain the ownership marker' }
  }
  if ($StartedAfter -ne [datetime]::MinValue) {
    $started = Convert-MvpCreationDate $snap.CreationDate
    if ($started -and ($started -lt $StartedAfter.AddSeconds(-5))) {
      return [pscustomobject]@{ Owned = $false; Reason = 'process started before this execution marker' }
    }
  }
  return [pscustomobject]@{ Owned = $true; Reason = 'owned'; Snapshot = $snap }
}

function Stop-MvpOwnedProcess {
  param(
    [Parameter(Mandatory)][int]$ProcessId,
    [Parameter(Mandatory)][int]$ExpectedPort,
    [Parameter(Mandatory)][string]$ExpectedName,
    [Parameter(Mandatory)][string]$CommandLineMustContain,
    [datetime]$StartedAfter = [datetime]::MinValue
  )
  $check = Test-MvpOwnedProcess -ProcessId $ProcessId -ExpectedPort $ExpectedPort -ExpectedName $ExpectedName -CommandLineMustContain $CommandLineMustContain -StartedAfter $StartedAfter
  if (-not $check.Owned) {
    throw "Refusing to stop pid=$ProcessId. $($check.Reason)"
  }
  Stop-Process -Id $ProcessId -Force -ErrorAction Stop
}

function Assert-MvpRefusesStalePid {
  param([int]$AlienPid, [int]$ExpectedPort = 8095)
  $before = Get-MvpProcessSnapshot -ProcessId $AlienPid
  if (-not $before) { throw "Alien pid $AlienPid is not running; cannot prove non-kill." }
  $check = Test-MvpOwnedProcess -ProcessId $AlienPid -ExpectedPort $ExpectedPort -ExpectedName 'node.exe' -CommandLineMustContain 'segsense-provider-mock'
  if ($check.Owned) { throw "Stale-pid fixture unexpectedly matched ownership." }
  $after = Get-MvpProcessSnapshot -ProcessId $AlienPid
  if (-not $after) { throw "Alien pid $AlienPid disappeared without an explicit stop." }
  Write-Output "stale-pid-refused pid=$AlienPid still-running=true reason=$($check.Reason)"
}

function Test-MvpOwnedLauncherProcess {
  param(
    [Parameter(Mandatory)][int]$ProcessId,
    [Parameter(Mandatory)][string]$ExpectedName,
    [Parameter(Mandatory)][string]$CommandLineMustContain,
    [datetime]$StartedAfter = [datetime]::MinValue,
    [int[]]$ForbiddenListenPorts = @(8080, 8095, 8088, 5178)
  )
  if (-not (Test-MvpOwnershipMarker $CommandLineMustContain)) {
    return [pscustomobject]@{ Owned = $false; Reason = 'launcher marker is missing or not unique to this execution' }
  }
  if ($ExpectedName -match '[\*\?]' -or $ExpectedName -notmatch '^[A-Za-z0-9._-]+\.exe$') {
    return [pscustomobject]@{ Owned = $false; Reason = 'expected launcher executable is missing or too broad' }
  }
  $snap = Get-MvpProcessSnapshot -ProcessId $ProcessId
  if (-not $snap) {
    return [pscustomobject]@{ Owned = $false; Reason = "launcher pid $ProcessId no longer exists" }
  }
  if ($snap.Name -ne $ExpectedName) {
    return [pscustomobject]@{ Owned = $false; Reason = "launcher executable is '$($snap.Name)', expected $ExpectedName" }
  }
  if ([string]::IsNullOrWhiteSpace($snap.CommandLine) -or ($snap.CommandLine -notlike "*$CommandLineMustContain*")) {
    return [pscustomobject]@{ Owned = $false; Reason = 'launcher command line does not contain the ownership marker' }
  }
  if ($StartedAfter -ne [datetime]::MinValue) {
    $started = Convert-MvpCreationDate $snap.CreationDate
    if ($started -and ($started -lt $StartedAfter.AddSeconds(-5))) {
      return [pscustomobject]@{ Owned = $false; Reason = 'launcher started before this execution marker' }
    }
  }
  foreach ($port in $ForbiddenListenPorts) {
    $listenPid = Get-MvpListenPid -Port $port
    if ($listenPid -eq $ProcessId) {
      return [pscustomobject]@{ Owned = $false; Reason = "pid $ProcessId is the listener on port $port; refusing launcher stop" }
    }
  }
  return [pscustomobject]@{ Owned = $true; Reason = 'owned-launcher'; Snapshot = $snap }
}

function Get-MvpOwnedLedgerPath {
  return (Join-Path $PSScriptRoot '.mvp-logs\owned-run.json')
}

function Get-MvpIsolatedCor016LedgerPath {
  return (Join-Path $PSScriptRoot '.mvp-logs\owned-run-cor016.json')
}

function Convert-MvpLedgerDate {
  param([string]$Iso)
  if ([string]::IsNullOrWhiteSpace($Iso)) { return $null }
  try {
    return [datetime]::Parse($Iso, [cultureinfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::RoundtripKind)
  } catch {
    return $null
  }
}

function New-MvpOwnedLedger {
  param([Parameter(Mandatory)][string]$RunId)
  return [pscustomobject]@{
    schemaVersion = 1
    runId = $RunId
    startedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    targets = @()
  }
}

function Read-MvpOwnedLedger {
  param([Parameter(Mandatory)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  try {
    $raw = [System.IO.File]::ReadAllText($Path)
    if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
    $parsed = $raw | ConvertFrom-Json
    if (-not $parsed) { return $null }
    $parsed.targets = @($parsed.targets)
    return $parsed
  } catch {
    return $null
  }
}

function Save-MvpOwnedLedger {
  param(
    [Parameter(Mandatory)][string]$Path,
    [Parameter(Mandatory)]$Ledger
  )
  $dir = Split-Path $Path -Parent
  if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $payload = [pscustomobject]@{
    schemaVersion = [int]$Ledger.schemaVersion
    runId = [string]$Ledger.runId
    startedAtUtc = [string]$Ledger.startedAtUtc
    targets = @($Ledger.targets)
  }
  $json = $payload | ConvertTo-Json -Depth 8
  $tmp = "$Path.$PID.tmp"
  $utf8 = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($tmp, $json, $utf8)
  Move-Item -LiteralPath $tmp -Destination $Path -Force
}

function Convert-MvpCommandLineExcerpt {
  param([string]$CommandLine)
  if ([string]::IsNullOrWhiteSpace($CommandLine)) { return '' }
  if ($CommandLine.Length -le 480) { return $CommandLine }
  return $CommandLine.Substring(0, 480)
}

function Add-MvpOwnedLedgerTarget {
  param(
    [Parameter(Mandatory)]$Ledger,
    [Parameter(Mandatory)][string]$Role,
    [Parameter(Mandatory)][int]$Port,
    [Parameter(Mandatory)][int]$ListenerPid,
    [Parameter(Mandatory)][string]$Executable,
    [Parameter(Mandatory)][string]$Marker,
    [Parameter(Mandatory)][datetime]$StartedAfter,
    [string]$CommandLineExcerpt = ''
  )
  if (-not (Test-MvpOwnershipMarker $Marker)) {
    throw "Refusing to record ${Role}: marker is not a unique run id."
  }
  $kept = @($Ledger.targets | Where-Object { $_.role -ne $Role })
  $kept += [pscustomobject]@{
    role = $Role
    port = $Port
    listenerPid = $ListenerPid
    executable = $Executable
    marker = $Marker
    commandLineExcerpt = $CommandLineExcerpt
    startedAfterUtc = $StartedAfter.ToUniversalTime().ToString('o')
    recordedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
  }
  $Ledger.targets = $kept
  return $Ledger
}

function Test-MvpOwnedLedgerTarget {
  param($Target)
  if (-not $Target) {
    return [pscustomobject]@{ Owned = $false; Reason = 'ledger target is missing' }
  }
  $marker = [string]$Target.marker
  if (-not (Test-MvpOwnershipMarker $marker)) {
    return [pscustomobject]@{ Owned = $false; Reason = 'ledger marker is missing or not unique to a start' }
  }
  $name = [string]$Target.executable
  $port = 0
  $procId = 0
  try { $port = [int]$Target.port } catch { }
  try { $procId = [int]$Target.listenerPid } catch { }
  if ($port -le 0 -or $procId -le 0 -or [string]::IsNullOrWhiteSpace($name)) {
    return [pscustomobject]@{ Owned = $false; Reason = 'ledger target is missing pid, port, or executable' }
  }
  $startedAfter = Convert-MvpLedgerDate ([string]$Target.startedAfterUtc)
  if (-not $startedAfter) {
    return [pscustomobject]@{ Owned = $false; Reason = 'ledger startedAfterUtc is missing or unreadable' }
  }
  return Test-MvpOwnedProcess -ProcessId $procId -ExpectedPort $port -ExpectedName $name -CommandLineMustContain $marker -StartedAfter $startedAfter
}

function Register-MvpOwnedListener {
  param(
    [Parameter(Mandatory)]$Ledger,
    [Parameter(Mandatory)][string]$Role,
    [Parameter(Mandatory)][int]$Port,
    [Parameter(Mandatory)][string]$ExpectedName,
    [Parameter(Mandatory)][string]$Marker,
    [Parameter(Mandatory)][datetime]$StartedAfter
  )
  $listenPid = Get-MvpListenPid -Port $Port
  if (-not $listenPid) {
    throw "Started $Role but nothing is listening on port $Port. Failing closed; not recording a stop target."
  }
  $check = Test-MvpOwnedProcess -ProcessId $listenPid -ExpectedPort $Port -ExpectedName $ExpectedName -CommandLineMustContain $Marker -StartedAfter $StartedAfter
  if (-not $check.Owned) {
    throw "Started $Role but could not prove listener ownership (pid=$listenPid). $($check.Reason). Failing closed; not recording a stop target. Inspect manually; the process was left intact."
  }
  $excerpt = Convert-MvpCommandLineExcerpt $check.Snapshot.CommandLine
  Add-MvpOwnedLedgerTarget -Ledger $Ledger -Role $Role -Port $Port -ListenerPid $listenPid -Executable $check.Snapshot.Name -Marker $Marker -StartedAfter $StartedAfter -CommandLineExcerpt $excerpt | Out-Null
  Write-Output "owned-listener role=$Role pid=$listenPid port=$Port executable=$($check.Snapshot.Name) marker=$Marker"
  return $listenPid
}

function Invoke-MvpStopOwnedLedger {
  param([Parameter(Mandatory)][string]$LedgerPath)
  if (-not (Test-Path -LiteralPath $LedgerPath)) {
    Write-Output "No owned-run ledger at $LedgerPath; refusing to stop. Inspect listeners manually. pids.txt is not a stop source."
    return
  }
  $ledger = Read-MvpOwnedLedger -Path $LedgerPath
  if (-not $ledger) {
    Write-Output "Owned-run ledger is missing or unreadable; refusing to stop any process."
    return
  }
  $remaining = @()
  foreach ($target in @($ledger.targets)) {
    $role = [string]$target.role
    $procId = 0
    try { $procId = [int]$target.listenerPid } catch { $procId = 0 }
    $check = Test-MvpOwnedLedgerTarget -Target $target
    if (-not $check.Owned) {
      $still = $false
      if ($procId -gt 0) { $still = [bool](Get-Process -Id $procId -ErrorAction SilentlyContinue) }
      Write-Output "stop-result role=$role pid=$procId action=refused still-running=$still reason=$($check.Reason)"
      $remaining += $target
      continue
    }
    try {
      Stop-Process -Id $procId -Force -ErrorAction Stop
    } catch {
      $stillFail = [bool](Get-Process -Id $procId -ErrorAction SilentlyContinue)
      Write-Output "stop-result role=$role pid=$procId action=refused still-running=$stillFail reason=Stop-Process failed"
      $remaining += $target
      continue
    }
    Start-Sleep -Milliseconds 400
    $still = [bool](Get-Process -Id $procId -ErrorAction SilentlyContinue)
    Write-Output "stop-result role=$role pid=$procId action=stopped still-running=$still"
    if ($still) { $remaining += $target }
  }
  if ($remaining.Count -eq 0) {
    Remove-Item -LiteralPath $LedgerPath -Force
    Write-Output 'owned-run ledger cleared (all verified targets stopped)'
  } else {
    $ledger.targets = $remaining
    Save-MvpOwnedLedger -Path $LedgerPath -Ledger $ledger
    Write-Output "owned-run ledger kept with $($remaining.Count) unverified or refused target(s) for manual inspection"
  }
}
