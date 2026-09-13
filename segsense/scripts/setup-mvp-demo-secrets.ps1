# Generates unversioned local secrets for the SegSense demo slice. Does not print values.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_mvp-secrets-acl.ps1')
$target = Join-Path $PSScriptRoot '.mvp-secrets.env'
$staging = Join-Path $PSScriptRoot '.mvp-secrets.env.new'

function New-Secret {
  $bytes = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  return ([System.BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
}

$appSecret = New-Secret
$mockSecret = New-Secret
@(
  '# Unversioned local secrets for the SegSense demo slice. Do not commit.',
  "SPIDER_SEGSENSE_DEMO_APPLICATION_SECRET=$appSecret",
  "SEGSENSE_SPIDER_DEMO_APPLICATION_SECRET=$appSecret",
  "SEGSENSE_MOCK_CREDENTIAL=$mockSecret",
  "SPIDER_SEGSENSE_MOCK_CREDENTIAL=$mockSecret"
) | Set-Content -LiteralPath $staging -Encoding ascii

try {
  Set-MvpRestrictedAcl -Path $staging
  Move-Item -LiteralPath $staging -Destination $target -Force
  Set-MvpRestrictedAcl -Path $target
} catch {
  if (Test-Path -LiteralPath $staging) {
    Remove-Item -LiteralPath $staging -Force -ErrorAction SilentlyContinue
  }
  throw
}

Write-Output "Wrote restricted secrets file (values not printed). Rotate by running this script again and restarting the three runtimes."
