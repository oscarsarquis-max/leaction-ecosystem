# Anexa no ALB do Inove: /ecossistema* /_next* /hub-api* → Hub EC2 :80
# TLS continua no ALB (certificado inove4us.com.br). O app ECS do professor não é alterado.
param(
    [string]$Region = 'us-east-2',
    [string]$AlbArn = 'arn:aws:elasticloadbalancing:us-east-2:253137917703:loadbalancer/app/inove4us-prod/249a5e418be394dc',
    [string]$HttpsListenerArn = 'arn:aws:elasticloadbalancing:us-east-2:253137917703:listener/app/inove4us-prod/249a5e418be394dc/5e692b2b401d1e2f',
    [string]$VpcId = 'vpc-017dc4cac16ba2c59',
    [string]$HubPrivateIp = '10.0.4.118',
    [string]$TgName = 'inove4us-prod-hub-eco'
)

$ErrorActionPreference = 'Stop'
$aws = 'C:\Program Files\Amazon\AWSCLIV2\aws.exe'

Write-Host '==> Target group'
$existing = & $aws elbv2 describe-target-groups --region $Region --names $TgName --query 'TargetGroups[0].TargetGroupArn' --output text 2>$null
if ($existing -and $existing -ne 'None') {
    $tgArn = $existing
    Write-Host "existe $tgArn"
} else {
    $tgArn = & $aws elbv2 create-target-group `
        --region $Region `
        --name $TgName `
        --protocol HTTP --port 80 --vpc-id $VpcId `
        --target-type ip `
        --health-check-protocol HTTP `
        --health-check-path /api/health `
        --health-check-interval-seconds 15 `
        --healthy-threshold-count 2 `
        --unhealthy-threshold-count 3 `
        --matcher 'HttpCode=200' `
        --query 'TargetGroups[0].TargetGroupArn' --output text
    Write-Host "criado $tgArn"
}

& $aws elbv2 register-targets --region $Region --target-group-arn $tgArn --targets "Id=$HubPrivateIp,Port=80" | Out-Null
Write-Host "target $HubPrivateIp:80 registrado"

$condFile = Join-Path $env:TEMP 'inove-eco-alb-conditions.json'
@'
[
  {
    "Field": "path-pattern",
    "PathPatternConfig": {
      "Values": ["/ecossistema", "/ecossistema/*", "/_next/*", "/hub-api/*"]
    }
  }
]
'@ | Set-Content -Path $condFile -Encoding ascii

Write-Host '==> Listener rule'
$ruleArn = & $aws elbv2 describe-rules --region $Region --listener-arn $HttpsListenerArn --query "Rules[?Priority=='10'].RuleArn | [0]" --output text
if ($ruleArn -and $ruleArn -ne 'None') {
    Write-Host "regra priority 10 já existe $ruleArn — atualizando"
    & $aws elbv2 modify-rule --region $Region --rule-arn $ruleArn `
        --conditions "file://$condFile" `
        --actions "Type=forward,TargetGroupArn=$tgArn" | Out-Null
} else {
    & $aws elbv2 create-rule --region $Region --listener-arn $HttpsListenerArn --priority 10 `
        --conditions "file://$condFile" `
        --actions "Type=forward,TargetGroupArn=$tgArn" | Out-Null
}

Write-Host 'OK ALB /ecossistema* → Hub'
