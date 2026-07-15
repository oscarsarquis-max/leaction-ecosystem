# Build + push da imagem inove4us para o ECR
param(
  [Parameter(Mandatory = $true)][string]$AwsRegion,
  [Parameter(Mandatory = $true)][string]$AccountId,
  [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Repo = "inove4us"
$Uri = "$AccountId.dkr.ecr.$AwsRegion.amazonaws.com/$Repo"

Write-Host "==> Login ECR"
aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$AwsRegion.amazonaws.com"

Write-Host "==> docker build $Root"
Set-Location $Root
docker build -t "${Repo}:${Tag}" -t "${Uri}:${Tag}" .

Write-Host "==> docker push ${Uri}:${Tag}"
docker push "${Uri}:${Tag}"

Write-Host "OK: ${Uri}:${Tag}"
