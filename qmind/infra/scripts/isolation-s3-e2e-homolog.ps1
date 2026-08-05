<#
.SYNOPSIS
  Gate 011 V5/V6 â€” isolamento 2 orgs + evidencias S3 reais (homolog).
  Sem senhas/tokens na evidencia.
#>
param(
  [string] $ApiBase = "https://api.homolog.qmind.com.br",
  [string] $Region = "us-east-2",
  [string] $UserPoolId = "us-east-2_ewD6ck5PM",
  [string] $ClientId = "306r2id1f5gm9vk733v3rlbda6",
  [string] $EvidencePath = (Join-Path $PSScriptRoot "..\terraform-lightsail\ISOLATION_S3_V5V6_evidence.json")
)

$ErrorActionPreference = "Stop"
$ModelId = "c1000000-0000-4000-8000-000000000001"
$SvId = "b1000000-0000-4000-8000-000000000002"
$ReqId = "b1000000-0000-4000-8000-000000000010"

function New-HomologPassword {
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  $bytes = New-Object byte[] 16
  $rng.GetBytes($bytes)
  $hex = ([BitConverter]::ToString($bytes) -replace "-", "").Substring(0, 12)
  return ("Iso" + $hex + "Aa1!")
}

function Invoke-Api {
  param([string]$Method,[string]$Path,[string]$AccessToken,[hashtable]$Headers=@{},[object]$Body=$null,[int[]]$ExpectStatus=@(200),[switch]$RawBytes)
  $hdr = @{}
  foreach ($k in $Headers.Keys) { $hdr[$k] = $Headers[$k] }
  if ($AccessToken) { $hdr["Authorization"] = "Bearer $AccessToken" }
  $params = @{ Method=$Method; Uri="$ApiBase$Path"; Headers=$hdr }
  if ($null -ne $Body) {
    $params.ContentType = "application/json"
    $params.Body = ($Body | ConvertTo-Json -Compress -Depth 8)
  }
  try {
    $resp = Invoke-WebRequest @params -UseBasicParsing
    $code = [int]$resp.StatusCode
    $content = $resp.Content
  } catch {
    $r = $_.Exception.Response
    if (-not $r) { throw }
    $code = [int]$r.StatusCode
    $reader = New-Object IO.StreamReader($r.GetResponseStream())
    $content = $reader.ReadToEnd()
  }
  if ($ExpectStatus -notcontains $code) {
    $safe = if ($content -and $content.Length -gt 350) { $content.Substring(0,350) + "..." } else { $content }
    throw "Unexpected $code $Method $Path :: $safe"
  }
  $parsed = $null
  if ($content) { try { $parsed = $content | ConvertFrom-Json } catch { $parsed = $content } }
  return @{ Status=$code; Body=$parsed; Raw=$content }
}

function Ensure-User([string]$Email,[string]$Password) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  aws cognito-idp admin-get-user --user-pool-id $UserPoolId --username $Email --region $Region 2>$null | Out-Null
  $missing = ($LASTEXITCODE -ne 0)
  $ErrorActionPreference = $prev
  if ($missing) {
    aws cognito-idp admin-create-user --user-pool-id $UserPoolId --username $Email `
      --user-attributes "Name=email,Value=$Email" "Name=email_verified,Value=true" `
      --message-action SUPPRESS --region $Region | Out-Null
  }
  aws cognito-idp admin-set-user-password --user-pool-id $UserPoolId --username $Email `
    --password $Password --permanent --region $Region | Out-Null
}

function Get-Tokens([string]$Email,[string]$Password) {
  $tmp = Join-Path $env:TEMP ("auth-" + [guid]::NewGuid().ToString("N") + ".json")
  @{ USERNAME=$Email; PASSWORD=$Password } | ConvertTo-Json | Set-Content $tmp -Encoding ascii
  try {
    $raw = aws cognito-idp admin-initiate-auth --user-pool-id $UserPoolId --client-id $ClientId `
      --auth-flow ADMIN_USER_PASSWORD_AUTH --auth-parameters "file://$tmp" --region $Region --output json | ConvertFrom-Json
    return $raw.AuthenticationResult
  } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
}

