<#
.SYNOPSIS
  Gate 011 V7b - worker PDF real (enqueue -> process -> download) + org B 404.
#>
param(
  [string] $ApiBase = "https://api.homolog.qmind.com.br",
  [string] $Region = "us-east-2",
  [string] $UserPoolId = "us-east-2_ewD6ck5PM",
  [string] $ClientId = "306r2id1f5gm9vk733v3rlbda6",
  [string] $EvidencePath = (Join-Path $PSScriptRoot "..\terraform-lightsail\WORKER_PDF_V7b_evidence.json"),
  [int] $WaitSeconds = 90
)

$ErrorActionPreference = "Stop"
$ModelId = "c1000000-0000-4000-8000-000000000001"
$SvId = "b1000000-0000-4000-8000-000000000002"
$ReqId = "b1000000-0000-4000-8000-000000000010"
$QuestionId = "c1000000-0000-4000-8000-000000000101"

function New-Pass {
  $b = New-Object byte[] 12
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  return ("W" + ([BitConverter]::ToString($b) -replace "-", "").Substring(0, 10) + "Aa1!")
}

function Invoke-Api {
  param([string]$Method,[string]$Path,[string]$Token,[hashtable]$Hdr=@{},[object]$Body=$null,[int[]]$Expect=@(200))
  $h = @{}
  foreach ($k in $Hdr.Keys) { $h[$k] = $Hdr[$k] }
  if ($Token) { $h["Authorization"] = "Bearer $Token" }
  $p = @{ Method = $Method; Uri = "$ApiBase$Path"; Headers = $h }
  if ($null -ne $Body) { $p.ContentType = "application/json"; $p.Body = ($Body | ConvertTo-Json -Compress -Depth 10) }
  try {
    $r = Invoke-WebRequest @p -UseBasicParsing
    $code = [int]$r.StatusCode; $content = $r.Content
  } catch {
    $resp = $_.Exception.Response
    if (-not $resp) { throw }
    $code = [int]$resp.StatusCode
    $content = if ($_.ErrorDetails.Message) { $_.ErrorDetails.Message } else { "" }
  }
  if ($Expect -notcontains $code) { throw "HTTP $code $Method $Path :: $content" }
  $parsed = $null
  if ($content) { try { $parsed = $content | ConvertFrom-Json } catch { $parsed = $content } }
  return @{ Status = $code; Body = $parsed; Raw = $content }
}

function Ensure-User([string]$Email,[string]$Password) {
  $prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
  aws cognito-idp admin-get-user --user-pool-id $UserPoolId --username $Email --region $Region 2>$null | Out-Null
  $miss = ($LASTEXITCODE -ne 0); $ErrorActionPreference = $prev
  if ($miss) {
    aws cognito-idp admin-create-user --user-pool-id $UserPoolId --username $Email `
      --user-attributes "Name=email,Value=$Email" "Name=email_verified,Value=true" `
      --message-action SUPPRESS --region $Region | Out-Null
  }
  aws cognito-idp admin-set-user-password --user-pool-id $UserPoolId --username $Email `
    --password $Password --permanent --region $Region | Out-Null
}

function Get-Tokens([string]$Email,[string]$Password) {
  $tmp = Join-Path $env:TEMP ("wauth-" + [guid]::NewGuid().ToString("N") + ".json")
  @{ USERNAME = $Email; PASSWORD = $Password } | ConvertTo-Json | Set-Content $tmp -Encoding ascii
  try {
    return (aws cognito-idp admin-initiate-auth --user-pool-id $UserPoolId --client-id $ClientId `
      --auth-flow ADMIN_USER_PASSWORD_AUTH --auth-parameters "file://$tmp" --region $Region --output json | ConvertFrom-Json).AuthenticationResult
  } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
}

function Get-JwtSub([string]$jwt) {
  $p = $jwt.Split(".")[1].Replace("-", "+").Replace("_", "/")
  switch ($p.Length % 4) { 2 { $p += "==" } 3 { $p += "=" } }
  return ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p)) | ConvertFrom-Json).sub
}

