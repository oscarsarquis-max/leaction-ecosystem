# Isolated COR_016 stack on distinct ports. Does not touch meeting listeners
# :8095/:8080/:8088/:5178 or volume segsense_pgdata. Ledger is owned-run-cor016.json.
# Occupied isolated ports are refused, never killed.
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $root 'segsense-provider-mock'))) {
  $root = 'C:\Projetos'
}
$logDir = Join-Path $root 'segsense\scripts\.mvp-logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

. (Join-Path $PSScriptRoot '_mvp-process-safety.ps1')
. (Join-Path $PSScriptRoot '_load-mvp-secrets.ps1')
. (Join-Path $PSScriptRoot '_mvp-preflight.ps1')

$mockPort = 19095
$spiderPort = 19080
$bffPort = 19088
$fePort = 15178
$pgPort = 15437
$containerName = 'segsense-postgres-isolated-cor016'
$volumeName = 'segsense_pgdata_isolated_cor016'

$runId = [guid]::NewGuid().ToString('N')
$marker = "segsense.isolated.stack=$runId"
$ledgerPath = Get-MvpIsolatedCor016LedgerPath
$script:ledger = New-MvpOwnedLedger -RunId $runId

function Test-Listen([int]$Port) {
  return [bool](Get-MvpListenPid -Port $Port)
}

function Assert-IsolatedPortFree([int]$Port, [string]$Role) {
  if (Test-Listen $Port) {
    throw "NÃO COMPROVADO: isolated port $Port ($Role) is already in use. Refusing to kill or reuse a foreign listener."
  }
}

function Start-LoggedProcess($Name, $WorkDir, $File, $ArgList) {
  $out = Join-Path $logDir "cor016-$Name.out.log"
  $err = Join-Path $logDir "cor016-$Name.err.log"
  $proc = Start-Process -FilePath $File -ArgumentList $ArgList -WorkingDirectory $WorkDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
  Write-Output "started isolated $Name launcherPid=$($proc.Id) (launcher is not a stop target)"
  return $proc
}

function Wait-ForCheck {
  param([scriptblock]$Check, [int]$Seconds, [string]$Name)
  $deadline = (Get-Date).AddSeconds($Seconds)
  $last = $null
  while ((Get-Date) -lt $deadline) {
    try {
      & $Check
      return
    } catch {
      $last = $_
    }
    Start-Sleep -Seconds 2
  }
  throw "Timed out waiting for isolated $Name. $($last.Exception.Message)"
}

foreach ($occupied in @(
    @{ Port = $mockPort; Role = 'mock' },
    @{ Port = $spiderPort; Role = 'spider' },
    @{ Port = $bffPort; Role = 'segsense-bff' },
    @{ Port = $fePort; Role = 'segsense-fe' }
  )) {
  Assert-IsolatedPortFree -Port $occupied.Port -Role $occupied.Role
}

