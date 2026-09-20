#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$secretFile = Join-Path $PSScriptRoot '.local-secrets.env'

function New-Secret {
  $bytes = New-Object byte[] 24
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  return [Convert]::ToBase64String($bytes)
}

$values = @{}
if (Test-Path $secretFile) {
  Get-Content $secretFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_.Split('=', 2)
    if ($parts.Count -eq 2) { $values[$parts[0]] = $parts[1] }
  }
}

if (-not $values.ContainsKey('SPIDER_SPIDERBANK_DEMO_APPLICATION_SECRET')) {
  $app = New-Secret
  $values['SPIDER_SPIDERBANK_DEMO_APPLICATION_SECRET'] = $app
  $values['SPIDERBANK_SPIDER_DEMO_APPLICATION_SECRET'] = $app
} elseif (-not $values.ContainsKey('SPIDERBANK_SPIDER_DEMO_APPLICATION_SECRET')) {
  $values['SPIDERBANK_SPIDER_DEMO_APPLICATION_SECRET'] = $values['SPIDER_SPIDERBANK_DEMO_APPLICATION_SECRET']
}

if (-not $values.ContainsKey('SPIDER_SPIDERBANK_CUSTOMER_ASSERTION_SECRET')) {
  $assertion = New-Secret
  $values['SPIDER_SPIDERBANK_CUSTOMER_ASSERTION_SECRET'] = $assertion
  $values['SPIDERBANK_CUSTOMER_ASSERTION_SECRET'] = $assertion
} elseif (-not $values.ContainsKey('SPIDERBANK_CUSTOMER_ASSERTION_SECRET')) {
  $values['SPIDERBANK_CUSTOMER_ASSERTION_SECRET'] = $values['SPIDER_SPIDERBANK_CUSTOMER_ASSERTION_SECRET']
}

if (-not $values.ContainsKey('SPIDER_CREDIT_MOCK_CREDENTIAL')) {
  $credit = New-Secret
  $values['SPIDER_CREDIT_MOCK_CREDENTIAL'] = $credit
  $values['CREDIT_MOCK_CREDENTIAL'] = $credit
} elseif (-not $values.ContainsKey('CREDIT_MOCK_CREDENTIAL')) {
  $values['CREDIT_MOCK_CREDENTIAL'] = $values['SPIDER_CREDIT_MOCK_CREDENTIAL']
}

$lines = @(
  "SPIDER_SPIDERBANK_DEMO_APPLICATION_SECRET=$($values['SPIDER_SPIDERBANK_DEMO_APPLICATION_SECRET'])",
  "SPIDERBANK_SPIDER_DEMO_APPLICATION_SECRET=$($values['SPIDERBANK_SPIDER_DEMO_APPLICATION_SECRET'])",
  "SPIDER_SPIDERBANK_CUSTOMER_ASSERTION_SECRET=$($values['SPIDER_SPIDERBANK_CUSTOMER_ASSERTION_SECRET'])",
  "SPIDERBANK_CUSTOMER_ASSERTION_SECRET=$($values['SPIDERBANK_CUSTOMER_ASSERTION_SECRET'])",
  "SPIDER_CREDIT_MOCK_CREDENTIAL=$($values['SPIDER_CREDIT_MOCK_CREDENTIAL'])",
  "CREDIT_MOCK_CREDENTIAL=$($values['CREDIT_MOCK_CREDENTIAL'])"
)
$lines | Set-Content -Path $secretFile -Encoding ascii
Write-Output "wrote $secretFile"
Write-Output "Engine local-demo needs the same SPIDER_SPIDERBANK_* and SPIDER_CREDIT_MOCK_CREDENTIAL values. Secrets are not printed."
