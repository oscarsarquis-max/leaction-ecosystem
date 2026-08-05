$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "== Postgres =="
Set-Location $root
docker compose up -d

$env:JAVA_HOME = if ($env:JAVA_HOME) { $env:JAVA_HOME } else { "C:\Program Files\Microsoft\jdk-21.0.12.8-hotspot" }
$mvn = Join-Path $root ".tools\apache-maven-3.9.16\bin\mvn.cmd"
if (-not (Test-Path $mvn)) { $mvn = "mvn" }
$env:Path = "$env:JAVA_HOME\bin;" + $env:Path

function Start-InWindow([string]$title, [string]$workdir, [string]$command) {
  Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$workdir'; `$Host.UI.RawUI.WindowTitle='$title'; $command"
  )
}

Write-Host "== Abrindo terminais =="
Start-InWindow "spider-legado:8082" (Join-Path $root "services\service-legado-financeiro") "npm start"
Start-Sleep -Seconds 1
Start-InWindow "spider-originador:8081" (Join-Path $root "services\service-originador") "npm start"
Start-Sleep -Seconds 1
Start-InWindow "spider-api:8080" (Join-Path $root "backend") "& '$mvn' spring-boot:run"
Start-Sleep -Seconds 1
Start-InWindow "spider-web:5180" (Join-Path $root "frontend") "npm run dev"

Write-Host ""
Write-Host "Console: http://127.0.0.1:5180/"
Write-Host "API:     http://127.0.0.1:8080/actuator/health"
Write-Host "Aguarde ~15s o Spring subir, depois abra o console."
