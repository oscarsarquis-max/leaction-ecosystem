$ErrorActionPreference = "Stop"

function Get-ActionFinanceRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Read-ActionFinanceEnvFile([string]$path) {
  $map = @{}
  if (-not (Test-Path $path)) {
    throw "Missing $path. Run setup-local.ps1 first."
  }
  Get-Content $path | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $parts = $_.Split('=', 2)
    $map[$parts[0].Trim()] = $parts[1]
  }
  return $map
}

function Get-ActionFinancePostgresName {
  return "actionfinance-postgres-17"
}

function Get-ActionFinanceLegacyPostgresName {
  return "actionfinance-postgres"
}

function Get-ActionFinancePorts {
  return [pscustomobject]@{
    Postgres = [int]($(if ($env:ACTIONFINANCE_POSTGRES_PORT) { $env:ACTIONFINANCE_POSTGRES_PORT } else { 5439 }))
    Backend  = [int]($(if ($env:ACTIONFINANCE_BACKEND_PORT) { $env:ACTIONFINANCE_BACKEND_PORT } else { 8091 }))
    Frontend = [int]($(if ($env:ACTIONFINANCE_FRONTEND_PORT) { $env:ACTIONFINANCE_FRONTEND_PORT } else { 5179 }))
  }
}

function Invoke-ActionFinanceNative {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [string[]]$ArgumentList = @()
  )
  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & $FilePath @ArgumentList
  $code = $LASTEXITCODE
  $ErrorActionPreference = $previous
  if ($code -ne 0) {
    throw "Native command failed: $FilePath $($ArgumentList -join ' ') exit=$code"
  }
}

function Get-ActionFinanceProcessSnapshot([int]$ProcessId) {
  $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if (-not $proc) { return $null }
  $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
  $created = $null
  if ($proc.StartTime) {
    $created = $proc.StartTime.ToUniversalTime()
  }
  return [pscustomobject]@{
    Pid           = $ProcessId
    ProcessName   = $proc.ProcessName
    Path          = $proc.Path
    CommandLine   = $(if ($cim) { [string]$cim.CommandLine } else { "" })
    CreationUtc   = $created
  }
}

