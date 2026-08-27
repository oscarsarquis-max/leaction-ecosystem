#Requires -Version 5.1
# Encerra a demo Panne com prova de identidade. Idempotente. Nao mata desconhecidos.
param(
    [switch]$Detailed
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "demo-lifecycle.ps1")

$Root = Get-PanneDemoRoot $PSScriptRoot
$ApiPort = 5080
$FePort = 5180
$results = @()

function Write-StopLine([string]$Message) {
    Write-Host $Message
}

$instance = Read-PanneDemoInstance -Root $Root
if ($null -eq $instance) {
    Write-StopLine "Nenhum registro de demo encontrado."
} else {
    Write-StopLine "Encerrando instancia registrada ($($instance.instance_id))."
    $targets = @()
    foreach ($role in @("api", "frontend")) {
        $block = $instance.$role
        if ($null -eq $block) { continue }
        foreach ($field in @("server_pid", "launcher_pid")) {
            $pidVal = $block.$field
            if ($pidVal) { $targets += [int]$pidVal }
        }
    }
    $targets = @($targets | Select-Object -Unique)
    foreach ($pidVal in $targets) {
        $expectedStart = [datetime]::MinValue
        if ($instance.api -and ($pidVal -eq $instance.api.server_pid -or $pidVal -eq $instance.api.launcher_pid) -and $instance.api.start_time) {
            try { $expectedStart = [datetime]::Parse($instance.api.start_time) } catch { }
        }
        if ($instance.frontend -and ($pidVal -eq $instance.frontend.server_pid -or $pidVal -eq $instance.frontend.launcher_pid) -and $instance.frontend.start_time) {
            try { $expectedStart = [datetime]::Parse($instance.frontend.start_time) } catch { }
        }
        $results += ,(Stop-ProvenPanneProcess -ProcessId $pidVal -Root $Root -ExpectedStartTime $expectedStart)
    }
}

foreach ($port in @($ApiPort, $FePort)) {
    $listener = Get-PortListenerPid -Port $port
    if ($null -eq $listener) {
        $results += ,[pscustomobject]@{ Pid = $null; Result = "porta_liberada"; Detail = ":$port" }
        continue
    }
    $identity = Get-ProcessIdentity -ProcessId $listener
    if (Test-PanneDemoProcessIdentity -Identity $identity -Root $Root) {
        $results += ,(Stop-ProvenPanneProcess -ProcessId $listener -Root $Root)
        Start-Sleep -Milliseconds 300
        $again = Get-PortListenerPid -Port $port
        if ($null -eq $again) {
            $results += ,[pscustomobject]@{ Pid = $listener; Result = "porta_liberada"; Detail = ":$port apos orfao" }
        } else {
            $results += ,[pscustomobject]@{ Pid = $again; Result = "porta_ocupada"; Detail = ":$port ainda escuta" }
        }
    } else {
        $results += ,[pscustomobject]@{
            Pid      = $listener
            Result   = "desconhecido"
            Detail   = "Porta :$port ocupada por processo nao Panne - nao encerrado. $(Format-ProcessReport $identity)"
            Identity = $identity
        }
    }
}

$unknownPort = @($results | Where-Object { $_.Result -eq "desconhecido" -and $_.Detail -like "Porta*" })
$unknownPid = @($results | Where-Object { $_.Result -eq "desconhecido" -and $_.Detail -notlike "Porta*" })

foreach ($row in $results) {
    $line = "[$($row.Result)] $($row.Detail)"
    if ($Detailed -and $row.Identity) {
        $line += " | $(Format-ProcessReport $row.Identity)"
    }
    Write-StopLine $line
}

$apiLeft = Get-PortListenerPid -Port $ApiPort
$feLeft = Get-PortListenerPid -Port $FePort

if ($unknownPort.Count -gt 0) {
    Write-StopLine "Ha processo(s) desconhecido(s) nas portas da demo. Nao foram encerrados."
    Write-StopLine "Libere manualmente ou encerre o servico correto e rode stop-demo de novo."
    exit 2
}

if ($null -eq $apiLeft -and $null -eq $feLeft) {
    Clear-PanneDemoInstanceFiles -Root $Root
    Write-StopLine "Demo encerrada. Portas 5080 e 5180 liberadas."
    if ($unknownPid.Count -gt 0) {
        Write-StopLine "Nota: PID(s) registrados sem prova Panne foram ignorados (portas ja livres)."
    }
    exit 0
}

$apiId = if ($apiLeft) { Get-ProcessIdentity -ProcessId $apiLeft } else { $null }
$feId = if ($feLeft) { Get-ProcessIdentity -ProcessId $feLeft } else { $null }
$apiPanne = if ($apiId) { Test-PanneDemoProcessIdentity -Identity $apiId -Root $Root } else { $false }
$fePanne = if ($feId) { Test-PanneDemoProcessIdentity -Identity $feId -Root $Root } else { $false }
if ($apiPanne -or $fePanne) {
    Write-StopLine "Ainda ha listener Panne residual. Tente stop-demo novamente."
    exit 1
}

Write-StopLine "Portas ainda ocupadas por processo nao Panne - nao encerrado."
exit 2