$results = [ordered]@{
  gate="011-V5-V6-isolation-s3"; started_at=(Get-Date).ToUniversalTime().ToString("o")
  api_base=$ApiBase; checks=New-Object System.Collections.ArrayList
}
function Add-Check([string]$Id,[string]$Status,[string]$Detail) {
  [void]$results.checks.Add([ordered]@{id=$Id;status=$Status;detail=$Detail})
  Write-Host "[$Status] $Id - $Detail" -ForegroundColor $(if($Status -eq "PASS"){"Green"}else{"Red"})
}

$emailA = "qmind.homolog.iso.a+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
$emailB = "qmind.homolog.iso.b+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
$passA = New-HomologPassword; $passB = New-HomologPassword
Ensure-User $emailA $passA; Ensure-User $emailB $passB
$tokA = Get-Tokens $emailA $passA; $tokB = Get-Tokens $emailB $passB
$accessA = [string]$tokA.AccessToken; $accessB = [string]$tokB.AccessToken

$orgA = Invoke-Api POST "/api/v1/organizations" $accessA -Body @{name="Iso Org A"; timezone="America/Sao_Paulo"} -ExpectStatus @(201)
$orgB = Invoke-Api POST "/api/v1/organizations" $accessB -Body @{name="Iso Org B"; timezone="America/Sao_Paulo"} -ExpectStatus @(201)
$orgAId = [string]$orgA.Body.organization.id
$orgBId = [string]$orgB.Body.organization.id
Add-Check "two_orgs" "PASS" "org_a=$orgAId org_b=$orgBId"

function New-Assessment([string]$Token,[string]$OrgId) {
  $h = @{ "X-Organization-Id" = $OrgId }
  $c = Invoke-Api POST "/api/v1/assessments" $Token -Headers $h -Body @{
    assessment_model_id = $ModelId
    standard_version_id = $SvId
    type = "diagnosis"
    scope = @(@{ requirement_id = $ReqId })
  } -ExpectStatus @(201)
  $aid = [string]$c.Body.id
  Invoke-Api POST "/api/v1/assessments/$aid/transitions/plan" $Token -Headers $h -ExpectStatus @(200) | Out-Null
  Invoke-Api POST "/api/v1/assessments/$aid/transitions/start" $Token -Headers $h -ExpectStatus @(200) | Out-Null
  return $aid
}

$aidA = New-Assessment $accessA $orgAId
$aidB = New-Assessment $accessB $orgBId
Add-Check "assessments_created" "PASS" "aid_a=$aidA aid_b=$aidB"

$listA = Invoke-Api GET "/api/v1/assessments" $accessA -Headers @{ "X-Organization-Id"=$orgAId } -ExpectStatus @(200)
$idsA = @($listA.Body | ForEach-Object { [string]$_.id })
$leakList = $idsA -contains $aidB
if (-not $leakList -and ($idsA -contains $aidA)) { Add-Check "list_isolation" "PASS" "A lists only own assessments" }
else { Add-Check "list_isolation" "FAIL" "leakList=$leakList count=$(@($listA.Body).Count)" }

$crossGet = Invoke-Api GET "/api/v1/assessments/$aidB" $accessA -Headers @{ "X-Organization-Id"=$orgAId } -ExpectStatus @(403,404)
$leakBody = ($crossGet.Raw -match "Iso Org B") -or (($crossGet.Status -eq 200) -and ($crossGet.Raw -match $aidB))
if (-not $leakBody) { Add-Check "get_cross_assessment" "PASS" "status=$($crossGet.Status)" }
else { Add-Check "get_cross_assessment" "FAIL" "leak" }

$wrongOrgHdr = Invoke-Api GET "/api/v1/assessments/$aidB" $accessA -Headers @{ "X-Organization-Id"=$orgBId } -ExpectStatus @(403)
Add-Check "header_org_without_membership" "PASS" "A+OrgB header -> $($wrongOrgHdr.Status)"

