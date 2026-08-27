#Requires -Version 5.1
# Harness R026-012 — testes seguros dos helpers (sem matar processos do usuário).
$ErrorActionPreference = "Stop"
$failed = 0
$passed = 0

. (Join-Path $PSScriptRoot "..\demo-lifecycle.ps1")

function Assert-True($Condition, [string]$Name) {
    if ($Condition) {
        Write-Host "PASS $Name"
        $script:passed++
    } else {
        Write-Host "FAIL $Name"
        $script:failed++
    }
}

$Root = Get-PanneDemoRoot (Join-Path $PSScriptRoot "..")
Assert-True (Test-Path (Join-Path $Root "backend\app\main.py")) "root resolve panne"

# Sanitização de URL
$san = ConvertTo-SanitizedCommand "uvicorn postgresql+asyncpg://admin:s3cret@127.0.0.1:5433/panne_demo"
Assert-True ($san -notmatch "s3cret") "sanitize hides password"
Assert-True ($san -match "\*\*\*") "sanitize keeps placeholder"

$db = Get-LogicalDatabaseName "postgresql+asyncpg://u:p@h/panne_demo"
Assert-True ($db -eq "panne_demo") "logical db name"

# Identidade: fake objects
$panneApi = [pscustomobject]@{
    Path = Join-Path $Root "backend\.venv\Scripts\python.exe"
    CommandLine = "python -m uvicorn app.main:app --host 127.0.0.1 --port 5080"
}
Assert-True (Test-PanneDemoProcessIdentity -Identity $panneApi -Root $Root) "api identity under panne"

$panneFe = [pscustomobject]@{
    Path = "C:\Program Files\nodejs\node.exe"
    CommandLine = "node $(Join-Path $Root 'frontend\node_modules\vite\bin\vite.js')"
}
Assert-True (Test-PanneDemoProcessIdentity -Identity $panneFe -Root $Root) "vite identity under panne"

$foreign = [pscustomobject]@{
    Path = "C:\Windows\System32\python.exe"
    CommandLine = "python -m http.server 5080"
}
Assert-True (-not (Test-PanneDemoProcessIdentity -Identity $foreign -Root $Root)) "foreign python rejected"

$otherProduct = [pscustomobject]@{
    Path = "C:\Projetos\qmind\backend\python.exe"
    CommandLine = "uvicorn app.main:app --port 5080"
}
Assert-True (-not (Test-PanneDemoProcessIdentity -Identity $otherProduct -Root $Root)) "other product rejected"

# PID inexistente
$missing = Stop-ProvenPanneProcess -ProcessId 99999999 -Root $Root
Assert-True ($missing.Result -eq "ja_ausente") "missing pid is ja_ausente"

# Registro sem segredo (diretório temporário — não toca demo em uso)
$tmpRoot = Join-Path $env:TEMP "panne-r012-$(Get-Random)"
New-Item -ItemType Directory -Force -Path (Join-Path $tmpRoot "backend\app") | Out-Null
Set-Content (Join-Path $tmpRoot "backend\app\main.py") -Value "# stub"
New-Item -ItemType Directory -Force -Path (Join-Path $tmpRoot ".tmp-demo") | Out-Null
$good = [pscustomobject]@{
    schema_version = 1
    instance_id = "testid"
    started_at = "2026-08-27T00:00:00Z"
    root = $tmpRoot
    environment = "demo"
    logical_database = "panne_demo"
    demo_anchor_date = "2026-08-24"
    api = [pscustomobject]@{ launcher_pid = 1; server_pid = 2; start_time = $null; command_safe = "uvicorn app.main:app" }
    frontend = [pscustomobject]@{ launcher_pid = 3; server_pid = 4; start_time = $null; command_safe = "npm run dev" }
    ports = [pscustomobject]@{ api = 5080; frontend = 5180 }
    logs = [pscustomobject]@{ api_out = "a"; api_err = "b"; fe_out = "c"; fe_err = "d" }
}
Write-PanneDemoInstance -Root $tmpRoot -Instance $good
$raw = Get-Content (Get-PanneDemoInstancePath $tmpRoot) -Raw
Assert-True ($raw -notmatch "postgresql://") "instance.json no connection string"
Assert-True ($raw -match "testid") "instance.json has id"
try {
    Assert-NoSecretInText -Text $raw -Label "instance"
    Assert-True $true "assert no secret ok"
} catch {
    Assert-True $false "assert no secret threw"
}

$bad = [pscustomobject]@{
    schema_version = 1
    instance_id = "x"
    leak = "postgresql+asyncpg://admin:s3cret@127.0.0.1/panne_demo"
}
$threw = $false
try { Write-PanneDemoInstance -Root $tmpRoot -Instance $bad } catch { $threw = $true }
Assert-True $threw "refuses secret in instance.json"
Remove-Item $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue

# npm.cmd resolução: start-demo exige .cmd (smoke via where)
$npm = @(where.exe npm.cmd 2>$null)
Assert-True ($npm.Count -gt 0) "npm.cmd available on station"

Write-Host ""
Write-Host "Passed=$passed Failed=$failed"
if ($failed -gt 0) { exit 1 }
exit 0
