# Real HTTP evidence across mock, Spider and SegSense via Satellite Contract V1.
# Does not print secret values. SegSense is not called through the deprecated demo slice.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_load-mvp-secrets.ps1')
. (Join-Path $PSScriptRoot '_mvp-preflight.ps1')

Invoke-MvpPreflight

function New-CanonicalBody($Objective, $Channel, $Correlation, $Key) {
  @{
    contractVersion = '1.0'
    messageId = 'msg-' + [guid]::NewGuid().ToString()
    correlationId = $Correlation
    satelliteId = 'segsense'
    satelliteRole = 'EXPERIENCE'
    interactionType = 'REQUEST_DECISION'
    createdAt = '2026-09-13T12:00:00Z'
    idempotencyKey = $Key
    purpose = 'INSURANCE_PROTECTION_ASSESSMENT'
    objective = @{
      text = $Objective
      origin = 'SATELLITE_GOVERNED'
      declaredAt = '2026-09-13T12:00:00Z'
    }
    context = @{
      snapshot = @{
        schemaVersion = '1.0'
        classification = 'INTERNAL'
        nonPersonal = $true
        provenance = @{
          sourceType = 'SATELLITE_GOVERNED'
          sourceId = 'SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1'
          sourceTimestamp = '2026-09-13T12:00:00Z'
          captureMethod = 'SERVER_REGISTRY'
          trustLevel = 'GOVERNED'
        }
        attributes = @{
          channel = $Channel
          editorialPieceVersion = 'demo-editorial-v1'
          purposeVersion = 'demo-purpose-v1'
        }
      }
    }
    dataClassification = 'INTERNAL'
    responseChannel = 'SYNC'
    metadata = @{}
  } | ConvertTo-Json -Depth 8
}

function Invoke-Canonical($Headers, $Body) {
  Invoke-RestMethod http://127.0.0.1:8080/v1/satellites/interactions -Method POST -Headers $Headers -ContentType 'application/json' -Body $Body
}

$secret = $env:SPIDER_SEGSENSE_DEMO_APPLICATION_SECRET
$corr = [guid]::NewGuid().ToString()
$key = [guid]::NewGuid().ToString()

Write-Output '--- canonical without identity (expect 401) ---'
try {
  Invoke-WebRequest http://127.0.0.1:8080/v1/satellites/interactions -Method POST -ContentType 'application/json' -Body '{}' -UseBasicParsing | Out-Null
} catch { Write-Output $_.Exception.Response.StatusCode.value__ }

Write-Output '--- canonical identity without secret (expect 401) ---'
try {
  $h = @{ 'X-Spider-Satellite-Id' = 'segsense'; 'X-Correlation-ID' = [guid]::NewGuid().ToString(); 'Idempotency-Key' = [guid]::NewGuid().ToString() }
  Invoke-WebRequest http://127.0.0.1:8080/v1/satellites/interactions -Method POST -Headers $h -ContentType 'application/json' -Body (New-CanonicalBody 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS' 'SEGSENSE_PUBLIC_DEMO' $h['X-Correlation-ID'] $h['Idempotency-Key']) -UseBasicParsing | Out-Null
} catch { Write-Output $_.Exception.Response.StatusCode.value__ }

Write-Output '--- canonical wrong satellite (expect 401) ---'
try {
  $h = @{ 'X-Spider-Satellite-Id' = 'unknown'; 'X-Spider-Satellite-Secret' = $secret; 'X-Correlation-ID' = [guid]::NewGuid().ToString(); 'Idempotency-Key' = [guid]::NewGuid().ToString() }
  Invoke-WebRequest http://127.0.0.1:8080/v1/satellites/interactions -Method POST -Headers $h -ContentType 'application/json' -Body (New-CanonicalBody 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS' 'SEGSENSE_PUBLIC_DEMO' $h['X-Correlation-ID'] $h['Idempotency-Key']) -UseBasicParsing | Out-Null
} catch { Write-Output $_.Exception.Response.StatusCode.value__ }

