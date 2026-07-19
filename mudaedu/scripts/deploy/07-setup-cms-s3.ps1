<#
.SYNOPSIS
  Cria bucket S3 para imagens CMS do PanelDX (leitura publica no prefixo cms/).

.EXAMPLE
  .\scripts\deploy\07-setup-cms-s3.ps1
#>
[CmdletBinding()]
param(
    [string]$Bucket = 'paneldx-cms-assets-2026',
    [string]$Region = 'us-east-2',
    [string]$Prefix = 'cms',
    [switch]$VerifySsl
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir '_common.ps1')

Write-DeployStep "Configurando bucket CMS S3: $Bucket ($Region)"

$exists = $false
try {
    $null = Invoke-DeployAws -VerifySsl:$VerifySsl s3api head-bucket --bucket $Bucket --region $Region
    $exists = $true
    Write-DeployOk "Bucket ja existe: $Bucket"
} catch {
    Write-DeployWarn 'Bucket nao encontrado - criando...'
}

if (-not $exists) {
    if ($Region -eq 'us-east-1') {
        Invoke-DeployAws -VerifySsl:$VerifySsl s3api create-bucket --bucket $Bucket --region $Region | Out-Null
    } else {
        $cfg = "{`"LocationConstraint`":`"$Region`"}"
        Invoke-DeployAws -VerifySsl:$VerifySsl s3api create-bucket `
            --bucket $Bucket `
            --region $Region `
            --create-bucket-configuration $cfg | Out-Null
    }
    Write-DeployOk "Bucket criado: $Bucket"
}

Write-DeployStep 'Ajustando Block Public Access para bucket policy'
Invoke-DeployAws -VerifySsl:$VerifySsl s3api put-public-access-block `
    --bucket $Bucket `
    --public-access-block-configuration `
    'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false' | Out-Null
Write-DeployOk 'Public access block configurado'

Write-DeployStep 'Aplicando politica de leitura publica no prefixo cms/'
$policy = @{
    Version   = '2012-10-17'
    Statement = @(
        @{
            Sid       = 'PublicReadCmsAssets'
            Effect    = 'Allow'
            Principal = '*'
            Action    = 's3:GetObject'
            Resource  = "arn:aws:s3:::$Bucket/$Prefix/*"
        }
    )
} | ConvertTo-Json -Depth 5 -Compress

$policyFile = Join-Path $env:TEMP ("cms-bucket-policy-$Bucket.json")
[System.IO.File]::WriteAllText($policyFile, $policy, (New-Object System.Text.UTF8Encoding($false)))
try {
    Invoke-DeployAws -VerifySsl:$VerifySsl s3api put-bucket-policy `
        --bucket $Bucket `
        --policy ("file://" + $policyFile) | Out-Null
    Write-DeployOk "Politica publica aplicada em s3://$Bucket/$Prefix/*"
} finally {
    Remove-Item $policyFile -ErrorAction SilentlyContinue
}

$publicBase = "https://$Bucket.s3.$Region.amazonaws.com/$Prefix/"
Write-Host ''
Write-Host 'Bucket CMS pronto:' -ForegroundColor Cyan
Write-Host "  s3://$Bucket/$Prefix/" -ForegroundColor White
Write-Host "  $publicBase" -ForegroundColor DarkGray