# Org switch: A creates nothing in B; B lists own; A re-lists A (no stale B)
$listB = Invoke-Api GET "/api/v1/assessments" $accessB -Headers @{ "X-Organization-Id"=$orgBId } -ExpectStatus @(200)
$listA2 = Invoke-Api GET "/api/v1/assessments" $accessA -Headers @{ "X-Organization-Id"=$orgAId } -ExpectStatus @(200)
$okSwitch = (@($listB.Body | ForEach-Object id) -contains $aidB) -and -not (@($listA2.Body | ForEach-Object id) -contains $aidB)
if ($okSwitch) { Add-Check "org_switch_no_cache_leak" "PASS" "B sees B; A re-list still isolated" }
else { Add-Check "org_switch_no_cache_leak" "FAIL" "cache/isolation issue" }

# --- S3 evidence path on Org A ---
$pdf = [Text.Encoding]::ASCII.GetBytes("%PDF-1.4`n%qmind-homolog-evidence`ntrailer`n%%EOF`n")
$auth = Invoke-Api POST "/api/v1/evidences/authorize" $accessA -Headers @{ "X-Organization-Id"=$orgAId } -Body @{
  assessment_id = $aidA
  content_type = "application/pdf"
  declared_byte_size = $pdf.Length
} -ExpectStatus @(201)
$eidA = [string]$auth.Body.evidence.id
$uploadUrl = [string]$auth.Body.upload.url
$uploadHost = ([uri]$uploadUrl).Host
Add-Check "s3_authorize" "PASS" "evidence=$eidA upload_host=$uploadHost expires=$($auth.Body.upload.expires_in_seconds)"

# PUT bytes via curl (PowerShell may alter Content-Type and break SigV4)
$tmpPdf = Join-Path $env:TEMP ("ev-" + [guid]::NewGuid().ToString("N") + ".pdf")
[IO.File]::WriteAllBytes($tmpPdf, $pdf)
try {
  $putOut = & curl.exe -sS -o NUL -w "%{http_code}" -X PUT -H "Content-Type: application/pdf" --data-binary "@$tmpPdf" -- "$uploadUrl"
  if ($putOut -eq "200" -or $putOut -eq "204") {
    Add-Check "s3_put" "PASS" "status=$putOut"
  } else {
    Add-Check "s3_put" "FAIL" "status=$putOut"
  }
} catch {
  Add-Check "s3_put" "FAIL" $_.Exception.Message
} finally {
  Remove-Item $tmpPdf -Force -ErrorAction SilentlyContinue
}

# Allow object_missing if put failed; otherwise expect 200
$recv = Invoke-Api POST "/api/v1/evidences/$eidA/transitions/receive" $accessA -Headers @{ "X-Organization-Id"=$orgAId } -ExpectStatus @(200, 422)
if ($recv.Status -ne 200) {
  Add-Check "s3_receive_hash_size" "FAIL" "receive status=$($recv.Status) (put may have failed)"
  Add-Check "s3_security_pass" "FAIL" "skipped"
  Add-Check "s3_download" "FAIL" "skipped"
} else {
$hash = [string]$recv.Body.evidence.content_hash
$size = [int]$recv.Body.evidence.byte_size
$ctype = [string]$recv.Body.evidence.content_type
if ($recv.Body.to_status -eq "quarantined" -and $size -eq $pdf.Length -and $hash -like "sha256:*") {
  Add-Check "s3_receive_hash_size" "PASS" "status=quarantined size=$size hash_prefix=$($hash.Substring(0,15))... type=$ctype"
} else {
  Add-Check "s3_receive_hash_size" "FAIL" "to=$($recv.Body.to_status) size=$size"
}

$passSec = Invoke-Api POST "/api/v1/evidences/$eidA/transitions/security_pass" $accessA -Headers @{ "X-Organization-Id"=$orgAId } -ExpectStatus @(200)
Add-Check "s3_security_pass" "PASS" "to=$($passSec.Body.to_status)"

$dl = Invoke-Api GET "/api/v1/evidences/$eidA/download-url" $accessA -Headers @{ "X-Organization-Id"=$orgAId } -ExpectStatus @(200)
$dlUrl = [string]$dl.Body.url
$dlHost = ([uri]$dlUrl).Host
try {
  $tmpDl = Join-Path $env:TEMP ("dl-" + [guid]::NewGuid().ToString("N") + ".pdf")
  $codeDl = & curl.exe -sS -o $tmpDl -w "%{http_code}" $dlUrl
  $lenDl = if (Test-Path $tmpDl) { (Get-Item $tmpDl).Length } else { 0 }
  Remove-Item $tmpDl -Force -ErrorAction SilentlyContinue
  if ($codeDl -eq "200" -and $lenDl -eq $pdf.Length) {
    Add-Check "s3_download" "PASS" "bytes=$lenDl host=$dlHost expires=$($dl.Body.expires_in_seconds)"
  } else {
    Add-Check "s3_download" "FAIL" "status=$codeDl len=$lenDl"
  }
} catch {
  Add-Check "s3_download" "FAIL" $_.Exception.Message
}
}

