#Requires -Version 5.1
# Funções compartilhadas do ciclo start/stop da demo Panne (R026-012).
# Dot-source apenas. Não matar processos sem prova de identidade Panne.

function Get-PanneDemoRoot {
    param([string]$ScriptsDevDir = $PSScriptRoot)
    return (Resolve-Path (Join-Path $ScriptsDevDir "..\..")).Path
}

function Get-PanneDemoTmpDir {
    param([string]$Root)
    return (Join-Path $Root ".tmp-demo")
}

function Get-PanneDemoInstancePath {
    param([string]$Root)
    return (Join-Path (Get-PanneDemoTmpDir $Root) "instance.json")
}

function Get-PanneDemoLegacyPidPath {
    param([string]$Root)
    return (Join-Path (Get-PanneDemoTmpDir $Root) "pids.json")
}

function ConvertTo-SanitizedCommand {
    param([AllowNull()][string]$CommandLine)
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $null }
    $safe = $CommandLine
    # Oculta credenciais em URLs postgresql://user:pass@host
    $safe = [regex]::Replace($safe, '(?i)(postgresql(?:\+\w+)?://)([^:@/\s]+):([^@/\s]+)@', '$1***:***@')
    $safe = [regex]::Replace($safe, '(?i)(password|passwd|secret|token)=([^\s&;]+)', '$1=***')
    return $safe
}

function Get-LogicalDatabaseName {
    param([string]$DatabaseUrl)
    if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) { return $null }
    if ($DatabaseUrl -match '/([^/?]+)(\?|$)') {
        return $Matches[1]
    }
    return $null
}

function Get-ProcessIdentity {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    $proc = $null
    try {
        $proc = Get-Process -Id $ProcessId -ErrorAction Stop
    } catch {
        return $null
    }
    $cim = $null
    try {
        $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    } catch { }
    $path = $null
    if ($proc.Path) { $path = $proc.Path }
    elseif ($cim -and $cim.ExecutablePath) { $path = $cim.ExecutablePath }
    $cmd = if ($cim) { $cim.CommandLine } else { $null }
    $parent = if ($cim) { [int]$cim.ParentProcessId } else { $null }
    return [pscustomobject]@{
        Pid           = $ProcessId
        Name          = $proc.ProcessName
        StartTime     = $proc.StartTime
        Path          = $path
        CommandLine   = $cmd
        CommandSafe   = (ConvertTo-SanitizedCommand $cmd)
        ParentProcessId = $parent
    }
}

