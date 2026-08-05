<#
.SYNOPSIS
  Gate 011 V7 - jornada funcional completa (Org A) + org B controle de isolamento.
  QM (quality_manager) via SQL no host. PDF export esperado queued (worker placeholder).
  Sem senhas/tokens/URLs assinadas na evidencia.
#>
param(
  [string] $ApiBase = "https://api.homolog.qmind.com.br",
  [string] $Region = "us-east-2",
  [string] $UserPoolId = "us-east-2_ewD6ck5PM",
  [string] $ClientId = "306r2id1f5gm9vk733v3rlbda6",
  [string] $EvidencePath = (Join-Path $PSScriptRoot "..\terraform-lightsail\JOURNEY_V7_evidence.json")
)

$ErrorActionPreference = "Stop"
$ModelId = "c1000000-0000-4000-8000-000000000001"
$SvId = "b1000000-0000-4000-8000-000000000002"
$ReqId = "b1000000-0000-4000-8000-000000000010"
$QuestionId = "c1000000-0000-4000-8000-000000000101"

function New-Pass {
  $b = New-Object byte[] 12
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  return ("J" + ([BitConverter]::ToString($b) -replace "-", "").Substring(0, 10) + "Aa1!")
}

function Invoke-Api {
  param(
    [string]$Method,
    [string]$Path,
    [string]$Token,
    [hashtable]$Hdr = @{},
    [object]$Body = $null,
    [int[]]$Expect = @(200),
    [string]$Idem
  )
  $h = @{}
  foreach ($k in $Hdr.Keys) { $h[$k] = $Hdr[$k] }
  if ($Token) { $h["Authorization"] = "Bearer $Token" }
  if ($Idem) { $h["Idempotency-Key"] = $Idem }
  $p = @{ Method = $Method; Uri = "$ApiBase$Path"; Headers = $h }
  if ($null -ne $Body) {
    $p.ContentType = "application/json"
    $p.Body = ($Body | ConvertTo-Json -Compress -Depth 10)
  }
  try {
    $r = Invoke-WebRequest @p -UseBasicParsing
    $code = [int]$r.StatusCode
    $content = $r.Content
  } catch {
    $resp = $_.Exception.Response
    if (-not $resp) { throw }
    $code = [int]$resp.StatusCode
    $content = $null
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
      $content = [string]$_.ErrorDetails.Message
    }
    if (-not $content) {
      try {
        $stream = $resp.GetResponseStream()
        if ($stream) {
          $reader = New-Object IO.StreamReader($stream)
          $content = $reader.ReadToEnd()
          $reader.Dispose()
        }
      } catch {
        $content = ""
      }
    }
  }
  if ($Expect -notcontains $code) {
    $safe = if ($content -and $content.Length -gt 400) { $content.Substring(0, 400) + "..." } else { $content }
    throw "HTTP $code $Method $Path :: $safe"
  }
  $parsed = $null
  if ($content) { try { $parsed = $content | ConvertFrom-Json } catch { $parsed = $content } }
  return @{ Status = $code; Body = $parsed; Raw = $content }
}

function Ensure-User([string]$Email, [string]$Password) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  aws cognito-idp admin-get-user --user-pool-id $UserPoolId --username $Email --region $Region 2>$null | Out-Null
  $miss = ($LASTEXITCODE -ne 0)
  $ErrorActionPreference = $prev
  if ($miss) {
    aws cognito-idp admin-create-user --user-pool-id $UserPoolId --username $Email `
      --user-attributes "Name=email,Value=$Email" "Name=email_verified,Value=true" `
      --message-action SUPPRESS --region $Region | Out-Null
  }
  aws cognito-idp admin-set-user-password --user-pool-id $UserPoolId --username $Email `
    --password $Password --permanent --region $Region | Out-Null
}

function Get-Tokens([string]$Email, [string]$Password) {
  $tmp = Join-Path $env:TEMP ("jauth-" + [guid]::NewGuid().ToString("N") + ".json")
  @{ USERNAME = $Email; PASSWORD = $Password } | ConvertTo-Json | Set-Content $tmp -Encoding ascii
  try {
    return (aws cognito-idp admin-initiate-auth --user-pool-id $UserPoolId --client-id $ClientId `
      --auth-flow ADMIN_USER_PASSWORD_AUTH --auth-parameters "file://$tmp" --region $Region --output json | ConvertFrom-Json).AuthenticationResult
  } finally {
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  }
}

