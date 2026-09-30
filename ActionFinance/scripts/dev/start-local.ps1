$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_lib.ps1")

$root = Get-ActionFinanceRoot
Set-Location $root
$local = Join-Path $root ".local"
$logs = Join-Path $PSScriptRoot ".logs"
New-Item -ItemType Directory -Force -Path $logs, (Join-Path $PSScriptRoot ".pids") | Out-Null

$secrets = Read-ActionFinanceEnvFile (Join-Path $local "secrets.env")
$tokens = Read-ActionFinanceEnvFile (Join-Path $local "demo-tokens.env")
$ports = Get-ActionFinancePorts

$env:ACTIONFINANCE_BOOTSTRAP_PASSWORD = $secrets.ACTIONFINANCE_BOOTSTRAP_PASSWORD
$env:ACTIONFINANCE_POSTGRES_PORT = "$($ports.Postgres)"
$env:ACTIONFINANCE_BACKEND_PORT = "$($ports.Backend)"
$env:ACTIONFINANCE_FRONTEND_PORT = "$($ports.Frontend)"

$legacy = Get-ActionFinanceLegacyPostgresName
if (Test-DockerContainerExists $legacy) {
  if (Test-ActionFinanceOwnedContainer $legacy) {
    Invoke-ActionFinanceNative -FilePath "docker" -ArgumentList @("stop", $legacy)
    Write-Output "STOPPED_LEGACY $legacy volume actionfinance_pgdata preserved"
  } else {
    throw "Legacy container $legacy exists and is not owned by ActionFinance. Refusing to start."
  }
}

$postgresName = Get-ActionFinancePostgresName
if ((Test-DockerContainerExists $postgresName) -and -not (Test-ActionFinanceOwnedContainer $postgresName)) {
  throw "Port or container name $postgresName is not owned by ActionFinance. Refusing to start."
}

function Assert-PortFreeOrOwned([int]$port, $meta, [string]$kind) {
  $listener = Get-ActionFinanceListenerPid $port
  if (-not $listener) { return }
  if ($meta -and (Test-ActionFinanceListenerInLaunch -Metadata $meta -Port $port)) { return }
  throw "Port $port is occupied by pid=$listener which is not a recorded ActionFinance $kind launch. Refusing to start."
}

function Wait-OwnedHttp {
  param(
    [Parameter(Mandatory = $true)][string]$Kind,
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][int]$Port,
    [int]$TimeoutSeconds = 120
  )
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    $record = Read-ActionFinancePidMetadata $Kind
    if ($record) {
      $null = Set-ActionFinanceLaunchServer -Record $record -Port $Port
    }
    if (Test-ActionFinanceHttpOk $Url) { return $true }
    Start-Sleep -Milliseconds 500
  } while ((Get-Date) -lt $deadline)
  return $false
}

Invoke-ActionFinanceNative -FilePath "docker" -ArgumentList @("compose", "--project-directory", $root, "up", "-d", "postgres")

$backendUrl = "http://127.0.0.1:$($ports.Backend)/actuator/health/liveness"
$frontendUrl = "http://127.0.0.1:$($ports.Frontend)/"
$backendMeta = Read-ActionFinancePidMetadata "backend"
$frontendMeta = Read-ActionFinancePidMetadata "frontend"
$backendOwned = $backendMeta -and (Test-ActionFinanceOwnedProcess -Metadata $backendMeta)
$frontendOwned = $frontendMeta -and (Test-ActionFinanceOwnedProcess -Metadata $frontendMeta)
$backendHealthy = Test-ActionFinanceHttpOk $backendUrl
$frontendHealthy = Test-ActionFinanceHttpOk $frontendUrl
$backendListenerOwned = $backendMeta -and (Test-ActionFinanceListenerInLaunch -Metadata $backendMeta -Port $ports.Backend)
$frontendListenerOwned = $frontendMeta -and (Test-ActionFinanceListenerInLaunch -Metadata $frontendMeta -Port $ports.Frontend)

if ($backendHealthy -and $frontendHealthy -and $backendListenerOwned -and $frontendListenerOwned) {
  $backendPid = if ($backendMeta.server) { $backendMeta.server.pid } elseif ($backendMeta.wrapper) { $backendMeta.wrapper.pid } else { $backendMeta.pid }
  $frontendPid = if ($frontendMeta.server) { $frontendMeta.server.pid } elseif ($frontendMeta.wrapper) { $frontendMeta.wrapper.pid } else { $frontendMeta.pid }
  Write-Output "ALREADY_RUNNING backend_pid=$backendPid frontend_pid=$frontendPid launch=$($backendMeta.launchId)"
  Write-Output "UI $frontendUrl"
  Write-Output "API http://127.0.0.1:$($ports.Backend)/api/v1/system/info"
  exit 0
}

