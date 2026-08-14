# Shared helpers for Action Hub local orchestration (leaction-platform only).

$ErrorActionPreference = 'Stop'

$script:HubRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script:RepoToolsNode = Join-Path $HubRoot '..\.tools\node'
$script:DevLogs = Join-Path $HubRoot '.dev-logs'
$script:HubPorts = @(4000, 4001, 4012)

function Write-HubInfo([string]$Message) {
    Write-Host "[hub-dev] $Message" -ForegroundColor Cyan
}

function Write-HubOk([string]$Message) {
    Write-Host "[hub-dev] $Message" -ForegroundColor Green
}

function Write-HubWarn([string]$Message) {
    Write-Host "[hub-dev] $Message" -ForegroundColor Yellow
}

function Write-HubErr([string]$Message) {
    Write-Host "[hub-dev] $Message" -ForegroundColor Red
}

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key
    )
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trim = $line.Trim()
        if (-not $trim -or $trim.StartsWith('#')) { continue }
        if ($trim -match "^\s*$([regex]::Escape($Key))\s*=\s*(.*)$") {
            $value = $Matches[1].Trim()
            if (
                ($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'"))
            ) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            return $value
        }
    }
    return $null
}

function Get-HubDatabaseUrl {
    $rootEnv = Join-Path $HubRoot '.env'
    $url = Get-DotEnvValue -Path $rootEnv -Key 'DATABASE_URL'
    if (-not $url) {
        $url = Get-DotEnvValue -Path $rootEnv -Key 'MARKETPLACE_DATABASE_URL'
    }
    if (-not $url) {
        throw "DATABASE_URL ausente em $rootEnv"
    }
    return $url
}

function Get-DatabaseHostPortFromUrl([string]$DatabaseUrl) {
    # postgresql://user:pass@host:port/db
    if ($DatabaseUrl -match '@([^/?#]+)') {
        $hostPort = $Matches[1]
        if ($hostPort -match '^([^:]+):(\d+)$') {
            return @{ Host = $Matches[1]; Port = [int]$Matches[2] }
        }
        return @{ Host = $hostPort; Port = 5432 }
    }
    throw "nao foi possivel extrair host/porta de DATABASE_URL"
}

function Ensure-HubNodeOnPath {
    $toolsNode = (Resolve-Path $script:RepoToolsNode -ErrorAction SilentlyContinue)
    if ($toolsNode) {
        $env:Path = "$($toolsNode.Path);$env:Path"
    }
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) {
        throw "Node.js nao encontrado. Use o Node do repo (.tools/node) ou instale Node 20+."
    }
    $version = & node -v
    Write-HubInfo "Node $version ($($node.Source))"
    if ($version -match '^v(\d+)\.') {
        $major = [int]$Matches[1]
        if ($major -lt 20) {
            Write-HubWarn "Node $version é antigo; o Hub foi validado com Node 20+."
        }
    }
}

function Ensure-DevLogsDir {
    if (-not (Test-Path -LiteralPath $script:DevLogs)) {
        New-Item -ItemType Directory -Path $script:DevLogs | Out-Null
    }
}

