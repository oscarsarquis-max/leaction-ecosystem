#Requires -Version 5.1
[CmdletBinding()]
param(
  [switch] $RecreateVolume
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$composeFile = Join-Path $root "ops\compose\actionfinance-https-trial.yml"
$image = if ($env:ACTIONFINANCE_IMAGE) { $env:ACTIONFINANCE_IMAGE } else { "actionfinance:local-prm006" }
$issuer = "https://idp.trial.localhost:18444/default"
$subject = "https-trial-operator-viewer"

function Assert-NativeExit {
  param([Parameter(Mandatory = $true)][string] $Step)
  if ($null -eq $LASTEXITCODE -or $LASTEXITCODE -ne 0) {
    $code = if ($null -eq $LASTEXITCODE) { 1 } else { $LASTEXITCODE }
    Write-Error "$Step failed with exit code $code."
    exit $code
  }
}

function Invoke-Compose {
  param([Parameter(Mandatory = $true)][string[]] $ComposeArgs)
  $env:ACTIONFINANCE_IMAGE = $image
  & docker compose -p actionfinance-https-trial -f $composeFile @ComposeArgs
  Assert-NativeExit ("docker compose " + ($ComposeArgs -join " "))
}

Set-Location $root
& (Join-Path $PSScriptRoot "generate-https-trial-certs.ps1")
Assert-NativeExit "generate-https-trial-certs.ps1"

$id = docker image inspect $image --format "{{.Id}}"
Assert-NativeExit "docker image inspect"
Write-Host "Using image $image id=$id"

if ($RecreateVolume) {
  Invoke-Compose -ComposeArgs @("down", "-v", "--remove-orphans")
} else {
  Invoke-Compose -ComposeArgs @("down", "--remove-orphans")
}

Invoke-Compose -ComposeArgs @("up", "-d")

$ready = $false
$lastBody = ""
for ($i = 0; $i -lt 45; $i++) {
  Start-Sleep -Seconds 2
  $info = & curl.exe -sk --resolve "finance.trial.localhost:18443:127.0.0.1" "https://finance.trial.localhost:18443/api/v1/system/info"
  if ($LASTEXITCODE -eq 0 -and $info -match "OIDC") {
    $ready = $true
    $lastBody = $info
    break
  }
  $lastBody = "$info"
}
if (-not $ready) {
  Write-Host "App did not become ready. Last /api/v1/system/info body (may be empty):"
  Write-Host $lastBody
  & docker compose -p actionfinance-https-trial -f $composeFile logs --tail 80 app
  Write-Error "HTTPS trial app did not serve /api/v1/system/info with OIDC."
  exit 1
}
Write-Host "App ready: $lastBody"

$env:ACTIONFINANCE_DATASOURCE_URL = "jdbc:postgresql://127.0.0.1:15439/actionfinance"
$env:ACTIONFINANCE_RUNTIME_USERNAME = "actionfinance_runtime"
$env:ACTIONFINANCE_RUNTIME_PASSWORD = "runtime-change-me"
$env:ACTIONFINANCE_MIGRATOR_USERNAME = "actionfinance_migrator"
$env:ACTIONFINANCE_MIGRATOR_PASSWORD = "migrator-change-me"
$env:ACTIONFINANCE_BACKEND_PORT = "18093"
$env:ACTIONFINANCE_OIDC_ENABLED = "false"
$env:ACTIONFINANCE_DEMO_AUTH_ENABLED = "false"

function Invoke-AccessAdmin {
  param([Parameter(Mandatory = $true)][string[]] $AdminArgs)
  $jar = Join-Path $root "backend\target\actionfinance-backend-0.1.0.jar"
  if (-not (Test-Path -LiteralPath $jar)) {
    throw "Host JAR missing; run build-production-image.ps1 first."
  }
  & java -jar $jar --spring.profiles.active=access-admin @AdminArgs
  Assert-NativeExit ("access-admin " + $AdminArgs[0])
}

function Get-OrgIds {
  param([string] $TenantCode, [string] $CompanyCode)
  $sql = "select t.id::text || ' ' || c.id::text from actionfinance.tenant t join actionfinance.company c on c.tenant_id = t.id where t.code = '$TenantCode' and c.code = '$CompanyCode';"
  $row = & docker compose -p actionfinance-https-trial -f $composeFile exec -T postgres psql -U postgres -d actionfinance -tA -c $sql
  Assert-NativeExit "psql lookup $TenantCode/$CompanyCode"
  $parts = ($row | Out-String).Trim() -split "\s+"
  if ($parts.Count -lt 2) {
    throw "Could not resolve ids for $TenantCode/$CompanyCode. Output: $row"
  }
  return @{ TenantId = $parts[0]; CompanyId = $parts[1] }
}

function Ensure-Org {
  param(
    [string] $TenantCode,
    [string] $TenantName,
    [string] $CompanyCode,
    [string] $CompanyName,
    [string] $ResponsibleName
  )
  $existing = & docker compose -p actionfinance-https-trial -f $composeFile exec -T postgres psql -U postgres -d actionfinance -tA -c "select count(*) from actionfinance.tenant where code = '$TenantCode';"
  if (($existing | Out-String).Trim() -eq "1") {
    Write-Host "Tenant $TenantCode already present (volume reused)."
    return
  }
  Invoke-AccessAdmin -AdminArgs @(
    "bootstrap-org", "--dry-run",
    "--tenant-code=$TenantCode", "--tenant-name=$TenantName",
    "--company-code=$CompanyCode", "--company-name=$CompanyName",
    "--timezone=America/Sao_Paulo", "--responsible-name=$ResponsibleName",
    "--reason=ensaio-https-trial-dry-run"
  )
  Invoke-AccessAdmin -AdminArgs @(
    "bootstrap-org",
    "--tenant-code=$TenantCode", "--tenant-name=$TenantName",
    "--company-code=$CompanyCode", "--company-name=$CompanyName",
    "--timezone=America/Sao_Paulo", "--responsible-name=$ResponsibleName",
    "--reason=ensaio-https-trial"
  )
}

Ensure-Org -TenantCode "TENANT-A-TRIAL" -TenantName "Tenant-A-ensaio-HTTPS" -CompanyCode "COMPANY-A-TRIAL" -CompanyName "Empresa-A-ensaio-HTTPS" -ResponsibleName "Responsavel-ensaio-HTTPS"
Ensure-Org -TenantCode "TENANT-B-TRIAL" -TenantName "Tenant-B-ensaio-HTTPS" -CompanyCode "COMPANY-B-TRIAL" -CompanyName "Empresa-B-ensaio-HTTPS" -ResponsibleName "Responsavel-ensaio-HTTPS"

$orgA = Get-OrgIds "TENANT-A-TRIAL" "COMPANY-A-TRIAL"
$orgB = Get-OrgIds "TENANT-B-TRIAL" "COMPANY-B-TRIAL"

Invoke-AccessAdmin -AdminArgs @(
  "provision", "--display-name=Operadora-ensaio-HTTPS", "--issuer=$issuer", "--subject=$subject",
  "--tenant-id=$($orgA.TenantId)", "--company-id=$($orgA.CompanyId)", "--role=OPERATOR",
  "--reason=ensaio-https-operator-a"
)
Invoke-AccessAdmin -AdminArgs @(
  "provision", "--display-name=Operadora-ensaio-HTTPS", "--issuer=$issuer", "--subject=$subject",
  "--tenant-id=$($orgB.TenantId)", "--company-id=$($orgB.CompanyId)", "--role=VIEWER",
  "--reason=ensaio-https-viewer-b"
)

Write-Host "HTTPS trial is up."
Write-Host "ImageId $id"
Write-Host "Origin https://finance.trial.localhost:18443"
Write-Host "Issuer $issuer"
Write-Host "Subject $subject (trial fixture in idp-config.json; not a production identity)"
Write-Host "Company A OPERATOR $($orgA.CompanyId) / Company B VIEWER $($orgB.CompanyId)"
Write-Host "Browser resolver: MAP finance.trial.localhost 127.0.0.1, MAP idp.trial.localhost 127.0.0.1"
Write-Host "Trial passwords come from ops/compose/bootstrap-prod-like.sql and are exclusive to this disposable stack."
