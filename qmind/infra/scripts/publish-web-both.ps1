<#
.SYNOPSIS
  Publica frontend em homolog (web_homolog) E piloto (web) no mesmo Lightsail.
#>
param(
  [string] $Region = "us-east-2",
  [string] $InstanceName = "qmind-homolog-app"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

function Write-Lf([string]$Path, [string]$Content) {
  [IO.File]::WriteAllBytes($Path, [Text.Encoding]::UTF8.GetBytes(($Content -replace "`r`n", "`n")))
}

Write-Host "== Lightsail access =="
$details = aws lightsail get-instance-access-details --instance-name $InstanceName --region $Region --protocol ssh --output json | ConvertFrom-Json
$ad = $details.accessDetails
$dir = Join-Path $env:TEMP ("web-both-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$pem = Join-Path $dir "id_rsa"
$cert = Join-Path $dir "id_rsa-cert.pub"
Write-Lf $pem $ad.privateKey
Write-Lf $cert $ad.certKey
icacls $pem /inheritance:r | Out-Null
icacls $pem /grant:r "$($env:USERNAME):(R)" | Out-Null
icacls $cert /inheritance:r | Out-Null
icacls $cert /grant:r "$($env:USERNAME):(R)" | Out-Null
$sshTarget = "$($ad.username)@$($ad.ipAddress)"
$sshOpts = @("-i", $pem, "-o", "CertificateFile=$cert", "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new")

Write-Host "== Pack web source =="
$tar = Join-Path $dir "qmind-web.tgz"
Push-Location $root
try {
  tar -czf $tar `
    --exclude=web/node_modules `
    --exclude=web/dist `
    --exclude=packages/api-client/node_modules `
    web packages/api-client package.json package-lock.json
} finally {
  Pop-Location
}

Write-Host "== Upload =="
scp @sshOpts $tar "${sshTarget}:/tmp/qmind-web.tgz"

Write-Host "== Rebuild web + web_homolog =="
$remote = @'
set -euo pipefail
cd /opt/qmind
sudo tar -xzf /tmp/qmind-web.tgz
rm -f /tmp/qmind-web.tgz
cd /opt/qmind/infra/compose
set -a
# shellcheck disable=SC1091
source .env
set +a
sudo docker compose -f docker-compose.homolog.yml build web web_homolog
sudo docker compose -f docker-compose.homolog.yml up -d web web_homolog
sudo docker compose -f docker-compose.homolog.yml ps web web_homolog
echo WEB_BOTH_OK
'@

$remoteFile = Join-Path $dir "remote.sh"
Write-Lf $remoteFile $remote
scp @sshOpts $remoteFile "${sshTarget}:/tmp/publish-web-both.sh"
ssh @sshOpts $sshTarget "bash /tmp/publish-web-both.sh; rm -f /tmp/publish-web-both.sh"

Write-Host "== Done (homolog + pilot web) =="
Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