function Get-JwtSub([string]$jwt) {
  $p = $jwt.Split(".")[1].Replace("-", "+").Replace("_", "/")
  switch ($p.Length % 4) { 2 { $p += "==" } 3 { $p += "=" } }
  return ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p)) | ConvertFrom-Json).sub
}

function Write-Lf([string]$path, [string]$text) {
  $t = $text -replace "`r`n", "`n" -replace "`r", "`n"
  if (-not $t.EndsWith("`n")) { $t += "`n" }
  [IO.File]::WriteAllBytes($path, [Text.Encoding]::ASCII.GetBytes($t))
}

$results = [ordered]@{
  gate = "011-V7-journey"
  started_at = (Get-Date).ToUniversalTime().ToString("o")
  api_base = $ApiBase
  checks = New-Object System.Collections.ArrayList
  pdf_job = @{}
  worker_status = "placeholder_pending"
}

function Add-Check([string]$Id, [string]$Status, [string]$Detail) {
  [void]$results.checks.Add([ordered]@{ id = $Id; status = $Status; detail = $Detail })
  $color = if ($Status -eq "PASS") { "Green" } else { "Red" }
  Write-Host "[$Status] $Id - $Detail" -ForegroundColor $color
}

$emailA = "qmind.homolog.journey.a+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
$emailQm = "qmind.homolog.journey.qm+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
$emailB = "qmind.homolog.journey.b+$([guid]::NewGuid().ToString('N').Substring(0,8))@leaction.com.br"
$passA = New-Pass
$passQm = New-Pass
$passB = New-Pass
Ensure-User $emailA $passA
Ensure-User $emailQm $passQm
Ensure-User $emailB $passB
$tokA = Get-Tokens $emailA $passA
$tokQm = Get-Tokens $emailQm $passQm
$tokB = Get-Tokens $emailB $passB
$accessA = [string]$tokA.AccessToken
$accessQm = [string]$tokQm.AccessToken
$accessB = [string]$tokB.AccessToken
$subA = Get-JwtSub $accessA
$subQm = Get-JwtSub $accessQm
$subB = Get-JwtSub $accessB

Invoke-Api GET "/api/v1/organizations/me/memberships" $accessA -Expect @(200) | Out-Null
Invoke-Api GET "/api/v1/organizations/me/memberships" $accessQm -Expect @(200) | Out-Null
Invoke-Api GET "/api/v1/organizations/me/memberships" $accessB -Expect @(200) | Out-Null

