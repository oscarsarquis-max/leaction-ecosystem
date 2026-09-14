# HTTP A/B proof of the PRM_016 COR_001 isolated stack. Does not stop meeting listeners.
# Starts isolated ports if free; stops only the isolated ledger at the end.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_mvp-process-safety.ps1')
. (Join-Path $PSScriptRoot '_load-mvp-secrets.ps1')

$mockPort = 19095
$spiderPort = 19080
$bffPort = 19088
$fePort = 15178
$bff = "http://127.0.0.1:$bffPort"
$mock = "http://127.0.0.1:$mockPort"
$fe = "http://127.0.0.1:$fePort"
$ledgerPath = Get-MvpIsolatedCor016LedgerPath
$started = $false
$script:proof = 'COMPROVADO'

function Get-MeetingSnapshot {
  return [pscustomobject]@{
    mock = Get-MvpListenPid -Port 8095
    spider = Get-MvpListenPid -Port 8080
    bff = Get-MvpListenPid -Port 8088
    fe = Get-MvpListenPid -Port 5178
    pg = Get-MvpListenPid -Port 5437
  }
}

function Assert-MeetingUnchanged($Before, $After, [string]$When) {
  foreach ($role in @('mock', 'spider', 'bff', 'fe', 'pg')) {
    if ($Before.$role -ne $After.$role) {
      throw "Meeting listener $role changed during isolated proof ($When): $($Before.$role) -> $($After.$role)"
    }
  }
}

function New-JourneyHeaders([string]$Key) {
  return @{
    'X-Correlation-ID' = [guid]::NewGuid().ToString()
    'Idempotency-Key' = $Key
  }
}

function Invoke-Journey([string]$Key, [string]$Body) {
  return Invoke-RestMethod "$bff/api/v1/public/demo/protection-journeys" -Method POST -Headers (New-JourneyHeaders $Key) -ContentType 'application/json' -Body $Body
}

function Invoke-JourneyStatus([string]$Key, [string]$Body) {
  try {
    Invoke-WebRequest "$bff/api/v1/public/demo/protection-journeys" -Method POST -Headers (New-JourneyHeaders $Key) -ContentType 'application/json' -Body $Body -UseBasicParsing | Out-Null
    return 200
  } catch {
    if ($_.Exception.Response) {
      return [int]$_.Exception.Response.StatusCode.value__
    }
    throw
  }
}

function Invoke-Resolve([string]$Url) {
  try {
    return Invoke-RestMethod "$bff/api/v1/public/demo/context-sources/resolve" -Method POST -ContentType 'application/json' -Body (@{ url = $Url } | ConvertTo-Json)
  } catch {
    if ($_.Exception.Response) {
      return [pscustomobject]@{ statusCode = [int]$_.Exception.Response.StatusCode.value__; error = $true }
    }
    throw
  }
}

$before = Get-MeetingSnapshot
Write-Output ("meetingBefore mock=$($before.mock) spider=$($before.spider) bff=$($before.bff) fe=$($before.fe) pg=$($before.pg)")

