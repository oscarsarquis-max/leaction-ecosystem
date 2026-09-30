$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_lib.ps1")

$root = Get-ActionFinanceRoot
$refused = $false

foreach ($kind in @("backend", "frontend")) {
  $meta = Read-ActionFinancePidMetadata $kind
  if (-not $meta) {
    Write-Output "STOPPED_ALREADY $kind metadata-absent"
    continue
  }
  $targets = Get-ActionFinanceRecordedTargets $meta
  $anyAlive = $false
  $anyConfirmed = $false
  $aliveUnconfirmed = @()
  foreach ($target in $targets) {
    $snap = Get-ActionFinanceProcessSnapshot ([int]$target.pid)
    if (-not $snap) { continue }
    $anyAlive = $true
    if (Test-ActionFinanceRecordMatchesLaunch -Metadata $meta -Record $target) {
      $anyConfirmed = $true
    } else {
      $aliveUnconfirmed += $target.pid
    }
  }
  if (-not $anyAlive) {
    Write-Output "STOPPED_ALREADY $kind launchId=$($meta.launchId) recorded-targets-absent"
    Remove-ActionFinancePidMetadata $kind
    continue
  }
  if (-not $anyConfirmed) {
    $refused = $true
    Write-Output "REFUSED_STOP kind=$kind launchId=$($meta.launchId) ownership-unconfirmed-or-reused pids=$($aliveUnconfirmed -join ',')"
    continue
  }
  try {
    Stop-ActionFinanceOwnedTree -Metadata $meta
    Write-Output "stopped $kind launchId=$($meta.launchId) recorded-targets-validated"
    Remove-ActionFinancePidMetadata $kind
  } catch {
    $refused = $true
    Write-Output $_.Exception.Message
  }
}

$postgresName = Get-ActionFinancePostgresName
if (Test-DockerContainerExists $postgresName) {
  if (Test-ActionFinanceOwnedContainer $postgresName) {
    Invoke-ActionFinanceNative -FilePath "docker" -ArgumentList @("compose", "--project-directory", $root, "stop", "postgres")
    Write-Output "STOPPED $postgresName container kept; volume actionfinance_pgdata_17 preserved"
  } else {
    $refused = $true
    Write-Output "REFUSED_STOP postgres ownership-unconfirmed"
  }
} else {
  Write-Output "STOPPED_ALREADY postgres container-absent"
}

if ($refused) { exit 2 }
