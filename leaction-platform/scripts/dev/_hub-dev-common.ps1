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