function Stop-PortListeners {
    param([int[]]$Ports = $script:HubPorts)

    foreach ($port in $Ports) {
        $pids = @()
        try {
            $pids = @(
                Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                    Select-Object -ExpandProperty OwningProcess -Unique
            )
        } catch {
            $pids = @()
        }

        # Fallback via netstat (alguns ambientes bloqueiam Get-NetTCPConnection)
        if (-not $pids -or $pids.Count -eq 0) {
            $lines = netstat -ano | Select-String ":$port\s+.*LISTENING\s+(\d+)"
            foreach ($m in $lines) {
                if ($m -match 'LISTENING\s+(\d+)\s*$') {
                    $pids += [int]$Matches[1]
                }
            }
            $pids = $pids | Select-Object -Unique
        }

        foreach ($procId in $pids) {
            if (-not $procId -or $procId -eq 0) { continue }
            try {
                $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                $name = if ($proc) { $proc.ProcessName } else { '?' }
                Write-HubWarn "Liberando :$port (PID $procId / $name)"
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            } catch {
                Write-HubWarn "nao foi possivel matar PID $procId em :$port"
            }
        }
    }

    # Reloader Flask deixa orfaos run.py mesmo após matar o listener
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and (
                $_.CommandLine -match 'leaction-platform\\backend\\run\.py' -or
                $_.CommandLine -match 'leaction-platform/backend/run\.py' -or
                $_.CommandLine -match 'gateway-api\\server\.js' -or
                $_.CommandLine -match 'gateway-api/server\.js' -or
                $_.CommandLine -match 'next dev -p 4000'
            )
        } |
        ForEach-Object {
            Write-HubWarn "Encerrando processo órfão PID $($_.ProcessId)"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }

    Start-Sleep -Seconds 1
}

function Test-TcpPortOpen {
    param(
        [string]$HostName = '127.0.0.1',
        [Parameter(Mandatory = $true)][int]$Port,
        [int]$TimeoutMs = 1500
    )
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($HostName, $Port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if (-not $ok) {
            $client.Close()
            return $false
        }
        $client.EndConnect($iar)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Wait-HttpOk {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSec = 45,
        [int[]]$AcceptStatus = @(200),
        # Timeout por tentativa HTTP (offers/vitrine ML podem passar de 5s)
        [int]$RequestTimeoutSec = 3
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $last = $null
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $RequestTimeoutSec
            if ($AcceptStatus -contains [int]$resp.StatusCode) {
                return $true
            }
            $last = "HTTP $($resp.StatusCode)"
        } catch {
            $ex = $_.Exception
            if ($ex.Response -and $AcceptStatus -contains [int]$ex.Response.StatusCode) {
                return $true
            }
            $last = $ex.Message
        }
        Start-Sleep -Milliseconds 700
    }
    Write-HubErr "Timeout esperando $Url ($last)"
    return $false
}

function Ensure-HubPostgres {
    $dbUrl = Get-HubDatabaseUrl
    $hp = Get-DatabaseHostPortFromUrl $dbUrl
    $hostName = $hp.Host
    if ($hostName -in @('localhost', '127.0.0.1')) {
        $hostName = '127.0.0.1'
    }

    Write-HubInfo "Postgres alvo: $($hp.Host):$($hp.Port)"

    if (-not (Test-TcpPortOpen -HostName $hostName -Port $hp.Port)) {
        Write-HubWarn "Postgres nao responde em $($hp.Host):$($hp.Port) - tentando docker compose up -d db"
        Push-Location $HubRoot
        try {
            docker compose up -d db
        } finally {
            Pop-Location
        }
        $ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            if (Test-TcpPortOpen -HostName $hostName -Port $hp.Port) {
                $ready = $true
                break
            }
            Start-Sleep -Seconds 1
        }
        if (-not $ready) {
            throw "Postgres indisponivel em $($hp.Host):$($hp.Port). Confira o container leaction_db e o DATABASE_URL."
        }
    }

    Write-HubOk "Postgres OK em $($hp.Host):$($hp.Port)"
    return $dbUrl
}