try {
  & (Join-Path $PSScriptRoot 'start-isolated-cor016.ps1')
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "start-isolated-cor016.ps1 exited $LASTEXITCODE"
  }
  $started = $true

  $info = Invoke-RestMethod "$bff/api/v1/system/info"
  Write-Output ("isolatedIdentity applicationId=$($info.applicationId) version=$($info.version) operationalState=$($info.operationalState)")
  $feStatus = (Invoke-WebRequest "$fe/demonstracao/mvp-integrado" -UseBasicParsing).StatusCode
  Write-Output "isolatedFrontendHttp=$feStatus (not visual proof)"

  $familyUrl = "http://127.0.0.1:$fePort/demonstracao/fontes/continuidade-familiar"
  $incomeUrl = "http://127.0.0.1:$fePort/demonstracao/fontes/interrupcao-renda"
  $revokedUrl = "http://127.0.0.1:$fePort/demonstracao/fontes/revogada"

  $familyKey = [guid]::NewGuid().ToString()
  $family = Invoke-Journey $familyKey ('{"declaredObjective":"UNDERSTAND_PROTECTION_OPTIONS","sourceUrl":"' + $familyUrl + '","intentionConfirmed":"true"}')
  Write-Output ("familyUrl status=$($family.status) id=$($family.id) scenarioKey=$($family.scenarioKey) capabilityId=$($family.capabilityId) providerRequestId=$($family.providerRequestId) mockResultId=$($family.mockResultId) decisionId=$($family.spiderDecisionId) item0=$($family.items[0].code)")
  if ($family.status -ne 'PRE_PROPOSAL_AVAILABLE' -or -not $family.mockResultId) { throw 'family URL journey was not READY' }

  $incomeKey = [guid]::NewGuid().ToString()
  $income = Invoke-Journey $incomeKey '{"declaredObjective":"COMPARE_COVERAGE_GAPS","declaredContext":"interrupção de renda se o trabalho parar","intentionConfirmed":"true"}'
  Write-Output ("writtenRelato status=$($income.status) id=$($income.id) scenarioKey=$($income.scenarioKey) capabilityId=$($income.capabilityId) providerRequestId=$($income.providerRequestId) mockResultId=$($income.mockResultId) item0=$($income.items[0].code)")
  if ($income.status -ne 'PRE_PROPOSAL_AVAILABLE') { throw 'written income journey was not READY' }
  if ($family.scenarioKey -eq $income.scenarioKey) { throw 'A/B scenarioKey was not distinct' }
  if ($family.items[0].code -eq $income.items[0].code) { throw 'A/B possibility codes were not distinct' }

  $health = Invoke-RestMethod "$mock/health"
  $keys = @($health.recentExecutions | ForEach-Object { $_.scenarioKey })
  Write-Output ("providerRecentKeys=" + ($keys -join ','))
  $unique = @($keys | Select-Object -Unique)
  Write-Output ("providerUniqueKeyCount=" + $unique.Count)
  if ($unique.Count -lt 2) { throw 'provider did not receive two distinct scenario keys' }

  $rejected = Invoke-Journey ([guid]::NewGuid().ToString()) '{"declaredObjective":"REQUEST_BINDING_QUOTE","declaredContext":"continuidade familiar","intentionConfirmed":"true"}'
  Write-Output ("rejected status=$($rejected.status) mockCalled=$($rejected.mockCalled) capabilityId=$($rejected.capabilityId) itemCount=$($rejected.items.Count)")
  if ($rejected.status -ne 'REJECTED' -or $rejected.mockCalled -eq $true) { throw 'rejected intention called provider or was not REJECTED' }

  $empty = Invoke-Journey ([guid]::NewGuid().ToString()) '{"declaredObjective":"UNDERSTAND_PROTECTION_OPTIONS"}'
  Write-Output ("emptyContext status=$($empty.status) spiderDecisionId=$($empty.spiderDecisionId) mockCalled=$($empty.mockCalled) itemCount=$($empty.items.Count)")
  if ($empty.status -ne 'MISSING_CONTEXT' -or $empty.spiderDecisionId) { throw 'empty context was not blocked before Spider' }

  $insufficient = Invoke-Journey ([guid]::NewGuid().ToString()) '{"declaredObjective":"UNDERSTAND_PROTECTION_OPTIONS","declaredContext":"asdf","intentionConfirmed":"true"}'
  Write-Output ("insufficient status=$($insufficient.status) spiderDecisionId=$($insufficient.spiderDecisionId)")
  if ($insufficient.status -ne 'MISSING_CONTEXT' -or $insufficient.spiderDecisionId) { throw 'insufficient context called Spider' }

  $conflict = Invoke-Journey ([guid]::NewGuid().ToString()) ('{"declaredObjective":"UNDERSTAND_PROTECTION_OPTIONS","sourceUrl":"' + $familyUrl + '","declaredContext":"interrupção de renda","intentionConfirmed":"true"}')
  Write-Output ("conflict status=$($conflict.status) spiderDecisionId=$($conflict.spiderDecisionId)")
  if ($conflict.status -ne 'AMBIGUOUS' -or $conflict.spiderDecisionId) { throw 'conflict was not blocked before Spider' }

  $invalid = Invoke-JourneyStatus ([guid]::NewGuid().ToString()) '{"declaredObjective":"UNDERSTAND_PROTECTION_OPTIONS","sourceUrl":"http://169.254.169.254/latest/meta-data","intentionConfirmed":"true"}'
  Write-Output "invalidUrl status=$invalid"
  if ($invalid -ne 400) { throw 'invalid URL was not 400' }

  $revokedResolve = Invoke-Resolve $revokedUrl
  Write-Output ("revokedResolve error=$($revokedResolve.error) statusCode=$($revokedResolve.statusCode)")
  if (-not $revokedResolve.error -or $revokedResolve.statusCode -ne 409) { throw 'revoked URL did not return 409' }

  $replayKey = [guid]::NewGuid().ToString()
  $replayBody = '{"declaredObjective":"UNDERSTAND_PROTECTION_OPTIONS","declaredContext":"continuidade familiar com dependentes","intentionConfirmed":"true"}'
  $firstReplay = Invoke-Journey $replayKey $replayBody
  $secondReplay = Invoke-Journey $replayKey $replayBody
  Write-Output ("identicalReplay sameId=" + ($firstReplay.id -eq $secondReplay.id) + " id=$($firstReplay.id)")
  if ($firstReplay.id -ne $secondReplay.id) { throw 'identical canonical replay did not return the same id' }

  $conflict409 = Invoke-JourneyStatus $replayKey '{"declaredObjective":"UNDERSTAND_PROTECTION_OPTIONS","declaredContext":"interrupção de renda se o trabalho parar","intentionConfirmed":"true"}'
  Write-Output "contextChange status=$conflict409"
  if ($conflict409 -ne 409) { throw 'material context change did not return 409' }

  $ledger = Read-MvpOwnedLedger -Path $ledgerPath
  $mockTarget = @($ledger.targets | Where-Object { $_.role -eq 'mock' })[0]
  $startedAfter = Convert-MvpLedgerDate ([string]$mockTarget.startedAfterUtc)
  Stop-MvpOwnedProcess -ProcessId ([int]$mockTarget.listenerPid) -ExpectedPort $mockPort -ExpectedName 'node.exe' -CommandLineMustContain ([string]$mockTarget.marker) -StartedAfter $startedAfter
  Write-Output "isolatedMockStopped=$($mockTarget.listenerPid)"
  Start-Sleep -Seconds 2
  $down = Invoke-Journey ([guid]::NewGuid().ToString()) '{"declaredObjective":"UNDERSTAND_PROTECTION_OPTIONS","declaredContext":"continuidade familiar","intentionConfirmed":"true"}'
  Write-Output ("providerDown status=$($down.status) mockCalled=$($down.mockCalled) mockResultId=$($down.mockResultId) itemCount=$($down.items.Count) decisionId=$($down.spiderDecisionId)")
  if ($down.items.Count -gt 0) { throw 'provider-down response leaked possibilities' }
  if ($down.status -eq 'PRE_PROPOSAL_AVAILABLE') { throw 'provider-down still returned READY' }

  $after = Get-MeetingSnapshot
  Write-Output ("meetingAfter mock=$($after.mock) spider=$($after.spider) bff=$($after.bff) fe=$($after.fe) pg=$($after.pg)")
  Assert-MeetingUnchanged $before $after 'after HTTP'
  Write-Output "isolatedHttpProof=COMPROVADO"
} catch {
  $script:proof = 'NÃO COMPROVADO'
  Write-Output "isolatedHttpProof=NÃO COMPROVADO"
  Write-Output ("isolatedHttpReason=" + $_.Exception.Message)
} finally {
  if (Test-Path -LiteralPath $ledgerPath) {
    Write-Output '--- stopping isolated ledger only ---'
    & (Join-Path $PSScriptRoot 'stop-mvp-demo.ps1') -LedgerPath $ledgerPath
  }
  $final = Get-MeetingSnapshot
  Write-Output ("meetingFinal mock=$($final.mock) spider=$($final.spider) bff=$($final.bff) fe=$($final.fe) pg=$($final.pg)")
  try {
    Assert-MeetingUnchanged $before $final 'after isolated stop'
    Write-Output 'meetingStackUntouched=true'
  } catch {
    Write-Output 'meetingStackUntouched=false'
    Write-Output $_.Exception.Message
    $script:proof = 'NÃO COMPROVADO'
  }
}

Write-Output "visualBrowser=NÃO COMPROVADO"
Write-Output "dictationBrowser=NÃO COMPROVADO"
if ($script:proof -ne 'COMPROVADO') {
  exit 1
}
