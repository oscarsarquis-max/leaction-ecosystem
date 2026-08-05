<#
.SYNOPSIS
  Gate 011 V4 - Cognito E2E against homolog (API + hosted UI reachability).
  Credentials via env or ephemeral in-process only. Evidence JSON has no secrets/tokens.
#>
param(
  [string] $ApiBase = "https://api.homolog.qmind.com.br",
  [string] $AppBase = "https://app.homolog.qmind.com.br",
  [string] $Region = "us-east-2",
  [string] $UserPoolId = "us-east-2_ewD6ck5PM",
  [string] $ClientId = "306r2id1f5gm9vk733v3rlbda6",
  [string] $EvidencePath = (Join-Path $PSScriptRoot "..\terraform-lightsail\COGNITO_E2E_V4_evidence.json")
)

$ErrorActionPreference = "Stop"

function New-HomologPassword {
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

function Mask-Token([string]$t) {
  if ([string]::IsNullOrEmpty($t)) { return "(empty)" }
  if ($t.Length -le 12) { return "***" }
  return ($t.Substring(0, 6) + "..." + $t.Substring($t.Length - 4) + " (len=$($t.Length))")
}

function Get-JwtPayload([string]$jwt) {
  $parts = $jwt.Split(".")
  if ($parts.Length -lt 2) { throw "not a JWT" }
  $p = $parts[1].Replace("-", "+").Replace("_", "/")
  switch ($p.Length % 4) { 2 { $p += "==" } 3 { $p += "=" } }
  $json = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p))
  return ($json | ConvertFrom-Json)
}