Assert-PortFreeOrOwned $ports.Backend $backendMeta "backend"
Assert-PortFreeOrOwned $ports.Frontend $frontendMeta "frontend"

$started = @()
try {
  if (-not ($backendOwned -and $backendHealthy)) {
    if ($backendOwned -and -not $backendHealthy) {
      if (-not (Wait-OwnedHttp -Kind "backend" -Url $backendUrl -Port $ports.Backend -TimeoutSeconds 120)) {
        throw "Recorded backend launch did not become ready at $backendUrl"
      }
    } else {
      if ($backendMeta -and -not $backendOwned) {
        Write-Output "STALE_METADATA backend ignored launchId=$($backendMeta.launchId)"
      }
      $env:SPRING_PROFILES_ACTIVE = "local-demo"
      $env:ACTIONFINANCE_DEMO_AUTH_ENABLED = "true"
      $env:ACTIONFINANCE_RUNTIME_PASSWORD = $secrets.ACTIONFINANCE_RUNTIME_PASSWORD
      $env:ACTIONFINANCE_MIGRATOR_PASSWORD = $secrets.ACTIONFINANCE_MIGRATOR_PASSWORD
      $env:ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A = $tokens.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A
      $env:ACTIONFINANCE_DEMO_TOKEN_VIEWER_A = $tokens.ACTIONFINANCE_DEMO_TOKEN_VIEWER_A
      $env:ACTIONFINANCE_DEMO_TOKEN_VIEWER_B = $tokens.ACTIONFINANCE_DEMO_TOKEN_VIEWER_B
      $backend = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile","-File",(Join-Path $PSScriptRoot "run-backend.ps1")) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs "backend.out.log") -RedirectStandardError (Join-Path $logs "backend.err.log") -PassThru
      $launchId = [guid]::NewGuid().ToString("N")
      $record = New-ActionFinanceLaunchRecord -Kind "backend" -LaunchId $launchId -CheckoutRoot $root -WrapperPid $backend.Id -Port $ports.Backend -BoundPath (Join-Path $PSScriptRoot "run-backend.ps1")
      $started += $record
    }
  }

  if (-not ($frontendOwned -and $frontendHealthy)) {
    if ($frontendOwned -and -not $frontendHealthy) {
      if (-not (Wait-OwnedHttp -Kind "frontend" -Url $frontendUrl -Port $ports.Frontend -TimeoutSeconds 60)) {
        throw "Recorded frontend launch did not become ready at $frontendUrl"
      }
    } else {
      if ($frontendMeta -and -not $frontendOwned) {
        Write-Output "STALE_METADATA frontend ignored launchId=$($frontendMeta.launchId)"
      }
      $frontend = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile","-File",(Join-Path $PSScriptRoot "run-frontend.ps1")) -WorkingDirectory (Join-Path $root "frontend") -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs "frontend.out.log") -RedirectStandardError (Join-Path $logs "frontend.err.log") -PassThru
      $launchId = [guid]::NewGuid().ToString("N")
      $record = New-ActionFinanceLaunchRecord -Kind "frontend" -LaunchId $launchId -CheckoutRoot $root -WrapperPid $frontend.Id -Port $ports.Frontend -BoundPath (Join-Path $PSScriptRoot "run-frontend.ps1")
      $started += $record
    }
  }

  if (-not (Wait-OwnedHttp -Kind "backend" -Url $backendUrl -Port $ports.Backend -TimeoutSeconds 120)) {
    throw "Backend liveness did not become ready at $backendUrl"
  }
  if (-not (Wait-OwnedHttp -Kind "frontend" -Url $frontendUrl -Port $ports.Frontend -TimeoutSeconds 60)) {
    throw "Frontend did not become ready at $frontendUrl"
  }

  $backendMeta = Read-ActionFinancePidMetadata "backend"
  $frontendMeta = Read-ActionFinancePidMetadata "frontend"
  $backendPid = if ($backendMeta.server) { $backendMeta.server.pid } elseif ($backendMeta.wrapper) { $backendMeta.wrapper.pid } else { $backendMeta.pid }
  $frontendPid = if ($frontendMeta.server) { $frontendMeta.server.pid } elseif ($frontendMeta.wrapper) { $frontendMeta.wrapper.pid } else { $frontendMeta.pid }
  Write-Output "STARTED backend_pid=$backendPid frontend_pid=$frontendPid launch=$($backendMeta.launchId)"
  Write-Output "UI $frontendUrl"
  Write-Output "API http://127.0.0.1:$($ports.Backend)/api/v1/system/info"
} catch {
  foreach ($meta in $started) {
    try { Stop-ActionFinanceOwnedTree -Metadata $meta } catch { Write-Output $_.Exception.Message }
    Remove-ActionFinancePidMetadata $meta.kind
  }
  throw
}
