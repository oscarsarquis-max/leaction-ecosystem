#Requires -Version 5.1
# Sobe API e Vite só contra panne_demo. Não lê .env. Não toca no banco panne.
# Por padrão sempre inicia instância nova (não reutiliza só porque /health responde).
param(
    [string]$DatabaseUrl = $env:PANNE_SEED_DATABASE_URL,
    [switch]$ReuseExisting,
    [switch]$Detailed
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "demo-lifecycle.ps1")

$Root = Get-PanneDemoRoot $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Tmp = Get-PanneDemoTmpDir $Root
$ApiPort = 5080
$FePort = 5180
$HealthUrl = "http://127.0.0.1:$ApiPort/health"
$ReadyUrl = "http://127.0.0.1:$ApiPort/ready"
$FeUrl = "http://127.0.0.1:$FePort/entrar"
$AnchorDefault = "2026-08-24"

function Test-LocalHttp([string]$Url) {
    try {
        $code = & curl.exe -s -o NUL -w "%{http_code}" --max-time 3 $Url 2>$null
        return ($code -eq "200")
    } catch {
        return $false
    }
}

function Get-HealthInstanceId([string]$Url) {
    try {
        $raw = & curl.exe -s --max-time 5 $Url 2>$null
        if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
        if ($raw -match '"instance_id"\s*:\s*"([0-9a-fA-F]+)"') {
            return $Matches[1]
        }
        return $null
    } catch {
        return $null
    }
}