function Start-HubLoggedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [hashtable]$Environment = @{}
    )

    Ensure-DevLogsDir
    $stdout = Join-Path $script:DevLogs "$Name.out.log"
    $stderr = Join-Path $script:DevLogs "$Name.err.log"
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $stdout -Value "`n==== start $stamp ====`n"
    Add-Content -LiteralPath $stderr -Value "`n==== start $stamp ====`n"

    foreach ($key in $Environment.Keys) {
        Set-Item -Path "Env:$key" -Value ([string]$Environment[$key])
    }

    $proc = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru `
        -WindowStyle Hidden

    Write-HubInfo "$Name PID $($proc.Id) -> logs .dev-logs/$Name.*.log"
    return $proc
}

function Get-HttpStatusCode {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSec = 8,
        [hashtable]$Headers = @{}
    )
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -Headers $Headers
        return [int]$resp.StatusCode
    } catch {
        if ($_.Exception.Response) {
            return [int]$_.Exception.Response.StatusCode
        }
        return $null
    }
}

# Rota do EcosystemMonitor — 401 (sem token) ou 200 (com admin) = OK; 404 = cache Next quebrado.
function Test-HubMonitorRouteReady {
    param(
        [string]$Url = 'http://127.0.0.1:4000/api/sys/status',
        [int]$TimeoutSec = 45
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $last = $null
    while ((Get-Date) -lt $deadline) {
        $code = Get-HttpStatusCode -Url $Url -TimeoutSec 5
        $last = $code
        if ($code -eq 401 -or $code -eq 200) { return $true }
        if ($code -eq 404) { return $false }
        Start-Sleep -Milliseconds 700
    }
    Write-HubErr "Timeout esperando rota do monitor $Url (ultimo HTTP $last)"
    return $false
}

function Clear-ActionHubNextDevCache {
    $feDir = Join-Path $HubRoot 'frontend\action-hub'
    $devCache = Join-Path $feDir '.next\dev'
    if (Test-Path -LiteralPath $devCache) {
        Write-HubWarn "Limpando cache Turbopack quebrado: $devCache"
        Remove-Item -LiteralPath $devCache -Recurse -Force -ErrorAction SilentlyContinue
        return $true
    }
    return $false
}

function Start-ActionHubFrontendDev {
    $feDir = Join-Path $HubRoot 'frontend\action-hub'
    if (-not (Test-Path (Join-Path $feDir 'node_modules'))) {
        Write-HubWarn "Instalando deps do frontend..."
        Push-Location $feDir
        try { npm install } finally { Pop-Location }
    }
    Ensure-DevLogsDir
    $feOut = Join-Path $script:DevLogs 'action-hub.out.log'
    $feErr = Join-Path $script:DevLogs 'action-hub.err.log'
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $feOut -Value "`n==== start $stamp ====`n"
    Add-Content -LiteralPath $feErr -Value "`n==== start $stamp ====`n"
    $feCmd = "npm run dev 1>>`"$feOut`" 2>>`"$feErr`""
    $null = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList @('/c', $feCmd) `
        -WorkingDirectory $feDir `
        -WindowStyle Hidden
    Write-HubInfo "action-hub -> logs .dev-logs/action-hub.*.log"
}

