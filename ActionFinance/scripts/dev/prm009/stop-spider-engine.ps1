$ErrorActionPreference = "Stop"
$listener = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $listener) { Write-Output "SPIDER_ALREADY_DOWN"; exit 0 }
$cim = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
if ($cim.CommandLine -notmatch "SpiderOrchestratorApplication") {
    throw "Porta 8080 não é a engine Spider. Recusando."
}
Stop-Process -Id $listener.OwningProcess
Write-Output "STOPPED_SPIDER pid=$($listener.OwningProcess)"