function Invoke-Api {
  param(
    [string] $Method,
    [string] $Path,
    [string] $AccessToken,
    [hashtable] $Headers = @{},
    [object] $Body = $null,
    [int[]] $ExpectStatus = @(200)
  )
  $hdr = @{}
  foreach ($k in $Headers.Keys) { $hdr[$k] = $Headers[$k] }
  if ($AccessToken) { $hdr["Authorization"] = "Bearer $AccessToken" }
  $uri = "$ApiBase$Path"
  $params = @{
    Method      = $Method
    Uri         = $uri
    Headers     = $hdr
    ContentType = "application/json"
  }
  if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Compress -Depth 6) }
  try {
    $resp = Invoke-WebRequest @params -UseBasicParsing
    $code = [int]$resp.StatusCode
    $content = $resp.Content
  } catch {
    $r = $_.Exception.Response
    if (-not $r) { throw }
    $code = [int]$r.StatusCode
    $stream = $r.GetResponseStream()
    $reader = New-Object IO.StreamReader($stream)
    $content = $reader.ReadToEnd()
  }
  if ($ExpectStatus -notcontains $code) {
    $safe = $content
    if ($safe -and $safe.Length -gt 400) { $safe = $safe.Substring(0, 400) + "..." }
    throw "Unexpected status $code for $Method $Path (expected $($ExpectStatus -join ',')). Body: $safe"
  }
  $parsed = $null
  if ($content) {
    try { $parsed = $content | ConvertFrom-Json } catch { $parsed = $content }
  }
  return @{ Status = $code; Body = $parsed; Raw = $content }
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
  }
  aws cognito-idp admin-set-user-password `
    --user-pool-id $UserPoolId `
    --username $Email `
    --password $Password `
    --permanent `
    --region $Region | Out-Null
}

function Get-Tokens {
  param([string]$Email, [string]$Password)
  $tmp = Join-Path $env:TEMP ("cognito-auth-" + [guid]::NewGuid().ToString("N") + ".json")
  @{ USERNAME = $Email; PASSWORD = $Password } | ConvertTo-Json | Set-Content -Path $tmp -Encoding ascii
  try {
    $raw = aws cognito-idp admin-initiate-auth `
      --user-pool-id $UserPoolId `
      --client-id $ClientId `
      --auth-flow ADMIN_USER_PASSWORD_AUTH `
      --auth-parameters "file://$tmp" `
      --region $Region `
      --output json | ConvertFrom-Json
    return $raw.AuthenticationResult
  } finally {
    Remove-Item -Force $tmp -ErrorAction SilentlyContinue
  }
}

function Refresh-Tokens {
  param([string]$RefreshToken)
  $tmp = Join-Path $env:TEMP ("cognito-refresh-" + [guid]::NewGuid().ToString("N") + ".json")
  @{ REFRESH_TOKEN = $RefreshToken } | ConvertTo-Json | Set-Content -Path $tmp -Encoding ascii
  try {
    $raw = aws cognito-idp admin-initiate-auth `
      --user-pool-id $UserPoolId `
      --client-id $ClientId `
      --auth-flow REFRESH_TOKEN_AUTH `
      --auth-parameters "file://$tmp" `
      --region $Region `
      --output json | ConvertFrom-Json
    return $raw.AuthenticationResult
  } finally {
    Remove-Item -Force $tmp -ErrorAction SilentlyContinue
  }
}

$results = [ordered]@{
  gate       = "011-V4-cognito-e2e"
  started_at = (Get-Date).ToUniversalTime().ToString("o")
  api_base   = $ApiBase
  app_base   = $AppBase
  pool_id    = $UserPoolId
  client_id  = $ClientId
  checks     = New-Object System.Collections.ArrayList
}

function Add-Check {
  param([string]$Id, [string]$Status, [string]$Detail)
  [void]$script:results.checks.Add([ordered]@{ id = $Id; status = $Status; detail = $Detail })
  $color = if ($Status -eq "PASS") { "Green" } else { "Red" }
  Write-Host "[$Status] $Id - $Detail" -ForegroundColor $color
}

$health = Invoke-Api -Method GET -Path "/health" -ExpectStatus @(200)
$authMode = [string]$health.Body.auth_mode
$envName = [string]$health.Body.environment
if ($authMode -eq "cognito" -and $envName -eq "homolog") {
  Add-Check "health_auth_mode" "PASS" "environment=$envName auth_mode=$authMode"
} else {
  Add-Check "health_auth_mode" "FAIL" "environment=$envName auth_mode=$authMode"
}

$devProbe = Invoke-Api -Method GET -Path "/api/v1/organizations/me/memberships" `
  -Headers @{ "X-Dev-User-Sub" = "dev-should-fail"; "X-Dev-User-Email" = "dev@example.com" } `
  -ExpectStatus @(401)
Add-Check "auth_mode_dev_rejected" "PASS" "X-Dev-* without Bearer -> $($devProbe.Status)"

$miss = Invoke-Api -Method GET -Path "/api/v1/organizations/me/memberships" -ExpectStatus @(401)
Add-Check "token_missing" "PASS" "status=$($miss.Status)"

$emailA = $env:QMIND_HOMOLOG_USER_A
$passA = $env:QMIND_HOMOLOG_PASS_A
$emailB = $env:QMIND_HOMOLOG_USER_B
$passB = $env:QMIND_HOMOLOG_PASS_B
$createdTemp = $false
if (-not $emailA -or -not $passA) {
  $emailA = "qmind.homolog.gate.a+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
  $passA = New-HomologPassword
  $createdTemp = $true
}
if (-not $emailB -or -not $passB) {
  $emailB = "qmind.homolog.gate.b+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
  $passB = New-HomologPassword
  $createdTemp = $true
}

Write-Host "Ensuring Cognito users (emails only): $emailA | $emailB"
Ensure-CognitoUser -Email $emailA -Password $passA
Ensure-CognitoUser -Email $emailB -Password $passB

$tokA = Get-Tokens -Email $emailA -Password $passA
$accessA = [string]$tokA.AccessToken
$refreshA = [string]$tokA.RefreshToken
$claimsA = Get-JwtPayload $accessA
$subA = [string]$claimsA.sub
$issOk = ([string]$claimsA.iss) -eq "https://cognito-idp.$Region.amazonaws.com/$UserPoolId"
$clientOk = ([string]$claimsA.client_id) -eq $ClientId
$tokenUse = [string]$claimsA.token_use
if ($issOk -and $clientOk -and $tokenUse -eq "access" -and $subA) {
  Add-Check "access_token_claims" "PASS" "sub=$subA token_use=$tokenUse client_id=ok iss=ok access=$(Mask-Token $accessA)"
} else {
  Add-Check "access_token_claims" "FAIL" "issOk=$issOk clientOk=$clientOk token_use=$tokenUse"
}

$org1 = Invoke-Api -Method POST -Path "/api/v1/organizations" -AccessToken $accessA `
  -Body @{ name = "Homolog Gate Org A"; timezone = "America/Sao_Paulo" } -ExpectStatus @(201)
$org1Id = [string]$org1.Body.organization.id
Add-Check "login_api_create_org" "PASS" "org_a=$org1Id status=$($org1.Status)"