# Valida o mesmo endpoint do painel /dashboard/monitor.
# - Sempre: rota /api/sys/status responde (nao 404).
# - Com HUB_DEV_MONITOR_PASSWORD (ou HUB_ADMIN_DEV_PASSWORD): login + todos UP.
function Assert-HubMonitorStatus {
    param(
        [switch]$AllowHealFrontend,
        [switch]$StrictServicesUp
    )

    $statusUrl = 'http://127.0.0.1:4000/api/sys/status'
    Write-HubInfo "Validando monitor (/api/sys/status)..."

    $routeOk = Test-HubMonitorRouteReady -Url $statusUrl -TimeoutSec 30
    if (-not $routeOk) {
        $code = Get-HttpStatusCode -Url $statusUrl -TimeoutSec 5
        if ($code -eq 404 -and $AllowHealFrontend) {
            Write-HubWarn "Monitor retornou 404 — cache Next provavelmente corrompido. Recuperando FE..."
            Stop-PortListeners -Ports @(4000)
            Start-Sleep -Seconds 1
            $null = Clear-ActionHubNextDevCache
            Start-ActionHubFrontendDev
            if (-not (Wait-HttpOk -Url 'http://127.0.0.1:4000/api/health' -TimeoutSec 90)) {
                Write-HubErr "FE nao voltou apos limpar cache. Veja .dev-logs/action-hub.err.log"
                return $false
            }
            $routeOk = Test-HubMonitorRouteReady -Url $statusUrl -TimeoutSec 45
        }
    }

    if (-not $routeOk) {
        $code = Get-HttpStatusCode -Url $statusUrl -TimeoutSec 5
        Write-HubErr "Rota do monitor indisponivel (HTTP $code). UI em /dashboard/monitor ficara toda 'Fora'."
        Write-HubErr "Tente: remover frontend/action-hub/.next/dev e .\scripts\dev\start-hub.ps1 -ForceRestart"
        return $false
    }
    Write-HubOk "Rota do monitor OK (HTTP 401 sem sessao = esperado)"

    $rootEnv = Join-Path $HubRoot '.env'
    $feEnv = Join-Path $HubRoot 'frontend\action-hub\.env.local'
    $email = (
        $env:HUB_DEV_MONITOR_EMAIL,
        (Get-DotEnvValue -Path $rootEnv -Key 'HUB_DEV_MONITOR_EMAIL'),
        (Get-DotEnvValue -Path $feEnv -Key 'HUB_DEV_MONITOR_EMAIL'),
        'admin@actionhub.com.br'
    ) | Where-Object { $_ } | Select-Object -First 1
    $password = (
        $env:HUB_DEV_MONITOR_PASSWORD,
        $env:HUB_ADMIN_DEV_PASSWORD,
        (Get-DotEnvValue -Path $rootEnv -Key 'HUB_DEV_MONITOR_PASSWORD'),
        (Get-DotEnvValue -Path $rootEnv -Key 'HUB_ADMIN_DEV_PASSWORD'),
        (Get-DotEnvValue -Path $feEnv -Key 'HUB_DEV_MONITOR_PASSWORD')
    ) | Where-Object { $_ } | Select-Object -First 1

    if (-not $password) {
        Write-HubWarn "Sem HUB_DEV_MONITOR_PASSWORD no .env — pulando probe autenticado dos 5 servicos do monitor."
        Write-HubWarn "Defina no .env do Hub para checagem completa a cada start."
        return -not $StrictServicesUp
    }

    try {
        $loginBody = @{ email = $email; password = $password } | ConvertTo-Json -Compress
        $login = Invoke-RestMethod -Uri 'http://127.0.0.1:4001/auth/login' `
            -Method POST -ContentType 'application/json' -Body $loginBody -TimeoutSec 15
        $token = $login.token
        if (-not $token) { $token = $login.access_token }
        if (-not $token) {
            Write-HubErr "Login monitor falhou para $email (sem token)."
            return $false
        }
    } catch {
        Write-HubErr "Login monitor falhou ($email): $($_.Exception.Message)"
        return $false
    }

    try {
        $headers = @{ Authorization = "Bearer $token"; Accept = 'application/json' }
        $services = Invoke-RestMethod -Uri $statusUrl -Headers $headers -TimeoutSec 90
    } catch {
        Write-HubErr "GET /api/sys/status autenticado falhou: $($_.Exception.Message)"
        return $false
    }

    if (-not ($services -is [System.Array])) {
        Write-HubErr "Resposta do monitor invalida (esperado array)."
        return $false
    }

    $failed = 0
    foreach ($svc in $services) {
        $name = [string]$svc.name
        $st = [string]$svc.status
        $detail = [string]$svc.detail
        if ($st -eq 'UP') {
            Write-HubOk ("Monitor {0,-28} UP  {1}" -f $name, $detail)
        } else {
            Write-HubErr ("Monitor {0,-28} {1}  {2}" -f $name, $st, $detail)
            $failed++
        }
    }

    if ($failed -gt 0) {
        Write-HubErr "$failed servico(s) do monitor nao estao UP."
        return $false
    }
    Write-HubOk "Monitor completo: $($services.Count) servico(s) UP."
    return $true
}
