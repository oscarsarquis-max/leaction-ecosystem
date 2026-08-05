$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$env:JAVA_HOME = if ($env:JAVA_HOME) { $env:JAVA_HOME } else { "C:\Program Files\Microsoft\jdk-21.0.12.8-hotspot" }
$mvnCandidates = @(
  (Join-Path $root ".tools\apache-maven-3.9.16\bin\mvn.cmd"),
  "mvn"
)
$mvn = $mvnCandidates | Where-Object { $_ -eq "mvn" -or (Test-Path $_) } | Select-Object -First 1
if (-not $mvn) { throw "Maven não encontrado. Instale ou use .tools/apache-maven-3.9.16" }

$env:Path = "$env:JAVA_HOME\bin;" + $env:Path
Set-Location (Join-Path $root "backend")
Write-Host "== mvn -DskipTests package =="
& $mvn -DskipTests package
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OK: backend/target/*.jar"
