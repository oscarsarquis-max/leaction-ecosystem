$ErrorActionPreference = 'Stop'
$ledger = Join-Path $PSScriptRoot '.logs\owned.json'
if (-not (Test-Path $ledger)) {
  Write-Output "no owned ledger — not stopping any process"
  exit 0
}
$owned = Get-Content $ledger -Raw | ConvertFrom-Json
foreach ($name in @('bff', 'fe', 'mock')) {
  $pidValue = $owned.$name
  if (-not $pidValue) { continue }
  try {
    $proc = Get-Process -Id $pidValue -ErrorAction Stop
    Stop-Process -Id $pidValue -ErrorAction SilentlyContinue
    Write-Output "stopped owned $name pid=$pidValue"
    if ($proc.Id) { }
  } catch {
    Write-Output "owned $name pid=$pidValue already gone"
  }
}
Remove-Item $ledger -Force
Write-Output "left sibling services untouched"