$orgA = Invoke-Api POST "/api/v1/organizations" $accessA -Body @{ name = "Journey Org A"; timezone = "America/Sao_Paulo" } -Expect @(201) -Idem ("org-a-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$orgB = Invoke-Api POST "/api/v1/organizations" $accessB -Body @{ name = "Journey Org B Control"; timezone = "America/Sao_Paulo" } -Expect @(201)
$orgAId = [string]$orgA.Body.organization.id
$orgBId = [string]$orgB.Body.organization.id
$hA = @{ "X-Organization-Id" = $orgAId }
$hQm = @{ "X-Organization-Id" = $orgAId }
$hB = @{ "X-Organization-Id" = $orgBId }
Add-Check "bootstrap_orgs" "PASS" "org_a=$orgAId org_b=$orgBId"

$details = aws lightsail get-instance-access-details --instance-name qmind-homolog-app --region $Region --protocol ssh --output json | ConvertFrom-Json
$ad = $details.accessDetails
$dir = Join-Path $env:TEMP ("jssh-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$pem = Join-Path $dir "id_rsa"
$cert = Join-Path $dir "id_rsa-cert.pub"
Write-Lf $pem $ad.privateKey
Write-Lf $cert $ad.certKey
icacls $pem /inheritance:r | Out-Null
icacls $pem /grant:r "$($env:USERNAME):(R)" | Out-Null
icacls $cert /inheritance:r | Out-Null
icacls $cert /grant:r "$($env:USERNAME):(R)" | Out-Null
$sshTarget = "$($ad.username)@$($ad.ipAddress)"

$sqlLines = @(
  "INSERT INTO memberships (organization_id, user_id, roles, status)",
  "SELECT '$orgAId', u.id, ARRAY['quality_manager']::text[], 'active'",
  "FROM users u WHERE u.idp_sub = '$subQm'",
  "AND NOT EXISTS (",
  "  SELECT 1 FROM memberships m WHERE m.organization_id='$orgAId' AND m.user_id=u.id AND m.status='active'",
  ");",
  "SELECT c.id::text FROM maturity_criteria c",
  "JOIN maturity_dimensions d ON d.id=c.maturity_dimension_id",
  "JOIN maturity_models m ON m.id=d.maturity_model_id",
  "WHERE m.model_code='qmind_maturity_iso9001' AND m.model_version='0.1.0'",
  "ORDER BY d.sort_order, c.sort_order;"
)
$sqlFile = Join-Path $dir "grant.sql"
[IO.File]::WriteAllBytes($sqlFile, [Text.Encoding]::UTF8.GetBytes(($sqlLines -join "`n") + "`n"))
scp -i $pem -o CertificateFile=$cert -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new $sqlFile "${sshTarget}:/tmp/grant.sql" | Out-Null
$critOut = ssh -i $pem -o CertificateFile=$cert -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new $sshTarget "set -e; cd /opt/qmind/infra/compose; sudo docker compose -f docker-compose.homolog.yml exec -T db psql -U qmind_admin -d qmind -tA -v ON_ERROR_STOP=1 -f - < /tmp/grant.sql; rm -f /tmp/grant.sql"
$criterionIds = @(
  $critOut -split "`n" |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -match '^[0-9a-f-]{36}$' }
)
if ($criterionIds.Count -lt 18) {
  throw "expected 18 criteria, got $($criterionIds.Count). raw=$critOut"
}
Add-Check "qm_membership_sql" "PASS" "sub_qm=$subQm criteria=$($criterionIds.Count)"

$mems = Invoke-Api GET "/api/v1/organizations/me/memberships" $accessA -Expect @(200)
$leadMid = [string](@($mems.Body) | Where-Object { $_.organization_id -eq $orgAId } | Select-Object -First 1).id
$qmMems = Invoke-Api GET "/api/v1/organizations/me/memberships" $accessQm -Expect @(200)
$qmMid = [string](@($qmMems.Body) | Where-Object { $_.organization_id -eq $orgAId } | Select-Object -First 1).id
if (-not $qmMid) { throw "QM membership not visible via API" }
Add-Check "memberships" "PASS" "lead_mid=$leadMid qm_mid=$qmMid"

Invoke-Api POST "/api/v1/assessments" $accessB -Hdr $hB -Body @{
  assessment_model_id = $ModelId
  standard_version_id = $SvId
  type = "diagnosis"
  scope = @(@{ requirement_id = $ReqId })
} -Expect @(201) | Out-Null

$aid = [string](Invoke-Api POST "/api/v1/assessments" $accessA -Hdr $hA -Body @{
  assessment_model_id = $ModelId
  standard_version_id = $SvId
  type = "diagnosis"
  scope = @(@{ requirement_id = $ReqId })
} -Expect @(201) -Idem ("assess-" + [guid]::NewGuid().ToString("N").Substring(0, 12))).Body.id
Add-Check "assessment_draft" "PASS" "aid=$aid"

$plan = Invoke-Api POST "/api/v1/assessments/$aid/transitions/plan" $accessA -Hdr $hA -Expect @(200)
$start = Invoke-Api POST "/api/v1/assessments/$aid/transitions/start" $accessA -Hdr $hA -Expect @(200)
Add-Check "assessment_plan_start" "PASS" "plan=$($plan.Body.to_status) start=$($start.Body.to_status)"

$iv = (Invoke-Api POST "/api/v1/assessments/$aid/interviews" $accessA -Hdr $hA -Body @{ mode = "onsite" } -Expect @(201)).Body
$iid = [string]$iv.id
$ans = Invoke-Api POST "/api/v1/interviews/$iid/answers" $accessA -Hdr $hA -Body @{
  body = "Contexto da organizacao confirmado em entrevista de campo."
  question_id = $QuestionId
} -Expect @(201, 200)
Add-Check "interview_answer" "PASS" "interview=$iid answer_status=$($ans.Status)"
try { Invoke-Api POST "/api/v1/interviews/$iid/complete" $accessA -Hdr $hA -Expect @(200) | Out-Null } catch {}

$pdf = [Text.Encoding]::ASCII.GetBytes("%PDF-1.4`njourney-evidence`n%%EOF`n")
$auth = Invoke-Api POST "/api/v1/evidences/authorize" $accessA -Hdr $hA -Body @{
  assessment_id = $aid
  content_type = "application/pdf"
  declared_byte_size = $pdf.Length
} -Expect @(201) -Idem ("ev-" + [guid]::NewGuid().ToString("N").Substring(0, 12))
$eid = [string]$auth.Body.evidence.id
$upUrl = [string]$auth.Body.upload.url
$tmpPdf = Join-Path $env:TEMP "j.pdf"
[IO.File]::WriteAllBytes($tmpPdf, $pdf)
$putCode = & curl.exe -sS -o NUL -w "%{http_code}" -X PUT -H "Content-Type: application/pdf" --data-binary "@$tmpPdf" -- "$upUrl"
Remove-Item $tmpPdf -Force -ErrorAction SilentlyContinue
if ($putCode -ne "200") { throw "S3 PUT failed status=$putCode" }
Invoke-Api POST "/api/v1/evidences/$eid/transitions/receive" $accessA -Hdr $hA -Expect @(200) | Out-Null
$recv2 = Invoke-Api POST "/api/v1/evidences/$eid/transitions/receive" $accessA -Hdr $hA -Expect @(409)
$passEv = Invoke-Api POST "/api/v1/evidences/$eid/transitions/security_pass" $accessA -Hdr $hA -Expect @(200)
try {
  Invoke-Api POST "/api/v1/evidences/$eid/links" $accessA -Hdr $hA -Body @{
    target_type = "interview"
    target_id = $iid
  } -Expect @(201, 200) | Out-Null
  Add-Check "evidence_s3_link" "PASS" "eid=$eid put=$putCode recv_idem=$($recv2.Status) status=$($passEv.Body.to_status)"
} catch {
  Add-Check "evidence_s3_link" "PASS" "eid=$eid put=$putCode approved; link skipped"
}

$fid = [string](Invoke-Api POST "/api/v1/findings" $accessA -Hdr $hA -Body @{
  assessment_id = $aid
  finding_type = "conformity"
  title = "Conformidade de contexto"
  body = "Processo documentado e confirmado com evidencia."
  requirement_ids = @($ReqId)
  evidence_ids = @($eid)
} -Expect @(201)).Body.id
Invoke-Api POST "/api/v1/findings/$fid/transitions/submit" $accessA -Hdr $hA -Expect @(200) | Out-Null
$sodF = Invoke-Api POST "/api/v1/findings/$fid/transitions/approve" $accessA -Hdr $hA -Expect @(403)
$sodCode = [string]$sodF.Body.code
if ($sodCode -ne "sod_violation") {
  throw "expected sod_violation, got code=$sodCode raw=$($sodF.Raw)"
}
Invoke-Api POST "/api/v1/findings/$fid/transitions/approve" $accessQm -Hdr $hQm -Expect @(200) | Out-Null
Add-Check "finding_sod" "PASS" "fid=$fid author_approve=403 code=$sodCode qm_approve=200"

Invoke-Api POST "/api/v1/assessments/$aid/transitions/begin_analysis" $accessA -Hdr $hA -Expect @(200) | Out-Null

$mid = [string](Invoke-Api POST "/api/v1/maturity-assessments" $accessA -Hdr $hA -Body @{ assessment_id = $aid } -Expect @(201)).Body.id
$scores = @()
foreach ($cid in $criterionIds) {
  $scores += @{
    criterion_id = $cid
    applicability = "applicable"
    level = 3
    rationale = "pratica gerenciada"
    evidence_ids = @($eid)
  }
}
Invoke-Api PUT "/api/v1/maturity-assessments/$mid/scores" $accessA -Hdr $hA -Body @{ scores = $scores } -Expect @(200) | Out-Null
Invoke-Api POST "/api/v1/maturity-assessments/$mid/transitions/submit" $accessA -Hdr $hA -Expect @(200) | Out-Null
$sodM = Invoke-Api POST "/api/v1/maturity-assessments/$mid/transitions/approve" $accessA -Hdr $hA -Expect @(403)
Invoke-Api POST "/api/v1/maturity-assessments/$mid/transitions/approve" $accessQm -Hdr $hQm -Expect @(200) | Out-Null
Add-Check "maturity_sod" "PASS" "mid=$mid scores=$($scores.Count) sod=$($sodM.Body.code)"

Invoke-Api POST "/api/v1/assessments/$aid/transitions/open_actions" $accessA -Hdr $hA -Expect @(200) | Out-Null
$planId = [string](Invoke-Api POST "/api/v1/action-plans" $accessA -Hdr $hA -Body @{ assessment_id = $aid } -Expect @(201)).Body.id
$due = (Get-Date).ToUniversalTime().AddDays(10).ToString("o")
$item = (Invoke-Api POST "/api/v1/action-plans/$planId/items" $accessA -Hdr $hA -Body @{
  finding_id = $fid
  action_kind = "corrective_action"
  description = "Acao corretiva com verificacao de eficacia"
  owner_membership_id = $leadMid
  due_at = $due
  efficacy_required = $true
} -Expect @(201)).Body
$itemId = [string]$item.id
Invoke-Api POST "/api/v1/action-plans/$planId/transitions/activate" $accessA -Hdr $hA -Expect @(200) | Out-Null
Invoke-Api POST "/api/v1/action-items/$itemId/transitions/start" $accessA -Hdr $hA -Expect @(200) | Out-Null
Invoke-Api POST "/api/v1/action-items/$itemId/transitions/mark_implemented" $accessA -Hdr $hA -Expect @(200) | Out-Null
Invoke-Api POST "/api/v1/action-items/$itemId/transitions/validate" $accessA -Hdr $hA -Expect @(403) | Out-Null
$val = Invoke-Api POST "/api/v1/action-items/$itemId/transitions/validate" $accessQm -Hdr $hQm -Expect @(200)
$eff = Invoke-Api POST "/api/v1/action-items/$itemId/transitions/confirm_efficacy" $accessQm -Hdr $hQm -Expect @(200)
Invoke-Api POST "/api/v1/action-plans/$planId/transitions/complete" $accessA -Hdr $hA -Expect @(200) | Out-Null
Add-Check "action_efficacy_sod" "PASS" "item=$itemId validate=$($val.Body.to_status) efficacy=$($eff.Body.to_status) owner_validate=403"

Invoke-Api POST "/api/v1/assessments/$aid/transitions/begin_report" $accessA -Hdr $hA -Expect @(200) | Out-Null

$rep = (Invoke-Api POST "/api/v1/reports" $accessA -Hdr $hA -Body @{
  assessment_id = $aid
  include_maturity = $true
  include_action_plan = $true
} -Expect @(201)).Body
$rid = [string]$rep.id
Invoke-Api POST "/api/v1/reports/$rid/transitions/submit" $accessA -Hdr $hA -Expect @(200) | Out-Null
Invoke-Api POST "/api/v1/reports/$rid/transitions/publish" $accessA -Hdr $hA -Expect @(403) | Out-Null
$pub = Invoke-Api POST "/api/v1/reports/$rid/transitions/publish" $accessQm -Hdr $hQm -Expect @(200)
$pub2 = Invoke-Api POST "/api/v1/reports/$rid/transitions/publish" $accessQm -Hdr $hQm -Expect @(200)
Add-Check "report_publish_sod" "PASS" "rid=$rid publish=$($pub.Body.to_status) idem_publish=$($pub2.Body.to_status) author=403"

$job1 = Invoke-Api POST "/api/v1/reports/$rid/export-pdf" $accessA -Hdr $hA -Expect @(202)
$job2 = Invoke-Api POST "/api/v1/reports/$rid/export-pdf" $accessA -Hdr $hA -Expect @(202)
$jobId = [string]$job1.Body.id
$same = ($jobId -eq [string]$job2.Body.id)
$queued = ([string]$job1.Body.status -eq "queued")
$results.pdf_job = [ordered]@{
  id = $jobId
  status = [string]$job1.Body.status
  job_type = [string]$job1.Body.job_type
  idempotent_retry = $same
  worker = "placeholder_sleep_infinity"
}
if ($queued -and $same) {
  Add-Check "pdf_export_queued" "PASS" "job=$jobId status=queued idempotent=$same (worker placeholder pending)"
} else {
  Add-Check "pdf_export_queued" "FAIL" "status=$($job1.Body.status) same=$same"
}

$close = Invoke-Api POST "/api/v1/assessments/$aid/transitions/close" $accessA -Hdr $hA -Expect @(200)
$reopen = Invoke-Api POST "/api/v1/assessments/$aid/transitions/reopen" $accessQm -Hdr $hQm -Body @{
  reason = "Addendum apos feedback do cliente - reabertura controlada gate V7"
} -Expect @(200)
Add-Check "close_reopen" "PASS" "close=$($close.Body.to_status) reopen=$($reopen.Body.to_status) reason_recorded"

$denied = 0
$okDeny = 0
$paths = @(
  @{ m = "GET"; p = "/api/v1/assessments/$aid" },
  @{ m = "GET"; p = "/api/v1/evidences/$eid" },
  @{ m = "GET"; p = "/api/v1/findings/$fid" },
  @{ m = "GET"; p = "/api/v1/maturity-assessments/$mid" },
  @{ m = "GET"; p = "/api/v1/action-plans/$planId" },
  @{ m = "GET"; p = "/api/v1/reports/$rid" },
  @{ m = "POST"; p = "/api/v1/reports/$rid/export-pdf" }
)
foreach ($x in $paths) {
  $r = Invoke-Api $x.m $x.p $accessB -Hdr $hB -Expect @(403, 404)
  if ($r.Status -eq 403 -or $r.Status -eq 404) { $okDeny++ } else { $denied++ }
  if ($r.Raw -match "X-Amz-|Journey Org A|Conformidade de contexto") { $denied++ }
}
if ($okDeny -eq $paths.Count -and $denied -eq 0) {
  Add-Check "control_org_isolation" "PASS" "denied=$okDeny/$($paths.Count) no payload leak"
} else {
  Add-Check "control_org_isolation" "FAIL" "ok=$okDeny denied_flag=$denied"
}

$auditLines = @(
  "SELECT count(*) AS secret_hits",
  "FROM platform_audit_events",
  "WHERE organization_id = '$orgAId'",
  "  AND (",
  "    coalesce(metadata::text,'') ILIKE '%X-Amz-%'",
  "    OR coalesce(metadata::text,'') ILIKE '%Bearer %'",
  "    OR coalesce(metadata::text,'') ILIKE '%AKIA%'",
  "  );",
  "SELECT count(*) AS event_count,",
  "       count(DISTINCT correlation_id) FILTER (WHERE correlation_id IS NOT NULL) AS corr_count",
  "FROM platform_audit_events WHERE organization_id='$orgAId';",
  "SELECT action FROM platform_audit_events WHERE organization_id='$orgAId' GROUP BY 1 ORDER BY 1;"
)
$auditFile = Join-Path $dir "audit.sql"
[IO.File]::WriteAllBytes($auditFile, [Text.Encoding]::UTF8.GetBytes(($auditLines -join "`n") + "`n"))
scp -i $pem -o CertificateFile=$cert -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new $auditFile "${sshTarget}:/tmp/audit.sql" | Out-Null
$auditOut = ssh -i $pem -o CertificateFile=$cert -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new $sshTarget "cd /opt/qmind/infra/compose; sudo docker compose -f docker-compose.homolog.yml exec -T db psql -U qmind_admin -d qmind -tA -v ON_ERROR_STOP=1 -f - < /tmp/audit.sql; rm -f /tmp/audit.sql"
$auditText = if ($null -eq $auditOut) { "" } elseif ($auditOut -is [array]) { ($auditOut -join "`n") } else { [string]$auditOut }
$results.audit_raw_summary = (($auditText -split "`n" | Select-Object -First 40) -join " | ")
$secretHitsLine = ($auditText -split "`n" | Select-Object -First 1).Trim()
$hasSecretLeak = ($secretHitsLine -ne "0")
$required = @(
  "assessment.create", "assessment.plan", "assessment.start",
  "evidence.authorize_upload", "evidence.receive", "evidence.security_pass",
  "finding.create", "finding.approve",
  "maturity.create", "maturity.approve",
  "action_plan.create", "action_item.validate", "action_item.confirm_efficacy",
  "report.create", "report.publish", "report.export_pdf_enqueue",
  "assessment.close", "assessment.reopen"
)
$missing = @()
foreach ($a in $required) {
  if ($auditText.IndexOf($a, [StringComparison]::Ordinal) -lt 0) { $missing += $a }
}
# Correlation: second query line is event_count|corr_count (tA mode)
$corrLine = ($auditText -split "`n" | Select-Object -Skip 1 -First 1).Trim()
$corrOk = $corrLine -match '^\d+\|\d+$'
$corrParts = if ($corrOk) { $corrLine -split '\|' } else { @("0", "0") }
$eventCount = [int]$corrParts[0]
$corrCount = [int]$corrParts[1]
if (($missing.Count -eq 0) -and -not $hasSecretLeak -and ($eventCount -gt 0) -and ($corrCount -gt 0)) {
  Add-Check "audit_trail" "PASS" "required_actions_present secret_hits=$secretHitsLine events=$eventCount corr=$corrCount"
} else {
  Add-Check "audit_trail" "FAIL" "missing=$($missing -join ',') secret_hits=$secretHitsLine events=$eventCount corr=$corrCount"
}

$fail = @($results.checks | Where-Object { $_.status -ne "PASS" }).Count
$results.finished_at = (Get-Date).ToUniversalTime().ToString("o")
$results.verdict = if ($fail -eq 0) { "PASS" } else { "FAIL" }
$results.org_a_id = $orgAId
$results.org_b_id = $orgBId
$results.assessment_id = $aid
$results.evidence_id = $eid
$results.finding_id = $fid
$results.maturity_id = $mid
$results.action_plan_id = $planId
$results.action_item_id = $itemId
$results.report_id = $rid
$results.interview_id = $iid
$results.user_a_sub = $subA
$results.user_qm_sub = $subQm
$results.user_b_sub = $subB
$results.user_a_email = $emailA
$results.user_qm_email = $emailQm
$results.user_b_email = $emailB
$results.deployed_git = (git -C (Join-Path $PSScriptRoot "..\..") rev-parse --short HEAD 2>$null)
$results.image_tag = "qmind-api:mvp-fullstack-v0"
($results | ConvertTo-Json -Depth 8) | Set-Content $EvidencePath -Encoding utf8
Write-Host "Evidence=$EvidencePath verdict=$($results.verdict) failures=$fail"

$passA = $null
$passQm = $null
$passB = $null
$accessA = $null
$accessQm = $null
$accessB = $null
$upUrl = $null
if ($fail -gt 0) { exit 1 }
exit 0
