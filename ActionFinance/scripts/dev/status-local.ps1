$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "_lib.ps1")

$ports = Get-ActionFinancePorts
$postgresName = Get-ActionFinancePostgresName
$owned = Test-ActionFinanceOwnedContainer $postgresName
$state = docker inspect -f "{{.State.Status}}" $postgresName 2>$null
Write-Output "container name=$postgresName owned=$owned state=$state port=$($ports.Postgres)"

foreach ($kind in @("backend", "frontend")) {
  $meta = Read-ActionFinancePidMetadata $kind
  if (-not $meta) {
    Write-Output "$kind metadata=absent"
    continue
  }
  $ownedProc = Test-ActionFinanceOwnedProcess -Metadata $meta
  Write-Output "$kind pid=$($meta.pid) owned=$ownedProc processName=$($meta.processName)"
}

$backendUrl = "http://127.0.0.1:$($ports.Backend)/api/v1/system/info"
$liveUrl = "http://127.0.0.1:$($ports.Backend)/actuator/health/liveness"
$uiUrl = "http://127.0.0.1:$($ports.Frontend)/"
Write-Output "api info=$(if (Test-ActionFinanceHttpOk $backendUrl) { 'up' } else { 'down' })"
Write-Output "api liveness=$(if (Test-ActionFinanceHttpOk $liveUrl) { 'up' } else { 'down' })"
Write-Output "ui=$(if (Test-ActionFinanceHttpOk $uiUrl) { 'up' } else { 'down' })"
