<#
.SYNOPSIS
  Cria EC2 Ubuntu + Elastic IP + registros Route53 (A) para chamelleon.com.br e HTTPS via Certbot.

.EXAMPLE
  .\scripts\deploy\01-provision-ec2.ps1
  .\scripts\deploy\01-provision-ec2.ps1 -Recreate
#>
[CmdletBinding()]
param(
    [switch]$Recreate
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../infra/aws/_config.ps1')

$cfg = $script:ChamelleonAws
$Region = $cfg.Region
$RepoRoot = Get-ChamelleonRepoRoot
$UserDataFile = Join-Path $RepoRoot 'infra/aws/user-data.sh'
$StateFile = Join-Path $RepoRoot 'infra/aws/state.json'

function Write-JsonFile([string]$Path, $Object) {
    $json = $Object | ConvertTo-Json -Depth 8 -Compress:$false
    [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
}

function Save-State($obj) {
    $obj | ConvertTo-Json -Depth 5 | Set-Content -Path $StateFile -Encoding UTF8
}

function Get-ExistingInstance {
    $json = aws ec2 describe-instances --region $Region `
        --filters "Name=tag:Name,Values=$($cfg.InstanceName)" `
                  "Name=instance-state-name,Values=running,pending,stopped,stopping" `
        --query "Reservations[0].Instances[0]" --output json 2>$null
    if ($json -and $json -ne 'null') { return $json | ConvertFrom-Json }
    return $null
}

Write-Host ""
Write-Host "==> Chamelleon - provision EC2 ($($cfg.Domain))" -ForegroundColor Cyan

$existing = Get-ExistingInstance
if ($existing -and -not $Recreate) {
    Write-Host "Instancia ja existe: $($existing.InstanceId) ($($existing.State.Name))" -ForegroundColor Yellow
    Write-Host "Use -Recreate para substituir ou rode 02-deploy-app.ps1 para publicar codigo."
    if (Test-Path $StateFile) { Get-Content $StateFile | Write-Host }
    exit 0
}

if ($existing -and $Recreate) {
    Write-Host "Encerrando instancia anterior $($existing.InstanceId)..." -ForegroundColor Yellow
    aws ec2 terminate-instances --region $Region --instance-ids $existing.InstanceId | Out-Null
    aws ec2 wait instance-terminated --region $Region --instance-ids $existing.InstanceId
}

$sgId = aws ec2 describe-security-groups --region $Region `
    --filters "Name=group-name,Values=$($cfg.SecurityGroupName)" `
    --query "SecurityGroups[0].GroupId" --output text 2>$null
if (-not $sgId -or $sgId -eq 'None') {
    Write-Host "Criando security group..." -ForegroundColor Green
    $sgId = aws ec2 create-security-group --region $Region `
        --group-name $cfg.SecurityGroupName `
        --description "Chamelleon web HTTP HTTPS SSH" `
        --vpc-id $cfg.VpcId `
        --query GroupId --output text
    aws ec2 authorize-security-group-ingress --region $Region --group-id $sgId --protocol tcp --port 22 --cidr 0.0.0.0/0 | Out-Null
    aws ec2 authorize-security-group-ingress --region $Region --group-id $sgId --protocol tcp --port 80 --cidr 0.0.0.0/0 | Out-Null
    aws ec2 authorize-security-group-ingress --region $Region --group-id $sgId --protocol tcp --port 443 --cidr 0.0.0.0/0 | Out-Null
}

$userDataRaw = Get-Content -Path $UserDataFile -Raw -Encoding UTF8
$userDataB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($userDataRaw))

$tagsArg = "ResourceType=instance,Tags=[{Key=Name,Value=$($cfg.InstanceName)},{Key=Project,Value=chamelleon}]"

Write-Host "Lancando EC2 ($($cfg.InstanceType))..." -ForegroundColor Green
$instanceId = aws ec2 run-instances --region $Region `
    --image-id $cfg.AmiId `
    --instance-type $cfg.InstanceType `
    --key-name $cfg.KeyName `
    --subnet-id $cfg.SubnetId `
    --security-group-ids $sgId `
    --associate-public-ip-address `
    --user-data $userDataB64 `
    --tag-specifications $tagsArg `
    --query "Instances[0].InstanceId" --output text

Write-Host "Aguardando instancia running ($instanceId)..." -ForegroundColor Yellow
aws ec2 wait instance-running --region $Region --instance-ids $instanceId

$eipAlloc = $null
$publicIp = $null
if (Test-Path $StateFile) {
    $prev = Get-Content $StateFile -Raw | ConvertFrom-Json
    if ($prev.allocation_id) {
        $assoc = aws ec2 describe-addresses --region $Region --allocation-ids $prev.allocation_id `
            --query "Addresses[0].AssociationId" --output text 2>$null
        if ($assoc -eq 'None' -or -not $assoc) {
            $eipAlloc = $prev.allocation_id
            $publicIp = $prev.public_ip
            Write-Host "Reutilizando Elastic IP existente: $publicIp" -ForegroundColor Yellow
        }
    }
}
if (-not $eipAlloc) {
    $eipAlloc = aws ec2 allocate-address --region $Region --domain vpc --query AllocationId --output text
    $publicIp = aws ec2 describe-addresses --region $Region --allocation-ids $eipAlloc --query "Addresses[0].PublicIp" --output text
    Write-Host "Elastic IP alocado: $eipAlloc ($publicIp)" -ForegroundColor Green
}
aws ec2 associate-address --region $Region --instance-id $instanceId --allocation-id $eipAlloc | Out-Null

$changeBatch = @{
    Changes = @(
        @{
            Action = 'UPSERT'
            ResourceRecordSet = @{
                Name = $cfg.Domain
                Type = 'A'
                TTL  = 300
                ResourceRecords = @(@{ Value = $publicIp })
            }
        },
        @{
            Action = 'UPSERT'
            ResourceRecordSet = @{
                Name = $cfg.WwwDomain
                Type = 'A'
                TTL  = 300
                ResourceRecords = @(@{ Value = $publicIp })
            }
        }
    )
} | ConvertTo-Json -Depth 6

$changeFile = Join-Path $env:TEMP "chamelleon-route53-$([Guid]::NewGuid().ToString('N')).json"
Write-JsonFile -Path $changeFile -Object $changeBatch
$changeUri = "file://$($changeFile -replace '\\', '/')"
aws route53 change-resource-record-sets --hosted-zone-id $cfg.HostedZoneId --change-batch $changeUri | Out-Null
Remove-Item $changeFile -Force -ErrorAction SilentlyContinue

$state = @{
    instance_id    = $instanceId
    allocation_id  = $eipAlloc
    public_ip      = $publicIp
    security_group = $sgId
    domain         = $cfg.Domain
    www_domain     = $cfg.WwwDomain
    region         = $Region
    key_name       = $cfg.KeyName
    created_at     = (Get-Date).ToString('o')
}
Save-State $state

Write-Host ""
Write-Host "==> Provisionamento concluido" -ForegroundColor Green
Write-Host "  Instance  : $instanceId"
Write-Host "  IP publico: $publicIp"
Write-Host "  HTTP      : http://$($cfg.Domain)"
Write-Host "  HTTPS     : https://$($cfg.Domain) (Certbot apos propagacao DNS, 5-15 min)"
Write-Host ""
Write-Host "  SSH:"
Write-Host "    ssh -i C:\Projetos\Chaves\paneldx-bastion-key.pem ubuntu@$publicIp"
Write-Host ""
Write-Host "  Proximo passo:"
Write-Host "    .\scripts\deploy\02-deploy-app.ps1"
Write-Host ""
Write-Host "  Credenciais DB no servidor:"
Write-Host "    sudo cat /var/log/chamelleon-bootstrap.log"