function Write-Lf([string]$path,[string]$text) {
  $t = $text -replace "`r`n", "`n" -replace "`r", "`n"
  if (-not $t.EndsWith("`n")) { $t += "`n" }
  [IO.File]::WriteAllBytes($path, [Text.Encoding]::ASCII.GetBytes($t))
}

$results = [ordered]@{
  gate = "011-V7b-worker-pdf"
  started_at = (Get-Date).ToUniversalTime().ToString("o")
  api_base = $ApiBase
  checks = New-Object System.Collections.ArrayList
}
function Add-Check([string]$Id,[string]$Status,[string]$Detail) {
  [void]$results.checks.Add([ordered]@{ id = $Id; status = $Status; detail = $Detail })
  Write-Host "[$Status] $Id - $Detail" -ForegroundColor $(if ($Status -eq "PASS") { "Green" } else { "Red" })
}

$emailA = "qmind.homolog.worker.a+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
$emailQm = "qmind.homolog.worker.qm+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
$emailB = "qmind.homolog.worker.b+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
$passA = New-Pass; $passQm = New-Pass; $passB = New-Pass
Ensure-User $emailA $passA; Ensure-User $emailQm $passQm; Ensure-User $emailB $passB
$accessA = [string](Get-Tokens $emailA $passA).AccessToken
$accessQm = [string](Get-Tokens $emailQm $passQm).AccessToken
$accessB = [string](Get-Tokens $emailB $passB).AccessToken
$subQm = Get-JwtSub $accessQm

Invoke-Api GET "/api/v1/organizations/me/memberships" $accessA | Out-Null
Invoke-Api GET "/api/v1/organizations/me/memberships" $accessQm | Out-Null
Invoke-Api GET "/api/v1/organizations/me/memberships" $accessB | Out-Null

$orgAId = [string](Invoke-Api POST "/api/v1/organizations" $accessA -Body @{ name = "Worker PDF Org A"; timezone = "America/Sao_Paulo" } -Expect @(201)).Body.organization.id
$orgBId = [string](Invoke-Api POST "/api/v1/organizations" $accessB -Body @{ name = "Worker PDF Org B"; timezone = "America/Sao_Paulo" } -Expect @(201)).Body.organization.id
$hA = @{ "X-Organization-Id" = $orgAId }
$hQm = @{ "X-Organization-Id" = $orgAId }
$hB = @{ "X-Organization-Id" = $orgBId }

# Grant QM via SSH
$details = aws lightsail get-instance-access-details --instance-name qmind-homolog-app --region $Region --protocol ssh --output json | ConvertFrom-Json
$ad = $details.accessDetails
$dir = Join-Path $env:TEMP ("wssh-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$pem = Join-Path $dir "id_rsa"; $cert = Join-Path $dir "id_rsa-cert.pub"
Write-Lf $pem $ad.privateKey; Write-Lf $cert $ad.certKey
icacls $pem /inheritance:r | Out-Null; icacls $pem /grant:r "$($env:USERNAME):(R)" | Out-Null
icacls $cert /inheritance:r | Out-Null; icacls $cert /grant:r "$($env:USERNAME):(R)" | Out-Null
$sshTarget = "$($ad.username)@$($ad.ipAddress)"

$sql = @"
INSERT INTO memberships (organization_id, user_id, roles, status)
SELECT '$orgAId', u.id, ARRAY['quality_manager']::text[], 'active'
FROM users u WHERE u.idp_sub = '$subQm'
AND NOT EXISTS (
  SELECT 1 FROM memberships m WHERE m.organization_id='$orgAId' AND m.user_id=u.id AND m.status='active'
);
SELECT c.id::text FROM maturity_criteria c
JOIN maturity_dimensions d ON d.id=c.maturity_dimension_id
JOIN maturity_models m ON m.id=d.maturity_model_id
WHERE m.model_code='qmind_maturity_iso9001' AND m.model_version='0.1.0'
ORDER BY d.sort_order, c.sort_order;
"@
$sqlFile = Join-Path $dir "grant.sql"
[IO.File]::WriteAllBytes($sqlFile, [Text.Encoding]::UTF8.GetBytes(($sql -replace "`r`n", "`n")))
scp -i $pem -o CertificateFile=$cert -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new $sqlFile "${sshTarget}:/tmp/grant.sql" | Out-Null
$critOut = ssh -i $pem -o CertificateFile=$cert -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new $sshTarget "cd /opt/qmind/infra/compose; sudo docker compose -f docker-compose.homolog.yml exec -T db psql -U qmind_admin -d qmind -tA -v ON_ERROR_STOP=1 -f - < /tmp/grant.sql; rm -f /tmp/grant.sql"
$criterionIds = @($critOut -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -match '^[0-9a-f-]{36}$' })
if ($criterionIds.Count -lt 18) { throw "criteria missing: $($criterionIds.Count)" }

