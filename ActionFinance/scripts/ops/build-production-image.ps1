#Requires -Version 5.1
[CmdletBinding()]
param(
  [switch] $SkipNpmCi,
  [switch] $SkipFrontendBuild
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$tag = if ($env:ACTIONFINANCE_IMAGE) { $env:ACTIONFINANCE_IMAGE } else { "actionfinance:local-prm006" }
$frontend = Join-Path $root "frontend"
$dist = Join-Path $frontend "dist"
$backend = Join-Path $root "backend"
$staticDir = Join-Path $backend "src\main\resources\static"
$targetJar = Join-Path $backend "target\actionfinance-backend-0.1.0.jar"
$stagingDir = Join-Path $root "ops\image-staging"
$stagingJar = Join-Path $stagingDir "actionfinance-backend.jar"
$evidence = [System.Collections.Generic.List[string]]::new()

function Assert-NativeExit {
  param(
    [Parameter(Mandatory = $true)][string] $Step
  )
  if ($null -eq $LASTEXITCODE -or $LASTEXITCODE -ne 0) {
    $code = if ($null -eq $LASTEXITCODE) { 1 } else { $LASTEXITCODE }
    Write-Error "$Step failed with exit code $code."
    exit $code
  }
}

function Remove-ProjectDistIfPresent {
  if (-not (Test-Path -LiteralPath $dist)) {
    return
  }
  $resolved = (Resolve-Path -LiteralPath $dist).Path
  $allowed = (Resolve-Path -LiteralPath $frontend).Path
  if ($resolved.StartsWith($allowed, [System.StringComparison]::OrdinalIgnoreCase) -and
      ([System.IO.Path]::GetFileName($resolved) -eq "dist")) {
    Remove-Item -LiteralPath $resolved -Recurse -Force
  }
}

function Remove-ProjectStaticIfPresent {
  if (-not (Test-Path -LiteralPath $staticDir)) {
    return
  }
  $resolved = (Resolve-Path -LiteralPath $staticDir).Path
  $allowed = (Resolve-Path -LiteralPath (Join-Path $backend "src\main\resources")).Path
  if ($resolved.StartsWith($allowed, [System.StringComparison]::OrdinalIgnoreCase) -and
      ([System.IO.Path]::GetFileName($resolved) -eq "static")) {
    Remove-Item -LiteralPath $resolved -Recurse -Force
  }
}

function Remove-StagingJarIfPresent {
  if (Test-Path -LiteralPath $stagingJar) {
    $resolved = (Resolve-Path -LiteralPath $stagingJar).Path
    $allowed = (Resolve-Path -LiteralPath $stagingDir).Path
    if ($resolved.StartsWith($allowed, [System.StringComparison]::OrdinalIgnoreCase) -and
        ([System.IO.Path]::GetFileName($resolved) -eq "actionfinance-backend.jar")) {
      Remove-Item -LiteralPath $resolved -Force
    }
  }
}

function Get-FileSha256 {
  param([string] $Path)
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

Set-Location $frontend
if ($SkipNpmCi) {
  if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    throw "SkipNpmCi requires an existing frontend/node_modules."
  }
  $evidence.Add("npm ci skipped by -SkipNpmCi; using existing node_modules with package-lock.json present.")
} else {
  npm ci
  Assert-NativeExit "npm ci"
  $evidence.Add("npm ci exit 0")
}

if ($SkipFrontendBuild) {
  if (-not (Test-Path (Join-Path $dist "index.html"))) {
    throw "SkipFrontendBuild requires frontend/dist/index.html."
  }
  $evidence.Add("npm run build skipped by -SkipFrontendBuild; using existing frontend/dist.")
} else {
  npm run build
  if ($null -eq $LASTEXITCODE -or $LASTEXITCODE -ne 0) {
    $code = if ($null -eq $LASTEXITCODE) { 1 } else { $LASTEXITCODE }
    Remove-ProjectDistIfPresent
    Write-Error "npm run build failed with exit code $code."
    exit $code
  }
  $evidence.Add("npm run build exit 0")
}

if (-not (Test-Path (Join-Path $dist "index.html"))) {
  throw "frontend/dist/index.html missing after frontend build."
}
$distHash = Get-FileSha256 (Join-Path $dist "index.html")
$evidence.Add("frontend/dist/index.html sha256=$distHash")

Remove-ProjectStaticIfPresent
New-Item -ItemType Directory -Force -Path $staticDir | Out-Null
Copy-Item -Path (Join-Path $dist "*") -Destination $staticDir -Recurse -Force

Remove-StagingJarIfPresent
if (Test-Path -LiteralPath $targetJar) {
  Remove-Item -LiteralPath $targetJar -Force
}

$packageStarted = Get-Date
Set-Location $backend
Write-Host "mvnw -DskipTests package (host Maven cache; no secrets copied into the image)"
& .\mvnw -DskipTests package
Assert-NativeExit "mvnw package"
if (-not (Test-Path -LiteralPath $targetJar)) {
  throw "backend/target/actionfinance-backend-0.1.0.jar missing after package."
}
$jarInfo = Get-Item -LiteralPath $targetJar
if ($jarInfo.LastWriteTime -lt $packageStarted.AddSeconds(-2)) {
  throw "Refusing stale JAR: last write $($jarInfo.LastWriteTime) is before package start $packageStarted."
}
$jarHash = Get-FileSha256 $targetJar
New-Item -ItemType Directory -Force -Path $stagingDir | Out-Null
Copy-Item -LiteralPath $targetJar -Destination $stagingJar -Force
$evidence.Add("host JAR sha256=$jarHash bytes=$($jarInfo.Length) written=$($jarInfo.LastWriteTime.ToString('o'))")
$evidence.Add("tests: host package used -DskipTests; correspondence is current sources + frontend dist + this JAR. Re-run mvnw verify separately when Java sources change.")

Set-Location $root
docker build -t $tag $root
Assert-NativeExit "docker build"
$imageId = docker image inspect $tag --format "{{.Id}}"
Assert-NativeExit "docker image inspect"
$created = docker image inspect $tag --format "{{.Created}}"
Assert-NativeExit "docker image inspect created"
$evidence.Add("image $tag id=$imageId created=$created")

Write-Host "Built $tag"
Write-Host "ImageId $imageId"
Write-Host "Correspondence:"
foreach ($line in $evidence) {
  Write-Host " - $line"
}
