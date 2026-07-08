<#
.SYNOPSIS
  Abre portas 80/443 no action_hub_sg e 5432 do RDS para o EC2 do Hub.
#>
[CmdletBinding()]
param(
    [string]$Region = 'us-east-2',
    [string]$ActionHubSg = 'sg-08a0721444e6176b3',
    [string]$RdsSg = 'sg-07bfd4f6c938cd47a'
)

$ErrorActionPreference = 'Stop'
$ssl = @('--no-verify-ssl')

function Add-IngressRule {
    param([string]$GroupId, [int]$Port, [string]$Description, [string]$Cidr = '0.0.0.0/0')
    aws ec2 authorize-security-group-ingress @ssl --region $Region `
        --group-id $GroupId --protocol tcp --port $Port --cidr $Cidr 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $GroupId port $Port ($Description)" -ForegroundColor Green
    }
    elseif ($LASTEXITCODE -eq 254) {
        Write-Host "[--] $GroupId port $Port ja existe" -ForegroundColor DarkGray
    }
    else {
        aws ec2 authorize-security-group-ingress @ssl --region $Region `
            --group-id $GroupId --protocol tcp --port $Port --cidr $Cidr 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Falha ao abrir porta $Port em $GroupId" }
    }
}

function Add-SgRule {
    param([string]$GroupId, [int]$Port, [string]$SourceSg, [string]$Description)
    aws ec2 authorize-security-group-ingress @ssl --region $Region `
        --group-id $GroupId --protocol tcp --port $Port --source-group $SourceSg 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $GroupId port $Port from $SourceSg" -ForegroundColor Green
    }
    else {
        $out = aws ec2 authorize-security-group-ingress @ssl --region $Region `
            --group-id $GroupId --protocol tcp --port $Port --source-group $SourceSg 2>&1
        if ($out -match 'InvalidPermission.Duplicate') {
            Write-Host "[--] regra SG ja existe" -ForegroundColor DarkGray
        }
        else {
            Write-Host $out
            throw "Falha regra SG $GroupId"
        }
    }
}

Write-Host ""
Write-Host "==> Security Groups Action Hub" -ForegroundColor Cyan
Add-IngressRule -GroupId $ActionHubSg -Port 80 -Description 'HTTP'
Add-IngressRule -GroupId $ActionHubSg -Port 443 -Description 'HTTPS'
Add-SgRule -GroupId $RdsSg -Port 5432 -SourceSg $ActionHubSg -Description 'Hub to RDS'
Write-Host ""
Write-Host "==> Portas configuradas." -ForegroundColor Green