$mems = Invoke-Api GET "/api/v1/organizations/me/memberships" $accessA
$leadMid = [string](@($mems.Body) | Where-Object { $_.organization_id -eq $orgAId } | Select-Object -First 1).id

# Minimal journey to published report
$aid = [string](Invoke-Api POST "/api/v1/assessments" $accessA -Hdr $hA -Body @{
  assessment_model_id = $ModelId; standard_version_id = $SvId; type = "diagnosis"
  scope = @(@{ requirement_id = $ReqId })
} -Expect @(201)).Body.id
Invoke-Api POST "/api/v1/assessments/$aid/transitions/plan" $accessA -Hdr $hA | Out-Null
Invoke-Api POST "/api/v1/assessments/$aid/transitions/start" $accessA -Hdr $hA | Out-Null
$iid = [string](Invoke-Api POST "/api/v1/assessments/$aid/interviews" $accessA -Hdr $hA -Body @{ mode = "onsite" } -Expect @(201)).Body.id
Invoke-Api POST "/api/v1/interviews/$iid/answers" $accessA -Hdr $hA -Body @{ body = "campo ok"; question_id = $QuestionId } -Expect @(201, 200) | Out-Null
try { Invoke-Api POST "/api/v1/interviews/$iid/complete" $accessA -Hdr $hA | Out-Null } catch {}

$pdf = [Text.Encoding]::ASCII.GetBytes("%PDF-1.4`nworker-e2e`n%%EOF`n")
$auth = Invoke-Api POST "/api/v1/evidences/authorize" $accessA -Hdr $hA -Body @{
  assessment_id = $aid; content_type = "application/pdf"; declared_byte_size = $pdf.Length
} -Expect @(201)
$eid = [string]$auth.Body.evidence.id
$tmpPdf = Join-Path $env:TEMP "w.pdf"; [IO.File]::WriteAllBytes($tmpPdf, $pdf)
$put = & curl.exe -sS -o NUL -w "%{http_code}" -X PUT -H "Content-Type: application/pdf" --data-binary "@$tmpPdf" -- "$([string]$auth.Body.upload.url)"
Remove-Item $tmpPdf -Force -ErrorAction SilentlyContinue
if ($put -ne "200") { throw "S3 PUT failed $put" }
Invoke-Api POST "/api/v1/evidences/$eid/transitions/receive" $accessA -Hdr $hA | Out-Null
Invoke-Api POST "/api/v1/evidences/$eid/transitions/security_pass" $accessA -Hdr $hA | Out-Null

$fid = [string](Invoke-Api POST "/api/v1/findings" $accessA -Hdr $hA -Body @{
  assessment_id = $aid; finding_type = "conformity"; title = "OK worker"; body = "ok"
  requirement_ids = @($ReqId); evidence_ids = @($eid)
} -Expect @(201)).Body.id
Invoke-Api POST "/api/v1/findings/$fid/transitions/submit" $accessA -Hdr $hA | Out-Null
Invoke-Api POST "/api/v1/findings/$fid/transitions/approve" $accessQm -Hdr $hQm | Out-Null
Invoke-Api POST "/api/v1/assessments/$aid/transitions/begin_analysis" $accessA -Hdr $hA | Out-Null