# Cross-org: B cannot get A's evidence
$crossEv = Invoke-Api GET "/api/v1/evidences/$eidA" $accessB -Headers @{ "X-Organization-Id"=$orgBId } -ExpectStatus @(403,404)
$crossDl = Invoke-Api GET "/api/v1/evidences/$eidA/download-url" $accessB -Headers @{ "X-Organization-Id"=$orgBId } -ExpectStatus @(403,404)
$leakEv = ($crossEv.Raw -match "sha256:") -or ($crossDl.Raw -match "X-Amz-")
if (-not $leakEv) { Add-Check "s3_cross_org" "PASS" "get=$($crossEv.Status) download=$($crossDl.Status) no hash/url leak" }
else { Add-Check "s3_cross_org" "FAIL" "data leak in error body" }

# Type/size mismatch on receive (Org B path)
$authBad = Invoke-Api POST "/api/v1/evidences/authorize" $accessB -Headers @{ "X-Organization-Id"=$orgBId } -Body @{
  assessment_id = $aidB
  content_type = "application/pdf"
  declared_byte_size = 100
} -ExpectStatus @(201)
$eidBad = [string]$authBad.Body.evidence.id
$badUrl = [string]$authBad.Body.upload.url
$badHdr = @{}
if ($authBad.Body.upload.headers) {
  $authBad.Body.upload.headers.PSObject.Properties | ForEach-Object { $badHdr[$_.Name] = [string]$_.Value }
}
$wrong = [Text.Encoding]::ASCII.GetBytes("not-a-pdf-and-wrong-size")
$tmpBad = Join-Path $env:TEMP ("bad-" + [guid]::NewGuid().ToString("N") + ".bin")
[IO.File]::WriteAllBytes($tmpBad, $wrong)
try {
  & curl.exe -sS -o NUL -X PUT -H "Content-Type: application/pdf" --data-binary "@$tmpBad" -- "$badUrl" | Out-Null
} finally { Remove-Item $tmpBad -Force -ErrorAction SilentlyContinue }
$recvBad = Invoke-Api POST "/api/v1/evidences/$eidBad/transitions/receive" $accessB -Headers @{ "X-Organization-Id"=$orgBId } -ExpectStatus @(422,409,400)
Add-Check "s3_reject_mismatch" "PASS" "receive mismatch status=$($recvBad.Status)"

$fail = @($results.checks | Where-Object { $_.status -ne "PASS" }).Count
$results.finished_at = (Get-Date).ToUniversalTime().ToString("o")
$results.verdict = if ($fail -eq 0) { "PASS" } else { "FAIL" }
$results.user_a_email = $emailA; $results.user_b_email = $emailB
$results.org_a_id = $orgAId; $results.org_b_id = $orgBId
$results.assessment_a_id = $aidA; $results.assessment_b_id = $aidB
$results.evidence_a_id = $eidA
$results.deployed_git = (git -C (Join-Path $PSScriptRoot "..\..") rev-parse --short HEAD 2>$null)
($results | ConvertTo-Json -Depth 6) | Set-Content $EvidencePath -Encoding utf8
Write-Host "Evidence: $EvidencePath verdict=$($results.verdict) failures=$fail"

$passA=$null;$passB=$null;$accessA=$null;$accessB=$null;$tokA=$null;$tokB=$null;$uploadUrl=$null;$dlUrl=$null
if ($fail -gt 0) { exit 1 }
exit 0