function Get-ActionFinanceNormalizedPath([string]$value) {
  if ([string]::IsNullOrWhiteSpace($value)) { return "" }
  return [System.IO.Path]::GetFullPath($value).TrimEnd('\', '/').ToLowerInvariant()
}

function Test-ActionFinancePathInside([string]$child, [string]$parent) {
  if ([string]::IsNullOrWhiteSpace($child) -or [string]::IsNullOrWhiteSpace($parent)) { return $false }
  $childPath = Get-ActionFinanceNormalizedPath $child
  $parentPath = Get-ActionFinanceNormalizedPath $parent
  $sep = [IO.Path]::DirectorySeparatorChar
  return $childPath -eq $parentPath -or $childPath.StartsWith($parentPath + $sep)
}

function Test-ActionFinanceExactCheckout([string]$recorded, [string]$expected) {
  if ([string]::IsNullOrWhiteSpace($recorded) -or [string]::IsNullOrWhiteSpace($expected)) { return $false }
  return (Get-ActionFinanceNormalizedPath $recorded) -eq (Get-ActionFinanceNormalizedPath $expected)
}

function Test-ActionFinanceCheckoutBound([string]$text, [string]$checkoutRoot) {
  if ([string]::IsNullOrWhiteSpace($text) -or [string]::IsNullOrWhiteSpace($checkoutRoot)) { return $false }
  $normalized = $text.Replace('/', '\').ToLowerInvariant()
  $root = (Get-ActionFinanceNormalizedPath $checkoutRoot)
  if ($normalized -eq $root) { return $true }
  $escaped = [regex]::Escape($root)
  return [regex]::IsMatch($normalized, "(?:^|[\s`"'=])$escaped(?:\\|[`"']|\s|$)")
}

function New-ActionFinanceProcessRecord($snap, [string]$BoundPath = "") {
  if (-not $snap) { return $null }
  $commandLine = [string]$snap.CommandLine
  $path = [string]$snap.Path
  if ($BoundPath -and [string]::IsNullOrWhiteSpace($commandLine)) {
    $commandLine = $BoundPath
  }
  if ($BoundPath -and [string]::IsNullOrWhiteSpace($path)) {
    $path = $BoundPath
  }
  return [pscustomobject]@{
    pid         = [int]$snap.Pid
    processName = [string]$snap.ProcessName
    path        = $path
    commandLine = $commandLine
    boundPath   = $BoundPath
    creationUtc = $(if ($snap.CreationUtc) { $snap.CreationUtc.ToString("o") } else { $null })
  }
}

function Test-ActionFinanceRecordedIdentity {
  param(
    [Parameter(Mandatory = $true)]$Record,
    [Parameter(Mandatory = $true)][string]$CheckoutRoot,
    [switch]$AllowTreeChild
  )
  if (-not $Record -or -not $Record.pid) { return $false }
  $snap = Get-ActionFinanceProcessSnapshot ([int]$Record.pid)
  if (-not $snap) { return $false }
  if ($snap.ProcessName -ne [string]$Record.processName) { return $false }
  if ([string]::IsNullOrWhiteSpace([string]$Record.creationUtc)) { return $false }
  $expected = [datetimeoffset]::Parse([string]$Record.creationUtc, [cultureinfo]::InvariantCulture).UtcDateTime
  if (-not $snap.CreationUtc) { return $false }
  if ([math]::Abs(($snap.CreationUtc - $expected).TotalSeconds) -gt 3) { return $false }
  if ($Record.path -and $snap.Path) {
    $recordedPath = Get-ActionFinanceNormalizedPath ([string]$Record.path)
    $livePath = Get-ActionFinanceNormalizedPath ([string]$snap.Path)
    if ($recordedPath -and $livePath -and $recordedPath -ne $livePath) { return $false }
  }
  $liveBound = (Test-ActionFinanceCheckoutBound $snap.CommandLine $CheckoutRoot) -or (Test-ActionFinanceCheckoutBound $snap.Path $CheckoutRoot)
  $recordedBound = (Test-ActionFinanceCheckoutBound $Record.commandLine $CheckoutRoot) -or (Test-ActionFinanceCheckoutBound $Record.path $CheckoutRoot) -or (Test-ActionFinanceCheckoutBound $Record.boundPath $CheckoutRoot)
  if ($liveBound -or $recordedBound) { return $true }
  return [bool]$AllowTreeChild
}

function Test-ActionFinanceRecordMatchesLaunch {
  param(
    [Parameter(Mandatory = $true)]$Metadata,
    [Parameter(Mandatory = $true)]$Record
  )
  $canonical = Get-ActionFinanceRoot
  if (-not (Test-ActionFinanceExactCheckout ([string]$Metadata.checkoutRoot) $canonical)) {
    return $false
  }
  $allowChild = $false
  if ($Metadata.server -and $Record.pid -and ([int]$Record.pid -eq [int]$Metadata.server.pid)) { $allowChild = $true }
  if ($Metadata.children) {
    foreach ($child in @($Metadata.children)) {
      if ($child.pid -and ([int]$child.pid -eq [int]$Record.pid)) { $allowChild = $true }
    }
  }
  return (Test-ActionFinanceRecordedIdentity -Record $Record -CheckoutRoot $canonical -AllowTreeChild:$allowChild)
}

function Test-ActionFinanceOwnedProcess {
  param(
    [Parameter(Mandatory = $true)]$Metadata
  )
  foreach ($item in (Get-ActionFinanceRecordedTargets $Metadata)) {
    if (Test-ActionFinanceRecordMatchesLaunch -Metadata $Metadata -Record $item) { return $true }
  }
  return $false
}

function Test-ActionFinanceMetadataComplete($Metadata) {
  if (-not $Metadata) { return $false }
  if ([string]::IsNullOrWhiteSpace([string]$Metadata.kind)) { return $false }
  if ([string]::IsNullOrWhiteSpace([string]$Metadata.checkoutRoot)) { return $false }
  $targets = Get-ActionFinanceRecordedTargets $Metadata
  if (-not $targets -or $targets.Count -eq 0) { return $false }
  foreach ($target in $targets) {
    if (-not $target.pid) { return $false }
    if ([string]::IsNullOrWhiteSpace([string]$target.processName)) { return $false }
    if ([string]::IsNullOrWhiteSpace([string]$target.creationUtc)) { return $false }
  }
  return $true
}

function Test-ActionFinanceListenerInLaunch {
  param(
    [Parameter(Mandatory = $true)]$Metadata,
    [Parameter(Mandatory = $true)][int]$Port
  )
  $listener = Get-ActionFinanceListenerPid $Port
  if (-not $listener) { return $false }
  foreach ($item in (Get-ActionFinanceRecordedTargets $Metadata)) {
    if ([int]$item.pid -eq $listener -and (Test-ActionFinanceRecordMatchesLaunch -Metadata $Metadata -Record $item)) {
      return $true
    }
  }
  return $false
}

function Get-ActionFinanceProcessTree([int]$RootPid) {
  $items = @()
  $queue = [System.Collections.Generic.Queue[int]]::new()
  $seen = [System.Collections.Generic.HashSet[int]]::new()
  $queue.Enqueue($RootPid)
  while ($queue.Count -gt 0) {
    $current = $queue.Dequeue()
    if (-not $seen.Add($current)) { continue }
    $snap = Get-ActionFinanceProcessSnapshot $current
    if (-not $snap) { continue }
    $items += $snap
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$current" -ErrorAction SilentlyContinue | ForEach-Object {
      $queue.Enqueue([int]$_.ProcessId)
    }
  }
  return $items
}