$mid = [string](Invoke-Api POST "/api/v1/maturity-assessments" $accessA -Hdr $hA -Body @{ assessment_id = $aid } -Expect @(201)).Body.id
$scores = @(); foreach ($cid in $criterionIds) {
  $scores += @{ criterion_id = $cid; applicability = "applicable"; level = 3; rationale = "ok"; evidence_ids = @($eid) }
}
Invoke-Api PUT "/api/v1/maturity-assessments/$mid/scores" $accessA -Hdr $hA -Body @{ scores = $scores } | Out-Null
Invoke-Api POST "/api/v1/maturity-assessments/$mid/transitions/submit" $accessA -Hdr $hA | Out-Null
Invoke-Api POST "/api/v1/maturity-assessments/$mid/transitions/approve" $accessQm -Hdr $hQm | Out-Null
Invoke-Api POST "/api/v1/assessments/$aid/transitions/open_actions" $accessA -Hdr $hA | Out-Null
$planId = [string](Invoke-Api POST "/api/v1/action-plans" $accessA -Hdr $hA -Body @{ assessment_id = $aid } -Expect @(201)).Body.id
$due = (Get-Date).ToUniversalTime().AddDays(7).ToString("o")
$itemId = [string](Invoke-Api POST "/api/v1/action-plans/$planId/items" $accessA -Hdr $hA -Body @{
  finding_id = $fid; action_kind = "improvement"; description = "item"; owner_membership_id = $leadMid
  due_at = $due; efficacy_required = $false
} -Expect @(201)).Body.id
Invoke-Api POST "/api/v1/action-plans/$planId/transitions/activate" $accessA -Hdr $hA | Out-Null
Invoke-Api POST "/api/v1/action-items/$itemId/transitions/start" $accessA -Hdr $hA | Out-Null
Invoke-Api POST "/api/v1/action-items/$itemId/transitions/mark_implemented" $accessA -Hdr $hA | Out-Null
Invoke-Api POST "/api/v1/action-items/$itemId/transitions/validate" $accessQm -Hdr $hQm | Out-Null
Invoke-Api POST "/api/v1/action-plans/$planId/transitions/complete" $accessA -Hdr $hA | Out-Null
Invoke-Api POST "/api/v1/assessments/$aid/transitions/begin_report" $accessA -Hdr $hA | Out-Null

$rid = [string](Invoke-Api POST "/api/v1/reports" $accessA -Hdr $hA -Body @{
  assessment_id = $aid; include_maturity = $true; include_action_plan = $true
} -Expect @(201)).Body.id
Invoke-Api POST "/api/v1/reports/$rid/transitions/submit" $accessA -Hdr $hA | Out-Null
Invoke-Api POST "/api/v1/reports/$rid/transitions/publish" $accessQm -Hdr $hQm | Out-Null
Add-Check "report_published" "PASS" "rid=$rid"

$job1 = Invoke-Api POST "/api/v1/reports/$rid/export-pdf" $accessA -Hdr $hA -Expect @(202)
$job2 = Invoke-Api POST "/api/v1/reports/$rid/export-pdf" $accessA -Hdr $hA -Expect @(202)
$jobId = [string]$job1.Body.id
if ($jobId -ne [string]$job2.Body.id) { throw "enqueue not idempotent" }
Add-Check "enqueue_idempotent" "PASS" "job=$jobId"

$deadline = (Get-Date).AddSeconds($WaitSeconds)
$final = $null
do {
  Start-Sleep -Seconds 2
  $final = Invoke-Api GET "/api/v1/jobs/$jobId" $accessA -Hdr $hA
  Write-Host "job status=$($final.Body.status) attempt=$($final.Body.attempt_count)"
} while ($final.Body.status -notin @("succeeded", "failed") -and (Get-Date) -lt $deadline)

if ([string]$final.Body.status -ne "succeeded") {
  Add-Check "worker_process" "FAIL" "status=$($final.Body.status) err=$($final.Body.error_safe_message)"
  throw "worker did not succeed"
}
Add-Check "worker_process" "PASS" "status=succeeded attempts=$($final.Body.attempt_count) bytes=$($final.Body.output_ref.byte_size)"