Write-Output '--- canonical wrong secret (expect 401) ---'
try {
  $h = @{ 'X-Spider-Satellite-Id' = 'segsense'; 'X-Spider-Satellite-Secret' = 'wrong'; 'X-Correlation-ID' = [guid]::NewGuid().ToString(); 'Idempotency-Key' = [guid]::NewGuid().ToString() }
  Invoke-WebRequest http://127.0.0.1:8080/v1/satellites/interactions -Method POST -Headers $h -ContentType 'application/json' -Body (New-CanonicalBody 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS' 'SEGSENSE_PUBLIC_DEMO' $h['X-Correlation-ID'] $h['Idempotency-Key']) -UseBasicParsing | Out-Null
} catch { Write-Output $_.Exception.Response.StatusCode.value__ }

Write-Output '--- canonical missing context (expect 400, before mock) ---'
try {
  $h = @{ 'X-Spider-Satellite-Id' = 'segsense'; 'X-Spider-Satellite-Secret' = $secret; 'X-Correlation-ID' = [guid]::NewGuid().ToString(); 'Idempotency-Key' = [guid]::NewGuid().ToString() }
  $body = '{"contractVersion":"1.0","messageId":"msg-missing-context","correlationId":"' + $h['X-Correlation-ID'] + '","satelliteId":"segsense","satelliteRole":"EXPERIENCE","interactionType":"REQUEST_DECISION","createdAt":"2026-09-13T12:00:00Z","idempotencyKey":"' + $h['Idempotency-Key'] + '","purpose":"INSURANCE_PROTECTION_ASSESSMENT"}'
  Invoke-WebRequest http://127.0.0.1:8080/v1/satellites/interactions -Method POST -Headers $h -ContentType 'application/json' -Body $body -UseBasicParsing | Out-Null
} catch { Write-Output $_.Exception.Response.StatusCode.value__ }

Write-Output '--- canonical happy path ---'
$okHeaders = @{
  'X-Spider-Satellite-Id' = 'segsense'
  'X-Spider-Satellite-Secret' = $secret
  'X-Correlation-ID' = $corr
  'Idempotency-Key' = $key
}
$okBody = New-CanonicalBody 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS' 'SEGSENSE_PUBLIC_DEMO' $corr $key
$sat = Invoke-Canonical $okHeaders $okBody
Write-Output ('canonicalStatus=' + $sat.status + ' contractVersion=' + $sat.contractVersion + ' decisionId=' + $sat.decisionId + ' sourceType=' + $sat.originProvenance.sourceType + ' channel=' + $sat.originProvenance.attributes.channel + ' capabilityId=' + $sat.capabilityId + ' providerRequestId=' + $sat.providerRequestId + ' providerReference=' + $sat.resultSummary.providerReference)
Write-Output ('canonicalExplanation=' + $sat.explanation)
if ($sat.explanation -match 'compreendeu|interpretou|personalizou') {
  throw 'READY explanation still claims semantic understanding.'
}
if ($sat.explanation -notmatch 'validou o contexto e o objetivo sintéticos permitidos') {
  throw 'READY explanation is not the deterministic Spider copy.'
}

Write-Output '--- segsense public journey (BFF uses canonical) ---'
$uiHeaders = @{
  'X-Correlation-ID' = [guid]::NewGuid().ToString()
  'Idempotency-Key' = [guid]::NewGuid().ToString()
}
$ui = Invoke-RestMethod http://127.0.0.1:8088/api/v1/public/demo/protection-journeys -Method POST -Headers $uiHeaders -ContentType 'application/json' -Body '{"declaredObjective":"UNDERSTAND_FAMILY_PROTECTION_OPTIONS"}'
Write-Output ('id=' + $ui.id + ' status=' + $ui.status + ' spiderDecisionId=' + $ui.spiderDecisionId + ' mockResultId=' + $ui.mockResultId + ' origin=' + $ui.originProvenance.channel + ' capabilityId=' + $ui.capabilityId + ' contractVersion=' + $ui.satelliteContractVersion)
Write-Output ('bffExplanation=' + $ui.explanation)
if ($ui.explanation -notmatch 'validou o contexto e o objetivo sintéticos permitidos') {
  throw 'BFF explanation was not the Spider deterministic copy.'
}
if ($ui.explanation -match 'compreendeu|interpretou|personalizou') {
  throw 'BFF explanation still claims semantic understanding.'
}