function Test-PanneDemoProcessIdentity {
    <#
      .SYNOPSIS
        Prova que o processo pertence à demo Panne sob $Root.
      Não basta ocupar 5080/5180.
    #>
    param(
        [Parameter(Mandatory = $true)]$Identity,
        [Parameter(Mandatory = $true)][string]$Root
    )
    if ($null -eq $Identity) { return $false }
    $rootNorm = ($Root.TrimEnd('\') -replace '/', '\').ToLowerInvariant()
    $hay = @()
    if ($Identity.Path) { $hay += $Identity.Path }
    if ($Identity.CommandLine) { $hay += $Identity.CommandLine }
    $blob = ($hay -join " ").ToLowerInvariant() -replace '/', '\'
    if ($blob -notlike "*$rootNorm*") { return $false }

    $backend = (Join-Path $Root "backend").ToLowerInvariant() -replace '/', '\'
    $frontend = (Join-Path $Root "frontend").ToLowerInvariant() -replace '/', '\'
    $isApi = ($blob -like "*$backend*") -and (
        $blob -match 'uvicorn' -or $blob -match 'app\.main:app' -or $blob -match '-m\s+uvicorn'
    )
    $isFe = ($blob -like "*$frontend*") -and (
        $blob -match 'vite' -or $blob -match 'npm(\.cmd)?\s+run\s+dev' -or $blob -match 'node\.exe'
    )
    # npm.cmd launcher: working dir / path under frontend + run dev
    if (-not $isFe -and ($blob -like "*$frontend*") -and ($blob -match 'npm') -and ($blob -match 'dev')) {
        $isFe = $true
    }
    return [bool]($isApi -or $isFe)
}

function Get-PortListenerPid {
    param([Parameter(Mandatory = $true)][int]$Port)
    $rows = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if ($rows.Count -eq 0) { return $null }
    return [int]$rows[0].OwningProcess
}

function Get-ChildProcessIds {
    param([Parameter(Mandatory = $true)][int]$ParentId)
    $children = @()
    try {
        $rows = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ParentId" -ErrorAction SilentlyContinue
        foreach ($row in @($rows)) {
            $cid = [int]$row.ProcessId
            $children += $cid
            $children += @(Get-ChildProcessIds -ParentId $cid)
        }
    } catch { }
    return $children
}

function Stop-ProvenPanneProcess {
    param(
        [Parameter(Mandatory = $true)][int]$ProcessId,
        [Parameter(Mandatory = $true)][string]$Root,
        [datetime]$ExpectedStartTime = [datetime]::MinValue,
        [double]$StartSkewSeconds = 3
    )
    $identity = Get-ProcessIdentity -ProcessId $ProcessId
    if ($null -eq $identity) {
        return [pscustomobject]@{ Pid = $ProcessId; Result = "ja_ausente"; Detail = "PID inexistente" }
    }
    if ($ExpectedStartTime -ne [datetime]::MinValue -and $identity.StartTime) {
        $delta = [math]::Abs(($identity.StartTime - $ExpectedStartTime).TotalSeconds)
        if ($delta -gt $StartSkewSeconds) {
            if (-not (Test-PanneDemoProcessIdentity -Identity $identity -Root $Root)) {
                return [pscustomobject]@{
                    Pid    = $ProcessId
                    Result = "divergente"
                    Detail = "PID reutilizado por processo não Panne ($($identity.Name))"
                    Identity = $identity
                }
            }
        }
    }
    if (-not (Test-PanneDemoProcessIdentity -Identity $identity -Root $Root)) {
        return [pscustomobject]@{
            Pid      = $ProcessId
            Result   = "desconhecido"
            Detail   = "Sem prova Panne; não encerrado"
            Identity = $identity
        }
    }
    $tree = @(Get-ChildProcessIds -ParentId $ProcessId) + @($ProcessId)
    # Filhos primeiro (ordem reversa de descoberta já é DFS; inverter para folhas→raiz)
    [array]::Reverse($tree)
    foreach ($procId in $tree) {
        $childId = Get-ProcessIdentity -ProcessId $procId
        if ($null -eq $childId) { continue }
        if (-not (Test-PanneDemoProcessIdentity -Identity $childId -Root $Root)) {
            # Filho estranho: nao matar
            continue
        }
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
        } catch { }
    }
    Start-Sleep -Milliseconds 200
    $still = Get-ProcessIdentity -ProcessId $ProcessId
    if ($null -eq $still) {
        return [pscustomobject]@{ Pid = $ProcessId; Result = "encerrado"; Detail = "ok"; Identity = $identity }
    }
    return [pscustomobject]@{ Pid = $ProcessId; Result = "falha"; Detail = "ainda vivo"; Identity = $still }
}

function Read-PanneDemoInstance {
    param([string]$Root)
    $path = Get-PanneDemoInstancePath $Root
    $legacy = Get-PanneDemoLegacyPidPath $Root
    if (Test-Path $path) {
        return (Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json)
    }
    if (Test-Path $legacy) {
        $old = Get-Content $legacy -Raw -Encoding UTF8 | ConvertFrom-Json
        return [pscustomobject]@{
            schema_version = 0
            instance_id    = $null
            started_at     = $old.started_at
            root           = $Root
            environment    = "demo"
            logical_database = "panne_demo"
            demo_anchor_date = $null
            api = [pscustomobject]@{ launcher_pid = $old.api; server_pid = $old.api; start_time = $null; command_safe = $null }
            frontend = [pscustomobject]@{ launcher_pid = $old.fe; server_pid = $old.fe; start_time = $null; command_safe = $null }
            ports = [pscustomobject]@{ api = 5080; frontend = 5180 }
            logs = $null
            legacy = $true
        }
    }
    return $null
}

function Write-PanneDemoInstance {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)]$Instance
    )
    $tmp = Get-PanneDemoTmpDir $Root
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $path = Get-PanneDemoInstancePath $Root
    $json = $Instance | ConvertTo-Json -Depth 6
    # Guardrail: nunca gravar connection string / senha
    if ($json -match '(?i)postgresql(\+\w+)?://[^:]+:[^@]+@' -or $json -match '(?i)"password"\s*:') {
        throw "Recusado: registro de instância conteria segredo."
    }
    Set-Content -Path $path -Value $json -Encoding UTF8
    # Compat: espelha PIDs reais no legacy para leitores antigos
    @{
        api = $Instance.api.server_pid
        fe  = $Instance.frontend.server_pid
        started_at = $Instance.started_at
        instance_id = $Instance.instance_id
    } | ConvertTo-Json | Set-Content -Path (Get-PanneDemoLegacyPidPath $Root) -Encoding UTF8
}

function Clear-PanneDemoInstanceFiles {
    param([string]$Root)
    foreach ($p in @((Get-PanneDemoInstancePath $Root), (Get-PanneDemoLegacyPidPath $Root))) {
        if (Test-Path $p) { Remove-Item $p -Force -ErrorAction SilentlyContinue }
    }
}

function Assert-NoSecretInText {
    param([string]$Text, [string]$Label = "texto")
    if ($Text -match '(?i)postgresql(\+\w+)?://[^:]+:[^@]+@') {
        throw "$Label contém connection string com credencial."
    }
    if ($Text -match '(?i)(Bearer\s+[A-Za-z0-9\-_\.]+)') {
        throw "$Label contém token."
    }
}

function Format-ProcessReport {
    param($Identity)
    if ($null -eq $Identity) { return "PID ausente" }
    $start = if ($Identity.StartTime) { $Identity.StartTime.ToString("s") } else { "?" }
    return "PID $($Identity.Pid) | $($Identity.Name) | inicio $start | $($Identity.CommandSafe)"
}
