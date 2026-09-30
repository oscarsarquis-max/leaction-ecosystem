$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $root
& (Join-Path $root "backend\mvnw.cmd") -q -f backend/pom.xml spring-boot:run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
