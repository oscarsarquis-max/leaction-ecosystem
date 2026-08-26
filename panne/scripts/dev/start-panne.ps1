#Requires -Version 5.1
# Sobe API + frontend e garante o proprietário local para acompanhamento visual.
$ErrorActionPreference = 'Stop'
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$BackendScript = Join-Path $PSScriptRoot 'start-backend.ps1'
$FrontendScript = Join-Path $PSScriptRoot 'start-frontend.ps1'
$BootstrapDb = Join-Path $PSScriptRoot 'bootstrap-db.ps1'

if (Test-Path $BootstrapDb) {
    & $BootstrapDb
}

function Test-LocalHttp([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

if (-not (Test-LocalHttp 'http://127.0.0.1:5080/health')) {
    Start-Process powershell -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $BackendScript) | Out-Null
}
if (-not (Test-LocalHttp 'http://127.0.0.1:5180/')) {
    Start-Process powershell -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $FrontendScript) | Out-Null
}

$deadline = (Get-Date).AddSeconds(40)
do {
    $api = Test-LocalHttp 'http://127.0.0.1:5080/health'
    $fe = Test-LocalHttp 'http://127.0.0.1:5180/'
    if ($api -and $fe) { break }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)

if (-not $api -or -not $fe) {
    throw "Panne nao respondeu a tempo. API=$api FE=$fe"
}

Start-Process 'http://127.0.0.1:5180/entrar'
Write-Host 'Panne local: http://127.0.0.1:5180/  API: http://127.0.0.1:5080/'
