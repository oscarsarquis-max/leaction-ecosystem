#Requires -Version 5.1
# Public AF-NAT → Spider → Hub list for Loja PRODUCTION. Does not print secrets.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$region = "us-east-2"
$cluster = "actionfinance-cluster"
$runtimeArn = aws secretsmanager describe-secret --region $region --secret-id actionfinance/runtime --query ARN --output text
$policyDoc = (@{
  Version = "2012-10-17"
  Statement = @(@{
    Effect = "Allow"
    Action = @("secretsmanager:GetSecretValue")
    Resource = @($runtimeArn)
  })
} | ConvertTo-Json -Depth 6)
$policyFile = Join-Path $env:TEMP "af-inc002-proof-policy.json"
[System.IO.File]::WriteAllText($policyFile, $policyDoc)
aws iam put-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-inc002-proof-once --policy-document "file://$policyFile" | Out-Null
Remove-Item -LiteralPath $policyFile -Force

$py = @'
import json, os, urllib.request, urllib.error
from datetime import datetime, timezone
secret = os.environ.get("ACTIONFINANCE_SPIDER_SECRET", "")
now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
company = "624023a4-57e3-415c-b7d0-925ca1acd3b7"
corr = "afp-inc002-proof-1"
body = {
  "contractVersion": "1.4",
  "messageId": "afm-inc002-proof-1",
  "correlationId": corr,
  "satelliteId": "actionfinance",
  "satelliteRole": "EXPERIENCE",
  "interactionType": "QUERY_STATUS",
  "createdAt": now,
  "idempotencyKey": "inc002-proof-list-1",
  "purpose": "FINANCIAL_EXTERNAL_LIST",
  "objective": {"text": "LIST_EXTERNAL_PAYMENTS", "origin": "SATELLITE_GOVERNED", "declaredAt": now},
  "dataClassification": "INTERNAL",
  "responseChannel": "SYNC",
  "context": {"snapshot": {
    "schemaVersion": "1.4", "classification": "INTERNAL", "nonPersonal": True,
    "provenance": {"sourceType": "SATELLITE_GOVERNED", "sourceId": "ACTIONFINANCE_FINANCIAL_LIST_V1",
      "sourceTimestamp": now, "captureMethod": "SERVER_REGISTRY", "trustLevel": "GOVERNED"},
    "selectedContribution": "GOVERNED_SOURCE",
    "contributions": [{"role": "GOVERNED_SOURCE", "sourceType": "SATELLITE_GOVERNED",
      "sourceId": "ACTIONFINANCE_FINANCIAL_LIST_V1", "sourceTimestamp": now,
      "captureMethod": "SERVER_REGISTRY", "trustLevel": "GOVERNED", "used": True,
      "elements": {"theme": "payment_list"}}],
    "attributes": {"channel": "ACTIONFINANCE_HOMOLOG", "purposeVersion": "financial-list-v1",
      "theme": "payment_list", "situation": "test_payment_list", "need": "list_external_payments",
      "horizon": "days", "companyId": company}
  }},
  "extensions": {"financialList": {"companyId": company, "originSystem": "ACTIONHUB_PAY",
    "environment": "PRODUCTION", "limit": 50}}
}
req = urllib.request.Request(
  "https://api.spider.actionhub.com.br/v1/satellites/interactions",
  data=json.dumps(body).encode(),
  headers={
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-Spider-Satellite-Id": "actionfinance",
    "X-Spider-Satellite-Secret": secret,
    "X-Correlation-ID": corr,
  },
  method="POST",
)
try:
  with urllib.request.urlopen(req, timeout=25) as resp:
    payload = json.loads(resp.read().decode())
    print("http=" + str(resp.status))
    print("status=" + str(payload.get("status")))
    print("capability=" + str(payload.get("capabilityId")))
    summary = payload.get("resultSummary") or {}
    print("itemCount=" + str(summary.get("itemCount")))
    print("reviewCount=" + str(summary.get("reviewCount") if summary.get("reviewCount") is not None else len(summary.get("reviews") or [])))
    print("environment=" + str(summary.get("environment")))
    print("errorCode=" + str(payload.get("errorCode")))
except urllib.error.HTTPError as err:
  raw = err.read().decode("utf-8", "replace")[:400]
  print("http=" + str(err.code))
  try:
    parsed = json.loads(raw)
    print("errorCode=" + str(parsed.get("errorCode")))
    print("message=" + str(parsed.get("message")))
  except Exception:
    print("body_prefix=" + raw[:160])
'@
$py = $py.Replace("`r`n", "`n")
$cmd = "python - <<'PY'`n$py`nPY"

$td = @{
  family = "actionfinance-dbadmin"
  networkMode = "awsvpc"
  requiresCompatibilities = @("FARGATE")
  cpu = "256"
  memory = "512"
  executionRoleArn = "arn:aws:iam::253137917703:role/actionfinance-migrate-execution"
  runtimePlatform = @{ operatingSystemFamily = "LINUX"; cpuArchitecture = "X86_64" }
  containerDefinitions = @(@{
    name = "dbadmin"
    image = "public.ecr.aws/docker/library/python:3.12-alpine"
    essential = $true
    secrets = @(
      @{ name = "ACTIONFINANCE_SPIDER_SECRET"; valueFrom = "${runtimeArn}:spider_secret::" }
    )
    command = @("sh", "-lc", $cmd)
    logConfiguration = @{
      logDriver = "awslogs"
      options = @{
        "awslogs-group" = "/actionfinance/migrate"
        "awslogs-region" = $region
        "awslogs-stream-prefix" = "inc002p"
      }
    }
  })
}
$tdFile = Join-Path $env:TEMP "af-inc002-proof-td.json"
[System.IO.File]::WriteAllText($tdFile, ($td | ConvertTo-Json -Depth 8))
try {
  aws ecs register-task-definition --region $region --cli-input-json "file://$tdFile" --query "taskDefinition.taskDefinitionArn" --output text | Out-Null
  $net = "awsvpcConfiguration={subnets=[subnet-0a1da7a0765588962,subnet-0693afdb3330b683a],securityGroups=[sg-02d2aacb3b77e4a41],assignPublicIp=DISABLED}"
  $taskArn = aws ecs run-task --region $region --cluster $cluster --task-definition actionfinance-dbadmin --launch-type FARGATE --network-configuration $net --query "tasks[0].taskArn" --output text
  if (-not $taskArn -or $taskArn -eq "None") { throw "proof run-task failed" }
  aws ecs wait tasks-stopped --region $region --cluster $cluster --tasks $taskArn
  $exit = aws ecs describe-tasks --region $region --cluster $cluster --tasks $taskArn --query "tasks[0].containers[0].exitCode" --output text
  $taskId = ($taskArn -split "/")[-1]
  Write-Host "proof_exit=$exit"
  aws logs get-log-events --region $region --log-group-name /actionfinance/migrate --log-stream-name "inc002p/dbadmin/$taskId" --limit 40 --query "events[].message" --output text
  if ($exit -ne "0") { throw "proof failed with exit $exit" }
} finally {
  aws iam delete-role-policy --role-name actionfinance-migrate-execution --policy-name actionfinance-inc002-proof-once | Out-Null
}
