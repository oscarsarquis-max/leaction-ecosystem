# Reinicia um serviço local do Action Hub (marketplace | gateway).
#
# Uso:
#   .\scripts\dev\restart-hub-service.ps1 -Service marketplace
#   .\scripts\dev\restart-hub-service.ps1 -Service gateway
#
# Saída: JSON em uma linha no stdout (para a API /api/sys/mitigate consumir).

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('marketplace', 'gateway')]
    [string]$Service
)

$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\_hub-dev-common.ps1"

function Stop-ServicePort {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [string[]]$CommandLinePatterns = @()
    )

    $pids = @()
    try {
        $pids = @(
            Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique
        )
    } catch {
        $pids = @()
    }
    if (-not $pids -or $pids.Count -eq 0) {
        $lines = netstat -ano | Select-String ":$Port\s+.*LISTENING\s+(\d+)"
        foreach ($m in $lines) {
            if ($m -match 'LISTENING\s+(\d+)\s*$') {
                $pids += [int]$Matches[1]
            }
        }
        $pids = $pids | Select-Object -Unique
    }

    foreach ($procId in $pids) {
        if (-not $procId -or $procId -eq 0) { continue }
        Write-HubWarn "Encerrando :$Port (PID $procId)"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }

    foreach ($pat in $CommandLinePatterns) {
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -and ($_.CommandLine -match $pat) } |
            ForEach-Object {
                Write-HubWarn "Encerrando órfão PID $($_.ProcessId) ($pat)"
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
    }

    Start-Sleep -Seconds 1
}

function Emit-Result {
    param(
        [bool]$Ok,
        [string]$ServiceName,
        [string]$Message,
        [int]$ExitCode = 0
    )
    $payload = @{
        ok      = $Ok
        service = $ServiceName
        message = $Message
        at      = (Get-Date).ToString('o')
    } | ConvertTo-Json -Compress
    Write-Output $payload
    exit $ExitCode
}

Ensure-HubNodeOnPath
Ensure-DevLogsDir
$dbUrl = Get-HubDatabaseUrl

try {
    if ($Service -eq 'marketplace') {
        Stop-ServicePort -Port 4012 -CommandLinePatterns @(
            'leaction-platform\\backend\\run\.py',
            'leaction-platform/backend/run\.py'
        )

        $venvPython = Join-Path $HubRoot 'backend\.venv\Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $venvPython)) {
            Emit-Result -Ok $false -ServiceName $Service -Message "Venv ausente: $venvPython" -ExitCode 2
        }

        # Garante deps críticas (mitiga ModuleNotFoundError recorrente)
        $pip = Join-Path $HubRoot 'backend\.venv\Scripts\pip.exe'
        if (Test-Path -LiteralPath $pip) {
            Write-HubInfo 'Sincronizando requirements do marketplace (rápido)...'
            & $pip install -r (Join-Path $HubRoot 'backend\requirements.txt') --quiet
        }

        Write-HubInfo 'Iniciando Marketplace :4012'
        $null = Start-HubLoggedProcess -Name 'marketplace' `
            -WorkingDirectory $HubRoot `
            -FilePath $venvPython `
            -ArgumentList @((Join-Path $HubRoot 'backend\run.py')) `
            -Environment @{
                MARKETPLACE_PORT           = '4012'
                DATABASE_URL               = $dbUrl
                MARKETPLACE_DATABASE_URL   = $dbUrl
                ML_PUBLIC_BASE_URL         = 'http://127.0.0.1:4000'
                FLASK_DEBUG                = '1'
                MARKETPLACE_USE_RELOADER   = '0'
            }

        $healthOk = Wait-HttpOk -Url 'http://127.0.0.1:4012/api/marketplace/health' -TimeoutSec 45
        $offersOk = Wait-HttpOk -Url 'http://127.0.0.1:4012/api/marketplace/offers' -TimeoutSec 20
        $vitrineOk = Wait-HttpOk -Url 'http://127.0.0.1:4012/api/marketplace/vitrine' -TimeoutSec 25

        if (-not $healthOk) {
            Emit-Result -Ok $false -ServiceName $Service -Message 'Marketplace não respondeu no health após reinício. Veja .dev-logs/marketplace.err.log' -ExitCode 3
        }
        if (-not $offersOk -or -not $vitrineOk) {
            Emit-Result -Ok $false -ServiceName $Service -Message "Health OK, mas rotas funcionais falharam (offers=$offersOk vitrine=$vitrineOk)" -ExitCode 4
        }

        Emit-Result -Ok $true -ServiceName $Service -Message 'Marketplace reiniciado (health + offers + vitrine OK)'
    }

    if ($Service -eq 'gateway') {
        Stop-ServicePort -Port 4001 -CommandLinePatterns @(
            'gateway-api\\server\.js',
            'gateway-api/server\.js'
        )

        $gatewayDir = Join-Path $HubRoot 'services\gateway-api'
        Write-HubInfo 'Iniciando Gateway :4001'
        $null = Start-HubLoggedProcess -Name 'gateway' `
            -WorkingDirectory $gatewayDir `
            -FilePath 'node' `
            -ArgumentList @('server.js') `
            -Environment @{
                NODE_ENV = 'development'
            }

        if (-not (Wait-HttpOk -Url 'http://127.0.0.1:4001/health' -TimeoutSec 40)) {
            Emit-Result -Ok $false -ServiceName $Service -Message 'Gateway não respondeu no health após reinício. Veja .dev-logs/gateway.err.log' -ExitCode 3
        }

        Emit-Result -Ok $true -ServiceName $Service -Message 'Gateway reiniciado (health OK)'
    }
} catch {
    Emit-Result -Ok $false -ServiceName $Service -Message $_.Exception.Message -ExitCode 1
}
