# Loads .mvp-secrets.env into the current process without printing values.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_mvp-secrets-acl.ps1')
$secretsFile = Join-Path $PSScriptRoot '.mvp-secrets.env'
if (-not (Test-Path $secretsFile)) {
  throw "Missing $secretsFile. Run setup-mvp-demo-secrets.ps1 first."
}
if (-not (Test-MvpRestrictedAcl -Path $secretsFile)) {
  throw "Secrets file ACL is not restricted. Re-run setup-mvp-demo-secrets.ps1. Do not announce this stack as ready on a shared computer."
}
Get-Content $secretsFile | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $name, $value = $_ -split '=', 2
  Set-Item -Path ('Env:' + $name.Trim()) -Value $value.Trim()
}
$required = @(
  'SPIDER_SEGSENSE_DEMO_APPLICATION_SECRET',
  'SEGSENSE_SPIDER_DEMO_APPLICATION_SECRET',
  'SEGSENSE_MOCK_CREDENTIAL',
  'SPIDER_SEGSENSE_MOCK_CREDENTIAL'
)
foreach ($name in $required) {
  $got = [Environment]::GetEnvironmentVariable($name)
  if ([string]::IsNullOrWhiteSpace($got)) {
    throw "Secret $name is empty. Re-run setup-mvp-demo-secrets.ps1."
  }
}
Write-Output 'local demo secrets loaded (values not printed)'