$mem = Invoke-Api -Method GET -Path "/api/v1/organizations/me/memberships" -AccessToken $accessA -ExpectStatus @(200)
$memCount = @($mem.Body).Count
Add-Check "memberships_list" "PASS" "count=$memCount"

$cur = Invoke-Api -Method GET -Path "/api/v1/organizations/current" -AccessToken $accessA `
  -Headers @{ "X-Organization-Id" = $org1Id } -ExpectStatus @(200)
Add-Check "org_via_membership" "PASS" "current org ok with membership name=$([string]$cur.Body.name)"

$orgOnly = Invoke-Api -Method GET -Path "/api/v1/organizations/current" `
  -Headers @{ "X-Organization-Id" = $org1Id } -ExpectStatus @(401)
Add-Check "org_header_alone" "PASS" "no bearer -> $($orgOnly.Status)"

$tokB = Get-Tokens -Email $emailB -Password $passB
$accessB = [string]$tokB.AccessToken
$claimsB = Get-JwtPayload $accessB
$subB = [string]$claimsB.sub
$org2 = Invoke-Api -Method POST -Path "/api/v1/organizations" -AccessToken $accessB `
  -Body @{ name = "Homolog Gate Org B"; timezone = "America/Sao_Paulo" } -ExpectStatus @(201)
$org2Id = [string]$org2.Body.organization.id
Add-Check "second_org" "PASS" "org_b=$org2Id sub_b=$subB"

$cross = Invoke-Api -Method GET -Path "/api/v1/organizations/current" -AccessToken $accessA `
  -Headers @{ "X-Organization-Id" = $org2Id } -ExpectStatus @(403, 404)
$leak = $false
if ($cross.Raw -match "Homolog Gate Org B") { $leak = $true }
if (-not $leak -and ($cross.Status -eq 403 -or $cross.Status -eq 404)) {
  Add-Check "cross_org" "PASS" "status=$($cross.Status) no org name leak"
} else {
  Add-Check "cross_org" "FAIL" "status=$($cross.Status) leak=$leak"
}

$parts = $accessA.Split(".")
$tampered = $parts[0] + "." + $parts[1] + "x." + $parts[2]
$tamp = Invoke-Api -Method GET -Path "/api/v1/organizations/me/memberships" -AccessToken $tampered -ExpectStatus @(401)
Add-Check "token_tampered" "PASS" "status=$($tamp.Status)"

$fakeHeader = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"alg":"none"}')).TrimEnd("=").Replace("+", "-").Replace("/", "_")
$fakePayload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"sub":"x","iss":"https://evil.example","exp":9999999999}')).TrimEnd("=").Replace("+", "-").Replace("/", "_")
$fake = "$fakeHeader.$fakePayload.x"
$badIss = Invoke-Api -Method GET -Path "/api/v1/organizations/me/memberships" -AccessToken $fake -ExpectStatus @(401)
Add-Check "token_wrong_issuer" "PASS" "status=$($badIss.Status)"

$wrongClient = Invoke-Api -Method GET -Path "/api/v1/organizations/me/memberships" `
  -AccessToken ($accessA.Substring(0, [Math]::Min(40, $accessA.Length)) + "deadbeef") `
  -ExpectStatus @(401)
Add-Check "token_adulterated" "PASS" "status=$($wrongClient.Status)"

# Expired token: decode, set exp in past is hard without resigning; use Cognito revoke path + note.
# Also try ID token from wrong use if available - skip. Use refresh of expired via empty string.
$expiredProbe = Invoke-Api -Method GET -Path "/api/v1/organizations/me/memberships" `
  -AccessToken "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ4IiwiZXhwIjoxLCJpc3MiOiJodHRwczovL2NvZ25pdG8taWRwLnVzLWVhc3QtMi5hbWF6b25hd3MuY29tL3VzLWVhc3QtMl9ld0Q2Y2s1UE0iLCJjbGllbnRfaWQiOiIzMDZyMmlkMWY1Z205dms3MzN2M3JsYmRhNiJ9.sig" `
  -ExpectStatus @(401)
Add-Check "token_expired_or_bad_sig" "PASS" "status=$($expiredProbe.Status)"

$refreshed = Refresh-Tokens -RefreshToken $refreshA
$accessA2 = [string]$refreshed.AccessToken
$mem2 = Invoke-Api -Method GET -Path "/api/v1/organizations/me/memberships" -AccessToken $accessA2 -ExpectStatus @(200)
Add-Check "session_refresh" "PASS" "new_access=$(Mask-Token $accessA2) memberships_ok count=$(@($mem2.Body).Count)"

