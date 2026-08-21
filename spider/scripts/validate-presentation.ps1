#Requires -Version 5.1
<#
.SYNOPSIS
  Valida pré-requisitos da apresentação Mock do Spider (PROMPT-015).
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Write-Host "== SPIDER validate-presentation =="

function Assert-Cmd($name) {
  $c = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $c) { throw "Comando obrigatório ausente: $name" }
  Write-Host "OK $name = $($c.Source)"
}

Assert-Cmd java
Assert-Cmd node
$mvn = Join-Path $Root ".tools\apache-maven-3.9.16\bin\mvn.cmd"
if (-not (Test-Path $mvn)) {
  Assert-Cmd mvn
  $mvn = "mvn"
} else {
  Write-Host "OK mvn = $mvn"
}

$javaVer = & java -version 2>&1 | Out-String
if ($javaVer -notmatch 'version "21') {
  Write-Warning "JDK 21 recomendado. Detectado: $javaVer"
}

foreach ($p in 8080, 5180) {
  $inUse = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if ($inUse) { Write-Warning "Porta $p em uso (PID $($inUse.OwningProcess))" }
  else { Write-Host "OK porta $p livre" }
}

$manifest = Join-Path $Root "backend\src\main\resources\implementation\spider-capability-manifest.json"
$schema = Join-Path $Root "backend\src\main\resources\implementation\spider-capability-manifest.schema.json"
if (-not (Test-Path $manifest)) { throw "Manifest ausente" }
if (-not (Test-Path $schema)) { throw "Schema ausente" }
Write-Host "OK manifesto/schema"

Push-Location (Join-Path $Root "backend")
& $mvn -q -DskipTests compile
if ($LASTEXITCODE -ne 0) { throw "mvn compile falhou" }
Pop-Location

Push-Location (Join-Path $Root "frontend")
if (-not (Test-Path "node_modules")) { npm install }
npm run build
if ($LASTEXITCODE -ne 0) { throw "npm build falhou" }
Pop-Location

Write-Host "VALIDAÇÃO OK — próximo: .\scripts\start-presentation.ps1"
Write-Host "Boundary: MOCK_ONLY (sem legado/rede real neste script)"