function Read-ActionFinancePidMetadata([string]$kind) {
  $file = Join-Path $PSScriptRoot ".pids\$kind.json"
  if (-not (Test-Path $file)) { return $null }
  return (Get-Content $file -Raw | ConvertFrom-Json)
}

function Save-ActionFinanceLaunchRecord($record) {
  $dir = Join-Path $PSScriptRoot ".pids"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $kind = [string]$record.kind
  ($record | ConvertTo-Json -Depth 6) | Set-Content -Path (Join-Path $dir "$kind.json") -Encoding utf8
  $recordedPid = if ($record.wrapper -and $record.wrapper.pid) { $record.wrapper.pid } elseif ($record.server -and $record.server.pid) { $record.server.pid } else { 0 }
  Set-Content -Path (Join-Path $dir "$kind.pid") $recordedPid
}

function New-ActionFinanceLaunchRecord {
  param(
    [Parameter(Mandatory = $true)][string]$Kind,
    [Parameter(Mandatory = $true)][string]$LaunchId,
    [Parameter(Mandatory = $true)][string]$CheckoutRoot,
    [Parameter(Mandatory = $true)][int]$WrapperPid,
    [Parameter(Mandatory = $true)][int]$Port,
    [string]$BoundPath = ""
  )
  $wrapper = New-ActionFinanceProcessRecord (Get-ActionFinanceProcessSnapshot $WrapperPid) $BoundPath
  if (-not $wrapper) { throw "Wrapper $WrapperPid disappeared before launch metadata could be recorded." }
  $record = [pscustomobject]@{
    kind         = $Kind
    launchId     = $LaunchId
    checkoutRoot = $CheckoutRoot
    wrapper      = $wrapper
    server       = $null
    children     = @()
    port         = $Port
    recordedAtUtc = [datetime]::UtcNow.ToString("o")
  }
  Save-ActionFinanceLaunchRecord $record
  return $record
}

function Update-ActionFinanceLaunchChildren($record) {
  if (-not $record.wrapper) { return $record }
  $wrapperAlive = Test-ActionFinanceRecordedIdentity -Record $record.wrapper -CheckoutRoot $record.checkoutRoot
  if (-not $wrapperAlive) { return $record }
  $tree = Get-ActionFinanceProcessTree ([int]$record.wrapper.pid)
  $children = @()
  foreach ($item in $tree) {
    if ($item.Pid -eq [int]$record.wrapper.pid) { continue }
    $children += (New-ActionFinanceProcessRecord $item)
  }
  $record.children = $children
  return $record
}

function Set-ActionFinanceLaunchServer {
  param(
    [Parameter(Mandatory = $true)]$Record,
    [Parameter(Mandatory = $true)][int]$Port
  )
  $updated = Update-ActionFinanceLaunchChildren $Record
  $listener = Get-ActionFinanceListenerPid $Port
  if (-not $listener) { return $updated }
  $known = @()
  if ($updated.wrapper) { $known += $updated.wrapper }
  if ($updated.children) { $known += $updated.children }
  $match = $known | Where-Object { [int]$_.pid -eq $listener } | Select-Object -First 1
  if ($match) {
    $updated.server = $match
  } else {
    $snap = Get-ActionFinanceProcessSnapshot $listener
    if ($snap -and ((Test-ActionFinanceCheckoutBound $snap.CommandLine $updated.checkoutRoot) -or (Test-ActionFinanceCheckoutBound $snap.Path $updated.checkoutRoot))) {
      $inTree = $false
      if ($updated.wrapper -and (Test-ActionFinanceRecordedIdentity -Record $updated.wrapper -CheckoutRoot $updated.checkoutRoot)) {
        $tree = Get-ActionFinanceProcessTree ([int]$updated.wrapper.pid)
        $inTree = [bool]($tree | Where-Object { $_.Pid -eq $listener })
      }
      if ($inTree) {
        $updated.server = New-ActionFinanceProcessRecord $snap
      }
    }
  }
  Save-ActionFinanceLaunchRecord $updated
  return $updated
}