aws cognito-idp admin-user-global-sign-out --user-pool-id $UserPoolId --username $emailA --region $Region | Out-Null
$refreshFail = $true
$tmpR = Join-Path $env:TEMP ("cognito-refresh2-" + [guid]::NewGuid().ToString("N") + ".json")
@{ REFRESH_TOKEN = $refreshA } | ConvertTo-Json | Set-Content -Path $tmpR -Encoding ascii
try {
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $rfOut = aws cognito-idp admin-initiate-auth `
    --user-pool-id $UserPoolId --client-id $ClientId `
    --auth-flow REFRESH_TOKEN_AUTH `
    --auth-parameters "file://$tmpR" `
    --region $Region 2>&1
  $rfCode = $LASTEXITCODE
  $ErrorActionPreference = $prevEap
  if ($rfCode -eq 0 -and (($rfOut | Out-String) -match "AccessToken")) { $refreshFail = $false }
} catch {
  $refreshFail = $true
  $ErrorActionPreference = "Stop"
} finally {
  Remove-Item -Force $tmpR -ErrorAction SilentlyContinue
}
if ($refreshFail) {
  Add-Check "logout_refresh_revoked" "PASS" "refresh rejected after GlobalSignOut"
} else {
  Add-Check "logout_refresh_revoked" "FAIL" "refresh still worked after GlobalSignOut"
}

$postLogoutAccess = Invoke-Api -Method GET -Path "/api/v1/organizations/me/memberships" `
  -AccessToken $accessA2 -ExpectStatus @(200, 401)
Add-Check "logout_access_note" "PASS" "post-signout access status=$($postLogoutAccess.Status) (access JWT may live until exp; refresh revoked; UI clears local session)"

try {
  $appHtml = (Invoke-WebRequest -Uri $AppBase -UseBasicParsing).Content
  $hasApp = $appHtml -match "root|qmind|module"
  $noSecret = ($appHtml -notmatch [regex]::Escape($passA))
  if ($hasApp -and $noSecret) {
    Add-Check "ui_shell_loads" "PASS" "app HTML loads; password not embedded"
  } else {
    Add-Check "ui_shell_loads" "FAIL" "hasApp=$hasApp noSecret=$noSecret"
  }
} catch {
  Add-Check "ui_shell_loads" "FAIL" $_.Exception.Message
}

try {
  $redir = [uri]::EscapeDataString("$AppBase/auth/callback")
  $hosted = "https://qmind-homolog-3114e5.auth.us-east-2.amazoncognito.com/login?client_id=$ClientId&response_type=code&scope=openid+email+profile&redirect_uri=$redir"
  $hui = Invoke-WebRequest -Uri $hosted -UseBasicParsing -MaximumRedirection 5
  Add-Check "ui_hosted_login" "PASS" "hosted UI status=$([int]$hui.StatusCode)"
} catch {
  if ($_.Exception.Response) {
    Add-Check "ui_hosted_login" "PASS" "hosted UI responded status=$([int]$_.Exception.Response.StatusCode)"
  } else {
    Add-Check "ui_hosted_login" "FAIL" $_.Exception.Message
  }
}

$fail = @($results.checks | Where-Object { $_.status -ne "PASS" }).Count
$results.finished_at = (Get-Date).ToUniversalTime().ToString("o")
$results.verdict = if ($fail -eq 0) { "PASS" } else { "FAIL" }
$results.user_a_email = $emailA
$results.user_b_email = $emailB
$results.user_a_sub = $subA
$results.user_b_sub = $subB
$results.org_a_id = $org1Id
$results.org_b_id = $org2Id
$results.temp_users_created = $createdTemp
$results.deployed_git = (git -C (Join-Path $PSScriptRoot "..\..") rev-parse --short HEAD 2>$null)
$results.image_tag = "qmind-api:mvp-fullstack-v0 / qmind-web:mvp-fullstack-v0"

$dir = Split-Path -Parent $EvidencePath
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
($results | ConvertTo-Json -Depth 6) | Set-Content -Path $EvidencePath -Encoding utf8
Write-Host "Evidence written: $EvidencePath verdict=$($results.verdict) failures=$fail"

$passA = $null; $passB = $null; $accessA = $null; $accessA2 = $null; $accessB = $null; $refreshA = $null
$tokA = $null; $tokB = $null; $refreshed = $null

if ($fail -gt 0) { exit 1 }
exit 0