if (Test-Listen $pgPort) {
  $names = docker ps --filter "name=^${containerName}$" --format '{{.Names}}' 2>$null
  if ($names -ne $containerName) {
    throw "NÃO COMPROVADO: port $pgPort is in use and is not container $containerName. Meeting volume segsense_pgdata was not touched."
  }
  Write-Output "reusing isolated postgres container $containerName on :$pgPort (volume $volumeName)"
} else {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'NÃO COMPROVADO: docker is not available to create the isolated postgres volume.'
  }
  $existing = docker ps -a --filter "name=^${containerName}$" --format '{{.Names}}' 2>$null
  if ($existing -eq $containerName) {
    Write-Output "starting existing isolated postgres container $containerName"
    docker start $containerName | Out-Null
  } else {
    Write-Output "creating isolated postgres container $containerName volume=$volumeName (not segsense_pgdata)"
    docker volume create $volumeName | Out-Null
    docker run -d --name $containerName `
      -e POSTGRES_DB=segsense `
      -e POSTGRES_USER=segsense `
      -e POSTGRES_PASSWORD=segsense_local_dev `
      -e TZ=UTC `
      -p "127.0.0.1:${pgPort}:5432" `
      -v "${volumeName}:/var/lib/postgresql" `
      postgres:18.6 | Out-Null
  }
  Wait-ForCheck -Check {
    $ready = docker exec $containerName pg_isready -U segsense -d segsense
    if ($ready -notmatch 'accepting connections') { throw "isolated postgres not ready: $ready" }
  } -Seconds 40 -Name 'isolated-postgres'
}

$env:PORT = "$mockPort"
$env:SPIDER_SEGSENSE_MOCK_BASE_URL = "http://127.0.0.1:$mockPort"
$env:SPIDER_SEGSENSE_DEMO_CREDENTIAL_REF = 'local-demo-segsense'
$env:SEGSENSE_SPIDER_DEMO_BASE_URL = "http://127.0.0.1:$spiderPort"
$env:SEGSENSE_SPIDER_DEMO_CREDENTIAL_REF = 'local-demo-segsense'
$env:SEGSENSE_BACKEND_PORT = "$bffPort"
$env:SEGSENSE_DATASOURCE_URL = "jdbc:postgresql://127.0.0.1:$pgPort/segsense"
$env:SEGSENSE_DATASOURCE_USERNAME = 'segsense'
$env:SEGSENSE_DATASOURCE_PASSWORD = 'segsense_local_dev'
$env:SEGSENSE_FRONTEND_ORIGIN = "http://127.0.0.1:$fePort,http://localhost:$fePort"
$env:SEGSENSE_PUBLIC_BASE_URL = "http://127.0.0.1:$fePort"
$env:SEGSENSE_DEMO_GOVERNED_PORTS = "$fePort,5178"
$env:VITE_DEV_PORT = "$fePort"
$env:VITE_API_BASE_URL = "http://127.0.0.1:$bffPort"
$env:MVP_MOCK_BASE_URL = "http://127.0.0.1:$mockPort"
$env:MVP_SPIDER_BASE_URL = "http://127.0.0.1:$spiderPort"
$env:MVP_SEGSENSE_BASE_URL = "http://127.0.0.1:$bffPort"

$feScript = Join-Path $PSScriptRoot 'mvp-fe-dev.mjs'

$startedAfter = Get-Date
Start-LoggedProcess 'mock' (Join-Path $root 'segsense-provider-mock') 'node' @('server.js', "--$marker") | Out-Null
Wait-ForCheck -Check { Test-MvpMockIdentity } -Seconds 20 -Name 'mock'
Register-MvpOwnedListener -Ledger $script:ledger -Role 'mock' -Port $mockPort -ExpectedName 'node.exe' -Marker $marker -StartedAfter $startedAfter | Out-Null
Save-MvpOwnedLedger -Path $ledgerPath -Ledger $script:ledger

$startedAfter = Get-Date
Start-LoggedProcess 'spider' (Join-Path $root 'spider\backend') 'cmd.exe' @('/c', "mvn -q spring-boot:run -Dspring-boot.run.profiles=local-demo -Dspring-boot.run.arguments=--server.port=$spiderPort -Dspring-boot.run.jvmArguments=-D$marker") | Out-Null
Wait-ForCheck -Check { Test-MvpSpiderSatelliteAuth } -Seconds 120 -Name 'spider'
Register-MvpOwnedListener -Ledger $script:ledger -Role 'spider' -Port $spiderPort -ExpectedName 'java.exe' -Marker $marker -StartedAfter $startedAfter | Out-Null
Save-MvpOwnedLedger -Path $ledgerPath -Ledger $script:ledger

$startedAfter = Get-Date
Start-LoggedProcess 'segsense-bff' (Join-Path $root 'segsense\backend') 'cmd.exe' @('/c', "mvnw.cmd -q spring-boot:run -Dspring-boot.run.profiles=local -Dspring-boot.run.jvmArguments=-D$marker -Dspring-boot.run.arguments=--server.port=$bffPort") | Out-Null
Wait-ForCheck -Check { Test-MvpSegSenseIdentity } -Seconds 120 -Name 'segsense-bff'
Register-MvpOwnedListener -Ledger $script:ledger -Role 'segsense-bff' -Port $bffPort -ExpectedName 'java.exe' -Marker $marker -StartedAfter $startedAfter | Out-Null
Save-MvpOwnedLedger -Path $ledgerPath -Ledger $script:ledger

$startedAfter = Get-Date
Start-LoggedProcess 'segsense-fe' (Join-Path $root 'segsense\frontend') 'node' @($feScript, "--$marker") | Out-Null
Wait-ForCheck -Check { if (-not (Get-MvpListenPid -Port $fePort)) { throw 'isolated frontend is not listening' } } -Seconds 40 -Name 'segsense-fe'
Register-MvpOwnedListener -Ledger $script:ledger -Role 'segsense-fe' -Port $fePort -ExpectedName 'node.exe' -Marker $marker -StartedAfter $startedAfter | Out-Null
Save-MvpOwnedLedger -Path $ledgerPath -Ledger $script:ledger
Write-Output "isolated owned-run ledger written (gitignored) runId=$runId targets=$(@($script:ledger.targets).Count)"
Write-Output 'pids.txt is not written and is not a stop source'
Invoke-MvpPreflight
Write-Output "isolatedFe=http://127.0.0.1:$fePort/demonstracao/mvp-integrado"
Write-Output "isolatedHealth mock=:$mockPort/health spider=:$spiderPort/actuator/health segsense=:$bffPort/api/v1/system/info"
Write-Output "stop with: .\stop-mvp-demo.ps1 -LedgerPath `"$ledgerPath`""