function Get-JsonUrl([string]$Url) {
    try {
        $raw = & curl.exe -s --max-time 5 $Url 2>$null
        if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
        return ($raw | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Resolve-DemoUrl([string]$Given) {
    if ($Given) { return $Given }
    if ($env:PANNE_ENV -eq "production") { throw "Recusado: ambiente production." }
    $portLine = @(docker port leaction_db 5432 2>$null | Where-Object { $_ })
    if (-not $portLine -or $portLine.Count -lt 1) {
        throw "Informe PANNE_SEED_DATABASE_URL com o banco panne_demo."
    }
    $first = [string]$portLine[0]
    if ($first -notmatch ":(\d+)\s*$") {
        throw "Não foi possível ler a porta do container leaction_db."
    }
    $port = $Matches[1]
    $user = (docker exec leaction_db printenv POSTGRES_USER).Trim()
    $pass = (docker exec leaction_db printenv POSTGRES_PASSWORD).Trim()
    if (-not $user -or -not $pass) {
        throw "Informe PANNE_SEED_DATABASE_URL com o banco panne_demo."
    }
    return "postgresql+asyncpg://${user}:${pass}@127.0.0.1:${port}/panne_demo"
}

function Assert-PortFreeOrPanne {
    param([int]$Port, [string]$Root)
    $pidVal = Get-PortListenerPid -Port $Port
    if ($null -eq $pidVal) { return }
    $identity = Get-ProcessIdentity -ProcessId $pidVal
    if (Test-PanneDemoProcessIdentity -Identity $identity -Root $Root) {
        $null = Stop-ProvenPanneProcess -ProcessId $pidVal -Root $Root
        Start-Sleep -Milliseconds 400
        $pidVal = Get-PortListenerPid -Port $Port
        if ($null -eq $pidVal) { return }
        $identity = Get-ProcessIdentity -ProcessId $pidVal
    }
    if ($null -ne $pidVal) {
        $report = Format-ProcessReport $identity
        throw @"
Porta :$Port ocupada por processo que não foi comprovado como demo Panne.
Não será encerrado automaticamente.
$report
Encerre esse processo manualmente (se for seguro) e rode start-demo de novo.
"@
    }
}

function Resolve-NpmCmd {
    $NodeDir = Join-Path (Split-Path $Root -Parent) ".tools\node"
    if (Test-Path (Join-Path $NodeDir "npm.cmd")) {
        $env:Path = "$NodeDir;$env:Path"
    }
    foreach ($candidate in @(
            (Join-Path $NodeDir "npm.cmd"),
            "${env:ProgramFiles}\nodejs\npm.cmd",
            "${env:ProgramFiles(x86)}\nodejs\npm.cmd"
        )) {
        if ($candidate -and (Test-Path $candidate)) { return $candidate }
    }
    $whereNpm = @(where.exe npm.cmd 2>$null)
    if ($whereNpm.Count -gt 0) { return $whereNpm[0] }
    throw "npm.cmd nao encontrado. Instale Node.js ou use .tools\node do monorepo."
}

if (-not (Test-Path (Join-Path $Root "backend\app\main.py"))) {
    throw "Diretório Panne inválido: $Root"
}
if ($env:PANNE_ENV -eq "production") {
    throw "Recusado: ambiente production."
}

$Resolved = Resolve-DemoUrl $DatabaseUrl
$LogicalDb = Get-LogicalDatabaseName $Resolved
if ($LogicalDb -eq "panne") {
    throw "Recusado: banco lógico panne."
}
if ($LogicalDb -notlike "*_demo") {
    throw "Recusado: start-demo exige sufixo _demo (obtido: $LogicalDb)."
}

$Anchor = $env:PANNE_DEMO_ANCHOR_DATE
if (-not $Anchor) { $Anchor = $AnchorDefault }

if ($ReuseExisting) {
    $existing = Read-PanneDemoInstance -Root $Root
    $health = Get-JsonUrl $HealthUrl
    if (
        $existing -and $health -and
        $health.ambiente -eq "demo" -and
        $health.demo -and
        $existing.instance_id -and
        $health.demo.instance_id -eq $existing.instance_id -and
        $health.demo.logical_database -eq "panne_demo" -and
        (Test-LocalHttp $ReadyUrl) -and
        (Test-LocalHttp $FeUrl)
    ) {
        Write-Host "Reutilizando instância existente $($existing.instance_id) (-ReuseExisting)."
        Write-Host "Aplicação: $FeUrl"
        exit 0
    }
    Write-Host "ReuseExisting pedido, mas a instância atual não é confiável. Iniciando nova."
}

Write-Host "Garantindo ciclo limpo (stop seguro)..."
& (Join-Path $PSScriptRoot "stop-demo.ps1")
$stopCode = $LASTEXITCODE
if ($stopCode -eq 2) {
    throw "Stop abortou: há processo desconhecido nas portas. Veja a mensagem acima."
}

Assert-PortFreeOrPanne -Port $ApiPort -Root $Root
Assert-PortFreeOrPanne -Port $FePort -Root $Root

$InstanceId = [guid]::NewGuid().ToString("N")
$StartedAt = (Get-Date).ToUniversalTime().ToString("o")
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ApiOut = Join-Path $Tmp "api-$RunStamp.out"
$ApiErr = Join-Path $Tmp "api-$RunStamp.err"
$FeOut = Join-Path $Tmp "fe-$RunStamp.out"
$FeErr = Join-Path $Tmp "fe-$RunStamp.err"
New-Item -ItemType Directory -Force -Path $Tmp | Out-Null

$env:PANNE_ENV = "demo"
$env:PANNE_DATABASE_URL = $Resolved
$env:PANNE_RUNTIME_DATABASE_URL = $Resolved
$env:PANNE_AUTH_VERIFIER = "fake"
$env:PANNE_FAKE_ISSUER = "https://panne.local/fake"
$env:PANNE_AI_GATEWAY = "fake"
$env:PANNE_DEMO_ANCHOR_DATE = $Anchor
$env:PANNE_DEMO_INSTANCE_ID = $InstanceId
$env:PANNE_DEMO_STARTED_AT = $StartedAt
$env:VITE_DEMO_MODE = "1"
$env:VITE_DEMO_ANCHOR_DATE = $Anchor
$env:PANNE_SEED_DATABASE_URL = $Resolved

$Py = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
$NpmCmd = Resolve-NpmCmd

Write-Host "Iniciando API (instancia $InstanceId)..."
$apiLauncher = Start-Process -FilePath $Py -ArgumentList @(
    "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort"
) -WorkingDirectory $Backend -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $ApiOut -RedirectStandardError $ApiErr

$deadline = (Get-Date).AddSeconds(60)
$apiHealth = $null
$readyOk = $false
$seenInstanceId = $null
do {
    if ($apiLauncher.HasExited) {
        throw "API morreu ao iniciar. Veja $ApiErr"
    }
    $seenInstanceId = Get-HealthInstanceId $HealthUrl
    $readyOk = Test-LocalHttp $ReadyUrl
    $apiHealth = Get-JsonUrl $HealthUrl
    if ($seenInstanceId -eq $InstanceId -and $readyOk) { break }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)

if ($seenInstanceId -ne $InstanceId) {
    throw "API nao confirmou instance_id $InstanceId a tempo (obtido: $seenInstanceId, ready=$readyOk). Veja $ApiErr / $ApiOut"
}
if (-not $apiHealth) { $apiHealth = Get-JsonUrl $HealthUrl }
if (-not $apiHealth -or $apiHealth.ambiente -ne "demo") {
    throw "API health sem ambiente demo apos confirmar instance_id."
}
if ($apiHealth.demo.demo_anchor_date -and $apiHealth.demo.demo_anchor_date -ne $Anchor) {
    throw "Ancora divergente: esperada $Anchor, API $($apiHealth.demo.demo_anchor_date)"
}

$apiServerPid = Get-PortListenerPid -Port $ApiPort
if ($null -eq $apiServerPid) { $apiServerPid = $apiLauncher.Id }
$apiIdentity = Get-ProcessIdentity -ProcessId $apiServerPid
if (-not (Test-PanneDemoProcessIdentity -Identity $apiIdentity -Root $Root)) {
    throw "Listener :$ApiPort não passou na prova Panne após o start."
}

Write-Host "Iniciando frontend (npm.cmd)..."
$feLauncher = Start-Process -FilePath $NpmCmd -ArgumentList @("run", "dev") `
    -WorkingDirectory $Frontend -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $FeOut -RedirectStandardError $FeErr

$deadline = (Get-Date).AddSeconds(90)
$feOk = $false
do {
    if ($feLauncher.HasExited) {
        throw "Frontend morreu ao iniciar. Veja $FeErr"
    }
    $feOk = Test-LocalHttp $FeUrl
    if ($feOk) { break }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)

if (-not $feOk) {
    throw "Frontend não respondeu em $FeUrl a tempo. Veja $FeErr / $FeOut"
}

$feServerPid = Get-PortListenerPid -Port $FePort
if ($null -eq $feServerPid) { $feServerPid = $feLauncher.Id }
$feIdentity = Get-ProcessIdentity -ProcessId $feServerPid
if (-not (Test-PanneDemoProcessIdentity -Identity $feIdentity -Root $Root)) {
    throw "Listener :$FePort não passou na prova Panne após o start."
}

$finalHealth = Get-JsonUrl $HealthUrl
if (-not $finalHealth -or -not $finalHealth.demo -or $finalHealth.demo.instance_id -ne $InstanceId) {
    throw "Health final sem instance_id esperado."
}
if (-not (Test-LocalHttp $ReadyUrl)) {
    throw "Ready final falhou."
}

$instance = [pscustomobject]@{
    schema_version   = 1
    instance_id      = $InstanceId
    started_at       = $StartedAt
    root             = $Root
    environment      = "demo"
    logical_database = "panne_demo"
    demo_anchor_date = $Anchor
    api = [pscustomobject]@{
        launcher_pid = $apiLauncher.Id
        server_pid   = $apiServerPid
        start_time   = if ($apiIdentity.StartTime) { $apiIdentity.StartTime.ToString("o") } else { $null }
        command_safe = $apiIdentity.CommandSafe
        process_id_reported = $finalHealth.demo.process_id
    }
    frontend = [pscustomobject]@{
        launcher_pid = $feLauncher.Id
        server_pid   = $feServerPid
        start_time   = if ($feIdentity.StartTime) { $feIdentity.StartTime.ToString("o") } else { $null }
        command_safe = $feIdentity.CommandSafe
        vite_demo_mode = "1"
    }
    ports = [pscustomobject]@{ api = $ApiPort; frontend = $FePort }
    logs = [pscustomobject]@{
        api_out = $ApiOut
        api_err = $ApiErr
        fe_out  = $FeOut
        fe_err  = $FeErr
    }
}

Write-PanneDemoInstance -Root $Root -Instance $instance
Assert-NoSecretInText -Text ((Get-Content (Get-PanneDemoInstancePath $Root) -Raw)) -Label "instance.json"

Write-Host ""
Write-Host "Demo Panne iniciada."
Write-Host "API: nova instância confirmada ($InstanceId)."
Write-Host "Frontend: nova instância confirmada."
Write-Host "Banco: panne_demo"
Write-Host "Referência: $Anchor"
Write-Host "URL: $FeUrl"
Write-Host "Health: $HealthUrl"
Write-Host "Ready: $ReadyUrl"
Write-Host "Logs: $Tmp"
if ($Detailed) {
    Write-Host "API PID launcher/server: $($apiLauncher.Id)/$apiServerPid"
    Write-Host "FE PID launcher/server: $($feLauncher.Id)/$feServerPid"
}
Write-Host "Para encerrar: powershell -File `"$PSScriptRoot\stop-demo.ps1`""