function Remove-ActionFinancePidMetadata([string]$kind) {
  $dir = Join-Path $PSScriptRoot ".pids"
  foreach ($name in @("$kind.json", "$kind.pid")) {
    $path = Join-Path $dir $name
    if (Test-Path $path) { Remove-Item $path -Force }
  }
}

function Get-ActionFinanceListenerPid([int]$port) {
  $conn = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if (-not $conn) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -First 1
  }
  if ($conn) { return [int]$conn.OwningProcess }
  return $null
}

function Test-ActionFinanceHttpOk([string]$url) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
    return $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
  } catch {
    return $false
  }
}

function Wait-ActionFinanceHttpOk {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$TimeoutSeconds = 90
  )
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    if (Test-ActionFinanceHttpOk $Url) { return $true }
    Start-Sleep -Milliseconds 500
  } while ((Get-Date) -lt $deadline)
  return $false
}

function Test-DockerContainerExists([string]$name) {
  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  docker inspect $name 2>$null | Out-Null
  $exists = $LASTEXITCODE -eq 0
  $ErrorActionPreference = $previous
  return $exists
}

function Get-ActionFinanceContainerLabels([string]$name) {
  $json = docker inspect --format "{{json .Config.Labels}}" $name 2>$null
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json) -or $json -eq "null") {
    return $null
  }
  return ($json | ConvertFrom-Json)
}

function Test-ActionFinanceOwnedContainer([string]$name) {
  $labels = Get-ActionFinanceContainerLabels $name
  if (-not $labels) { return $false }
  if ($labels.'com.actionfinance.project' -eq "actionfinance") { return $true }
  return ($labels.'com.docker.compose.project' -eq "actionfinance" -and $labels.'com.docker.compose.service' -eq "postgres")
}

function Get-ActionFinanceRecordedTargets($metadata) {
  $targets = @()
  if ($metadata.server) { $targets += $metadata.server }
  if ($metadata.children) { $targets += $metadata.children }
  if ($metadata.wrapper) { $targets += $metadata.wrapper }
  elseif ($metadata.pid) {
    $targets += [pscustomobject]@{
      pid = $metadata.pid
      processName = $metadata.processName
      path = $metadata.path
      commandLine = $metadata.commandLine
      creationUtc = $metadata.creationUtc
    }
  }
  return $targets
}

function Stop-ActionFinanceOwnedTree {
  param(
    [Parameter(Mandatory = $true)]$Metadata
  )
  if (-not (Test-ActionFinanceMetadataComplete $Metadata)) {
    throw "REFUSED_STOP kind=$($Metadata.kind) incomplete-metadata"
  }
  if (-not (Test-ActionFinanceExactCheckout ([string]$Metadata.checkoutRoot) (Get-ActionFinanceRoot))) {
    throw "REFUSED_STOP kind=$($Metadata.kind) checkout-not-canonical"
  }
  $targets = Get-ActionFinanceRecordedTargets $Metadata
  if (-not $targets -or $targets.Count -eq 0) {
    throw "REFUSED_STOP kind=$($Metadata.kind) no-recorded-targets"
  }
  $confirmed = @()
  foreach ($target in $targets) {
    if (Test-ActionFinanceRecordMatchesLaunch -Metadata $Metadata -Record $target) {
      $confirmed += $target
    }
  }
  if ($confirmed.Count -eq 0) {
    throw "REFUSED_STOP kind=$($Metadata.kind) launchId=$($Metadata.launchId) ownership-unconfirmed-or-reused"
  }
  $stopped = 0
  $refused = @()
  foreach ($target in (@($confirmed) | Sort-Object { [int]$_.pid } -Descending)) {
    if (-not (Get-ActionFinanceProcessSnapshot ([int]$target.pid))) { continue }
    if (-not (Test-ActionFinanceRecordMatchesLaunch -Metadata $Metadata -Record $target)) {
      $refused += [int]$target.pid
      continue
    }
    Stop-Process -Id ([int]$target.pid) -Force -ErrorAction SilentlyContinue
    $stopped++
  }
  if ($stopped -eq 0) {
    throw "REFUSED_STOP kind=$($Metadata.kind) launchId=$($Metadata.launchId) identity-changed-before-stop pids=$($refused -join ',')"
  }
}