$rep = Invoke-Api GET "/api/v1/reports/$rid" $accessA -Hdr $hA
$key = [string]$rep.Body.export_storage_key
if (-not $key -or $key -notmatch "^org/.+/reports/.+/v\d+\.pdf$") {
  Add-Check "storage_key" "FAIL" "key=$key"
  throw "bad storage key"
}
Add-Check "storage_key" "PASS" "key=$key"

$dl = Invoke-Api GET "/api/v1/reports/$rid/export-pdf/download-url" $accessA -Hdr $hA
$url = [string]$dl.Body.url
if ($url -notmatch "X-Amz-Signature|X-Amz-Credential") { throw "expected signed S3 URL" }
$tmpOut = Join-Path $env:TEMP ("report-" + [guid]::NewGuid().ToString("N") + ".pdf")
$code = & curl.exe -sS -o $tmpOut -w "%{http_code}" -- "$url"
$bytes = [IO.File]::ReadAllBytes($tmpOut)
$header = [Text.Encoding]::ASCII.GetString($bytes[0..([Math]::Min(4, $bytes.Length - 1))])
Remove-Item $tmpOut -Force -ErrorAction SilentlyContinue
if ($code -ne "200" -or -not $header.StartsWith("%PDF")) {
  Add-Check "pdf_download_valid" "FAIL" "http=$code header=$header size=$($bytes.Length)"
  throw "invalid pdf download"
}
Add-Check "pdf_download_valid" "PASS" "http=200 size=$($bytes.Length) pdf_header_ok"

$cross1 = Invoke-Api GET "/api/v1/reports/$rid/export-pdf/download-url" $accessB -Hdr $hB -Expect @(403, 404)
$cross2 = Invoke-Api GET "/api/v1/jobs/$jobId" $accessB -Hdr $hB -Expect @(403, 404)
$leak = ($cross1.Raw -match "X-Amz-|org/") -or ($cross2.Raw -match "X-Amz-|org/")
if ($leak) {
  Add-Check "cross_org" "FAIL" "payload leak"
  throw "cross-org leak"
}
Add-Check "cross_org" "PASS" "download=$($cross1.Status) job=$($cross2.Status) no_leak"

# Audit: no signed URL in metadata
$auditSql = "SELECT count(*) FROM platform_audit_events WHERE organization_id='$orgAId' AND (coalesce(metadata::text,'') ILIKE '%X-Amz-%' OR coalesce(metadata::text,'') ILIKE '%Bearer %');"
$auditFile = Join-Path $dir "audit.sql"
[IO.File]::WriteAllBytes($auditFile, [Text.Encoding]::UTF8.GetBytes($auditSql + "`n"))
scp -i $pem -o CertificateFile=$cert -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new $auditFile "${sshTarget}:/tmp/audit.sql" | Out-Null
$hits = (ssh -i $pem -o CertificateFile=$cert -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new $sshTarget "cd /opt/qmind/infra/compose; sudo docker compose -f docker-compose.homolog.yml exec -T db psql -U qmind_admin -d qmind -tA -f - < /tmp/audit.sql; rm -f /tmp/audit.sql").Trim()
if ($hits -ne "0") { Add-Check "audit_no_secrets" "FAIL" "hits=$hits"; throw "secrets in audit" }
Add-Check "audit_no_secrets" "PASS" "secret_hits=0"

$fail = @($results.checks | Where-Object { $_.status -ne "PASS" }).Count
$results.finished_at = (Get-Date).ToUniversalTime().ToString("o")
$results.verdict = if ($fail -eq 0) { "PASS" } else { "FAIL" }
$results.org_a_id = $orgAId; $results.org_b_id = $orgBId
$results.report_id = $rid; $results.job_id = $jobId; $results.export_storage_key = $key
$results.pdf_bytes = $bytes.Length
($results | ConvertTo-Json -Depth 6) | Set-Content $EvidencePath -Encoding utf8
Write-Host "Evidence=$EvidencePath verdict=$($results.verdict)"
if ($fail -gt 0) { exit 1 }
exit 0
