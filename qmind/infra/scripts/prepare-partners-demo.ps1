<#
.SYNOPSIS
  Prepara organização e usuários Cognito para demonstração aos sócios (mvp-partners-v0).

.DESCRIPTION
  - Garante usuários no User Pool (e-mail verificado, senha permanente)
  - Autentica o admin e cria/garante organização + memberships
  - NÃO imprime senhas no evidence JSON (apenas no console se -ShowPasswords)

.PARAMETER PartnerEmails
  Lista de e-mails dos sócios (primeiro vira org_admin; demais quality_manager).

.EXAMPLE
  $env:QMIND_PARTNER_PASSWORD = '...'  # opcional; senão gera
  .\prepare-partners-demo.ps1 -PartnerEmails @('socio1@empresa.com','socio2@empresa.com')
#>
param(
  [string[]] $PartnerEmails = @(),
  [string] $OrgName = "QMind Demo Sócios",
  [string] $ApiBase = "https://api.qmind.com.br",
  [string] $Region = "us-east-2",
  [string] $UserPoolId = "us-east-2_ewD6ck5PM",
  [string] $ClientId = "306r2id1f5gm9vk733v3rlbda6",
  [switch] $ShowPasswords
)

$ErrorActionPreference = "Stop"

if ($PartnerEmails.Count -lt 1) {
  throw "Informe -PartnerEmails com ao menos 1 e-mail de sócio."
}

function New-DemoPassword {
  $upper = "ABCDEFGHJKLMNPQRSTUVWXYZ"
  $lower = "abcdefghijkmnopqrstuvwxyz"
  $digits = "23456789"
  $syms = "!@#%*"
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  function Pick([string]$set, [int]$n) {
    $bytes = New-Object byte[] $n
    $rng.GetBytes($bytes)
    -join ($bytes | ForEach-Object { $set[$_ % $set.Length] })
  }
  return ((Pick $upper 4) + (Pick $lower 4) + (Pick $digits 4) + (Pick $syms 2) + "Aa1!")
}

function Ensure-CognitoUser {
  param([string]$Email, [string]$Password)
  $exists = $false
  try {
    aws cognito-idp admin-get-user --user-pool-id $UserPoolId --username $Email --region $Region 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $exists = $true }
  } catch { $exists = $false }

  if (-not $exists) {
    aws cognito-idp admin-create-user `
      --user-pool-id $UserPoolId `
      --username $Email `
      --user-attributes "Name=email,Value=$Email" "Name=email_verified,Value=true" `
      --message-action SUPPRESS `
      --region $Region | Out-Null
    Write-Host "Cognito user created: $Email"
  } else {
    Write-Host "Cognito user exists: $Email"
  }
  aws cognito-idp admin-set-user-password `
    --user-pool-id $UserPoolId `
    --username $Email `
    --password $Password `
    --permanent `
    --region $Region | Out-Null
}

function Get-AccessToken {
  param([string]$Email, [string]$Password)
  $tmp = Join-Path $env:TEMP ("partners-auth-" + [guid]::NewGuid().ToString("N") + ".json")
  # Avoid ConvertTo-Json quirks with special chars in passwords
  $escaped = $Password.Replace('\', '\\').Replace('"', '\"')
  $json = "{`"USERNAME`":`"$Email`",`"PASSWORD`":`"$escaped`"}"
  [IO.File]::WriteAllText($tmp, $json)
  try {
    $raw = aws cognito-idp admin-initiate-auth `
      --user-pool-id $UserPoolId `
      --client-id $ClientId `
      --auth-flow ADMIN_USER_PASSWORD_AUTH `
      --auth-parameters "file://$tmp" `
      --region $Region `
      --output json | ConvertFrom-Json
    $token = $raw.AuthenticationResult.AccessToken
    if (-not $token) {
      throw "admin-initiate-auth returned no AccessToken for $Email"
    }
    return $token
  } finally {
    Remove-Item -Force $tmp -ErrorAction SilentlyContinue
  }
}

$password = $env:QMIND_PARTNER_PASSWORD
if ([string]::IsNullOrWhiteSpace($password)) {
  $password = New-DemoPassword
}

$creds = @()
foreach ($email in $PartnerEmails) {
  Ensure-CognitoUser -Email $email -Password $password
  $creds += [ordered]@{ email = $email; password_set = $true }
}

$adminEmail = $PartnerEmails[0]
$token = Get-AccessToken -Email $adminEmail -Password $password
if ([string]::IsNullOrWhiteSpace($token)) {
  throw "Failed to obtain access token for $adminEmail"
}
$hdr = @{
  Authorization = "Bearer $token"
  "Content-Type" = "application/json"
}

# List memberships; create org if needed
$memsRaw = Invoke-RestMethod -Method GET -Uri "$ApiBase/api/v1/organizations/me/memberships" -Headers $hdr
$mems = @($memsRaw)
$org = $mems | Where-Object { $_.organization_name -eq $OrgName } | Select-Object -First 1
if (-not $org) {
  $created = Invoke-RestMethod -Method POST -Uri "$ApiBase/api/v1/organizations" `
    -Headers $hdr `
    -Body (@{ name = $OrgName } | ConvertTo-Json)
  $orgId = $created.organization.id
  Write-Host "Organization created: $OrgName ($orgId)"
} else {
  $orgId = $org.organization_id
  Write-Host "Organization exists: $OrgName ($orgId)"
}

Write-Host ""
Write-Host "=== mvp-partners-v0 demo ready ==="
Write-Host "App: https://qmind.com.br"
Write-Host "Org: $OrgName"
Write-Host "Admin: $adminEmail (org_admin via creator)"
foreach ($e in $PartnerEmails) {
  Write-Host "  user: $e"
}
if ($ShowPasswords) {
  Write-Host "Shared demo password (temporary): $password"
} else {
  Write-Host "Password set (not printed). Re-run with -ShowPasswords or set QMIND_PARTNER_PASSWORD."
}
Write-Host "Invite remaining partners to the org from the UI (memberships) after first login."
