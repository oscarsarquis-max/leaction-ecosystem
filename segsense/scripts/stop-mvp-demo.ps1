# Stops only processes recorded by start-mvp-demo.ps1. Does not touch Docker volumes.
$logDir = Join-Path $PSScriptRoot '.mvp-logs'
$pidsFile = Join-Path $logDir 'pids.txt'
if (-not (Test-Path $pidsFile)) {
  Write-Output 'No PID file; nothing to stop.'
  exit 0
}
Get-Content $pidsFile | ForEach-Object {
  if ($_ -match '=(\d+)$') {
    $procId = [int]$Matches[1]
    try {
      Stop-Process -Id $procId -Force -ErrorAction Stop
      Write-Output "stopped pid=$procId"
    } catch {
      Write-Output "pid=$procId already gone"
    }
  }
}
Remove-Item $pidsFile -Force
