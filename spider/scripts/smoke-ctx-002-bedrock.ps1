#Requires -Version 5.1
<#
.SYNOPSIS
  Smoke opcional CTX-002 contra AWS Bedrock já configurado no backend local.

.DESCRIPTION
  Requer backend iniciado com local-demo, SPIDER_CONTEXT_AI_ENABLED=true e provider bedrock.
  Usa a cadeia padrão de credenciais AWS do SDK. Não imprime credenciais nem o prompt.
#>
[CmdletBinding()]
param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8080",
  [string]$CredentialRef = "local-demo-console"
)

$ErrorActionPreference = "Stop"
$headers = @{ "X-Spider-Credential-Ref" = $CredentialRef }

$catalog = Invoke-RestMethod -Uri "$ApiBaseUrl/v1/context/intents" -Headers $headers
if ($catalog.aiState -ne "ACTIVE" -or $catalog.aiProvider -ne "aws-bedrock-anthropic") {
  throw "Backend não está com o provider AWS Bedrock ativo."
}

$body = @{
  objective = "Verifique a proposta 12345 porque o crédito ainda não foi liberado."
} | ConvertTo-Json

$watch = [System.Diagnostics.Stopwatch]::StartNew()
$result = Invoke-RestMethod `
  -Method Post `
  -Uri "$ApiBaseUrl/v1/context/interpretations" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
$watch.Stop()

if ($result.status -ne "SUCCEEDED") {
  throw "Smoke Bedrock falhou fechado com status $($result.status)."
}

[pscustomobject]@{
  provider = $result.interpretation.provider
  model = $result.interpretation.model
  elapsedMs = $watch.ElapsedMilliseconds
  providerLatencyMs = $result.interpretation.latencyMs
  inputTokens = $result.interpretation.usage.inputTokens
  outputTokens = $result.interpretation.usage.outputTokens
  totalTokens = $result.interpretation.usage.totalTokens
  intent = $result.decision.intentContract.intent
  route = $result.decision.route.routeRef
  executionStarted = [bool]$result.decision.executionId
} | ConvertTo-Json
