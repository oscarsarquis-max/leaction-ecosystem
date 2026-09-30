$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $root

if (Test-Path (Join-Path $root ".git")) {
  throw "Nested git repository detected under ActionFinance. Stop."
}

$local = Join-Path $root ".local"
New-Item -ItemType Directory -Force -Path $local, (Join-Path $local "init") | Out-Null

function New-Secret {
  $bytes = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

function Read-EnvFile([string]$path) {
  $map = @{}
  if (-not (Test-Path $path)) { return $map }
  Get-Content $path | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $parts = $_.Split('=', 2)
    $map[$parts[0].Trim()] = $parts[1]
  }
  return $map
}

$secretsPath = Join-Path $local "secrets.env"
$existing = Read-EnvFile $secretsPath
if (-not $existing.ContainsKey("ACTIONFINANCE_BOOTSTRAP_PASSWORD")) {
  $existing["ACTIONFINANCE_BOOTSTRAP_PASSWORD"] = New-Secret
  $existing["ACTIONFINANCE_MIGRATOR_PASSWORD"] = New-Secret
  $existing["ACTIONFINANCE_RUNTIME_PASSWORD"] = New-Secret
  @(
    "ACTIONFINANCE_BOOTSTRAP_PASSWORD=$($existing.ACTIONFINANCE_BOOTSTRAP_PASSWORD)",
    "ACTIONFINANCE_MIGRATOR_PASSWORD=$($existing.ACTIONFINANCE_MIGRATOR_PASSWORD)",
    "ACTIONFINANCE_RUNTIME_PASSWORD=$($existing.ACTIONFINANCE_RUNTIME_PASSWORD)"
  ) | Set-Content -Path $secretsPath -Encoding ascii
}

$tokensPath = Join-Path $local "demo-tokens.env"
$tokenExisting = Read-EnvFile $tokensPath
if (-not $tokenExisting.ContainsKey("ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A")) {
  $tokenExisting["ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A"] = New-Secret
  $tokenExisting["ACTIONFINANCE_DEMO_TOKEN_VIEWER_A"] = New-Secret
  $tokenExisting["ACTIONFINANCE_DEMO_TOKEN_VIEWER_B"] = New-Secret
  @(
    "ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A=$($tokenExisting.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A)",
    "ACTIONFINANCE_DEMO_TOKEN_VIEWER_A=$($tokenExisting.ACTIONFINANCE_DEMO_TOKEN_VIEWER_A)",
    "ACTIONFINANCE_DEMO_TOKEN_VIEWER_B=$($tokenExisting.ACTIONFINANCE_DEMO_TOKEN_VIEWER_B)"
  ) | Set-Content -Path $tokensPath -Encoding ascii
}

$template = Get-Content (Join-Path $root "database\bootstrap\01-roles.sql.tmpl") -Raw
$sql = $template.Replace("__MIGRATOR_PASSWORD__", $existing.ACTIONFINANCE_MIGRATOR_PASSWORD).Replace("__RUNTIME_PASSWORD__", $existing.ACTIONFINANCE_RUNTIME_PASSWORD)
Set-Content -Path (Join-Path $local "init\01-roles.sql") -Value $sql -Encoding ascii

$env:ACTIONFINANCE_BOOTSTRAP_PASSWORD = $existing.ACTIONFINANCE_BOOTSTRAP_PASSWORD
docker compose --project-directory $root up -d postgres
Write-Output "SETUP_OK container=actionfinance-postgres-17 image=postgres:17.6 volume=actionfinance_pgdata_17"
Write-Output "Legacy actionfinance-postgres / actionfinance_pgdata were left in place."
Write-Output "Secrets and demo tokens remain in .local/ and are not printed."
