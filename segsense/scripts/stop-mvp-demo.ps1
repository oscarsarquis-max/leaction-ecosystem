# Stops only listeners recorded in the owned-run ledger after the same identity
# check used at start (PID + port + executable + unique marker + start time).
# Does not read pids.txt, does not match broad command-line globs, does not touch
# Docker/volumes, and does not stop a process when any evidence is missing or
# divergent. Wrappers (Maven cmd, npm) are not stop targets.
param(
  [string]$LedgerPath = ''
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_mvp-process-safety.ps1')
if ([string]::IsNullOrWhiteSpace($LedgerPath)) {
  $LedgerPath = Get-MvpOwnedLedgerPath
}
Write-Output "stop-mvp-demo ledger=$LedgerPath"
Invoke-MvpStopOwnedLedger -LedgerPath $LedgerPath
