<#
.SYNOPSIS
  Envia imagens locais do CMS para o S3 com os nomes referenciados no banco.

.EXAMPLE
  .\scripts\deploy\08-sync-cms-images-to-s3.ps1
  .\scripts\deploy\08-sync-cms-images-to-s3.ps1 -LocalDir C:\Projetos\PanelDX\LeAction_Sys_FE\public\images
#>
[CmdletBinding()]
param(
    [string]$LocalDir = (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'LeAction_Sys_FE\public\images'),
    [string]$Bucket = 'paneldx-cms-assets-2026',
    [string]$Prefix = 'cms',
    [string]$Region = 'us-east-2',
    [switch]$VerifySsl
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir '_common.ps1')

if (-not (Test-Path $LocalDir)) {
    throw "Diretorio local nao encontrado: $LocalDir"
}

# Nomes exatos no CMS de producao -> arquivo local (quando o upload acrescentou prefixo de timestamp)
$cmsAliases = @{
    '1782577918962-1781900286860-imagemherobanner_5.png' = '1781900286860-imagemherobanner_5.png'
    '1782577927708-1782151920197-1782151798013-mesainovacaobanner.png' = '1782151920197-1782151798013-mesainovacaobanner.png'
}

function Get-ImageContentType([string]$filePath) {
    switch ([System.IO.Path]::GetExtension($filePath).ToLowerInvariant()) {
        '.png' { return 'image/png' }
        '.jpg' { return 'image/jpeg' }
        '.jpeg' { return 'image/jpeg' }
        '.webp' { return 'image/webp' }
        '.gif' { return 'image/gif' }
        default { return 'application/octet-stream' }
    }
}

function Send-CmsImageToS3 {
    param(
        [Parameter(Mandatory)][string]$SourcePath,
        [Parameter(Mandatory)][string]$ObjectKey
    )
    $contentType = Get-ImageContentType $SourcePath
    $s3Uri = "s3://$Bucket/$ObjectKey"
    Invoke-DeployAws -VerifySsl:$VerifySsl s3 cp $SourcePath $s3Uri `
        --region $Region `
        --content-type $contentType `
        --cache-control 'public, max-age=31536000, immutable' | Out-Null
    Write-DeployOk "$ObjectKey"
}

Write-DeployStep "Sincronizando imagens CMS: $LocalDir -> s3://$Bucket/$Prefix/"

$uploaded = 0
$files = Get-ChildItem -Path $LocalDir -Recurse -File | Where-Object { $_.Name -ne '.gitkeep' }

foreach ($file in $files) {
    $relative = $file.FullName.Substring($LocalDir.Length).TrimStart('\', '/').Replace('\', '/')
    $objectKey = if ($Prefix) { "$Prefix/$relative" } else { $relative }
    Send-CmsImageToS3 -SourcePath $file.FullName -ObjectKey $objectKey
    $uploaded++
}

Write-DeployStep 'Publicando aliases com nomes exatos do CMS (producao)'
foreach ($targetName in $cmsAliases.Keys) {
    $sourceName = $cmsAliases[$targetName]
    $sourcePath = Join-Path $LocalDir $sourceName
    if (-not (Test-Path $sourcePath)) {
        Write-DeployWarn "Alias ignorado - origem ausente: $sourceName (destino $targetName)"
        continue
    }
    $objectKey = "$Prefix/$targetName"
    Send-CmsImageToS3 -SourcePath $sourcePath -ObjectKey $objectKey
    $uploaded++
}

Write-Host ''
Write-Host "Total de objetos enviados: $uploaded" -ForegroundColor Cyan
$sampleKey = "$Prefix/1782577918962-1781900286860-imagemherobanner_5.png"
Write-Host ('Verifique: https://{0}.s3.{1}.amazonaws.com/{2}' -f $Bucket, $Region, $sampleKey) -ForegroundColor DarkGray