Write-Output '--- rejected objective (mock must not be required) ---'
$rejectHeaders = @{
  'X-Spider-Satellite-Id' = 'segsense'
  'X-Spider-Satellite-Secret' = $secret
  'X-Correlation-ID' = [guid]::NewGuid().ToString()
  'Idempotency-Key' = [guid]::NewGuid().ToString()
}
$rejected = Invoke-Canonical $rejectHeaders (New-CanonicalBody 'REQUEST_BINDING_QUOTE' 'SEGSENSE_PUBLIC_DEMO' $rejectHeaders['X-Correlation-ID'] $rejectHeaders['Idempotency-Key'])
Write-Output ('status=' + $rejected.status + ' capabilityId=' + $rejected.capabilityId + ' providerReference=' + $rejected.resultSummary.providerReference)
Write-Output ('rejectedExplanation=' + $rejected.explanation)
if ($rejected.explanation -match 'compreendeu|interpretou|personalizou') {
  throw 'REJECTED explanation still claims semantic understanding.'
}
if ($rejected.explanation -notmatch 'lista permitida') {
  throw 'REJECTED explanation is not the allowlist copy.'
}

Write-Output '--- retry same canonical idempotency key ---'
$again = Invoke-Canonical $okHeaders $okBody
Write-Output ('sameDecision=' + ($again.decisionId -eq $sat.decisionId))

Write-Output '--- same key different context (expect 409) ---'
try {
  Invoke-WebRequest http://127.0.0.1:8080/v1/satellites/interactions -Method POST -Headers $okHeaders -ContentType 'application/json' -Body (New-CanonicalBody 'UNDERSTAND_FAMILY_PROTECTION_OPTIONS' 'OTHER_CHANNEL' $corr $key) -UseBasicParsing | Out-Null
} catch { Write-Output $_.Exception.Response.StatusCode.value__ }

Write-Output '--- mock provider contract without credential (expect 401) ---'
try {
  Invoke-WebRequest http://127.0.0.1:8095/v1/provider/capabilities/BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO/executions -Method POST -ContentType 'application/json' -Body '{}' -UseBasicParsing | Out-Null
} catch { Write-Output $_.Exception.Response.StatusCode.value__ }

Write-Output '--- provider unavailable via isolated Spider (meeting stack must stay up) ---'
try {
  & (Join-Path $PSScriptRoot 'prove-provider-unavailable-isolated.ps1')
} catch {
  Write-Output 'providerUnavailableProof=NÃO COMPROVADO'
  Write-Output ('providerUnavailableReason=' + $_.Exception.Message)
}

Write-Output '--- logs must not contain secret material ---'
$logDir = Join-Path $PSScriptRoot '.mvp-logs'
$secretNames = @(
  $env:SPIDER_SEGSENSE_DEMO_APPLICATION_SECRET,
  $env:SEGSENSE_SPIDER_DEMO_APPLICATION_SECRET,
  $env:SEGSENSE_MOCK_CREDENTIAL,
  $env:SPIDER_SEGSENSE_MOCK_CREDENTIAL
)
$leaked = $false
Get-ChildItem $logDir -Filter '*.log' -ErrorAction SilentlyContinue | ForEach-Object {
  foreach ($value in $secretNames) {
    if (-not [string]::IsNullOrWhiteSpace($value) -and (Select-String -Path $_.FullName -SimpleMatch -Pattern $value -Quiet)) {
      $leaked = $true
    }
  }
}
if ($leaked) { throw 'Secret material found in MVP logs.' }
Write-Output 'log-secret-scan=ok'
Write-Output 'canonical-endpoint=POST /v1/satellites/interactions'
Write-Output 'deprecated-demo-slice=not-called-by-segsense'
