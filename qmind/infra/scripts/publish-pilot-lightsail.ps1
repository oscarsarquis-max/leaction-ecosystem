<#
.SYNOPSIS
  Publica baseline piloto (qmind.com.br + api) no mesmo Lightsail da homolog.
  Usa chave temporária Lightsail. Não imprime secrets.
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
$dir = Join-Path $env:TEMP ("pilot-pub-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
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

Write-Host "== Pack source =="
$tar = Join-Path $dir "qmind-pilot.tgz"
# Paths relative to qmind root
Push-Location $root
try {
  tar -czf $tar `
    --exclude=backend/.venv `
    --exclude=backend/__pycache__ `
    --exclude=web/node_modules `
    --exclude=web/dist `
    --exclude=packages/api-client/node_modules `
    --exclude=**/__pycache__ `
    --exclude=**/.pytest_cache `
    backend web packages/api-client package.json package-lock.json infra/compose
} finally {
  Pop-Location
}

Write-Host "== Upload =="
scp @sshOpts $tar "${sshTarget}:/tmp/qmind-pilot.tgz"

Write-Host "== Extract + rebuild =="
$remote = @'
set -euo pipefail
cd /opt/qmind
sudo tar -xzf /tmp/qmind-pilot.tgz
rm -f /tmp/qmind-pilot.tgz

# Metadados piloto (sem secrets)
if [[ -f /opt/qmind/INSTANCE_META.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source /opt/qmind/INSTANCE_META.env
  set +a
fi
sudo tee /opt/qmind/INSTANCE_META.env >/dev/null <<META
QMIND_PROFILE=lightsail
QMIND_API_HOST=${QMIND_API_HOST:-api.homolog.qmind.com.br}
QMIND_APP_HOST=${QMIND_APP_HOST:-app.homolog.qmind.com.br}
QMIND_PILOT_API_HOST=api.qmind.com.br
QMIND_PILOT_APP_HOST=qmind.com.br
QMIND_PILOT_WWW_HOST=www.qmind.com.br
QMIND_EVIDENCE_BUCKET=${QMIND_EVIDENCE_BUCKET}
QMIND_BACKUP_BUCKET=${QMIND_BACKUP_BUCKET}
QMIND_BACKUP_PREFIX=${QMIND_BACKUP_PREFIX:-pgdump/}
QMIND_AWS_REGION=${QMIND_AWS_REGION:-us-east-2}
META
sudo chmod 0644 /opt/qmind/INSTANCE_META.env

cd /opt/qmind/infra/compose
# Compose .env: preservar existentes; garantir hosts piloto + CORS
if [[ ! -f .env ]]; then
  echo "MISSING_COMPOSE_ENV" >&2
  exit 2
fi
# Sempre terminar com newline antes de append (evita colar na última chave).
sudo sed -i -e '$a\' .env

# Reparar CLIENT_ID se append sem newline colou QMIND_PILOT_* na mesma linha.
if grep -qE '^VITE_COGNITO_CLIENT_ID=.+QMIND_PILOT_' .env; then
  sudo sed -i -E 's/^(VITE_COGNITO_CLIENT_ID=[A-Za-z0-9]+)QMIND_PILOT_.*/\1/' .env
fi
if grep -qE '^COGNITO_APP_CLIENT_ID=.+QMIND_PILOT_' .env; then
  sudo sed -i -E 's/^(COGNITO_APP_CLIENT_ID=[A-Za-z0-9]+)QMIND_PILOT_.*/\1/' .env
fi
# Remover CR e garantir newline final (evita colagem na próxima append).
sudo sed -i 's/\r$//' .env
sudo sed -i -e '$a\' .env

ensure_kv() {
  local key="$1" val="$2"
  if grep -q "^${key}=" .env; then
    sudo sed -i "s|^${key}=.*|${key}=${val}|" .env
  else
    printf '%s=%s\n' "$key" "$val" | sudo tee -a .env >/dev/null
  fi
}
ensure_kv QMIND_PILOT_API_HOST api.qmind.com.br
ensure_kv QMIND_PILOT_APP_HOST qmind.com.br
ensure_kv QMIND_PILOT_WWW_HOST www.qmind.com.br
ensure_kv CORS_ORIGINS 'https://qmind.com.br,https://www.qmind.com.br,https://app.homolog.qmind.com.br'

# Sanity: client id limpo (Cognito app client = 26 chars alfanuméricos).
cid="$(grep -E '^VITE_COGNITO_CLIENT_ID=' .env | head -1 | cut -d= -f2- | tr -d '\r' || true)"
app_cid="$(grep -E '^COGNITO_APP_CLIENT_ID=' .env | head -1 | cut -d= -f2- | tr -d '\r' || true)"
if [[ -n "$app_cid" && "$cid" != "$app_cid" ]]; then
  echo "SYNC_VITE_COGNITO_CLIENT_ID_FROM_APP"
  ensure_kv VITE_COGNITO_CLIENT_ID "$app_cid"
  cid="$app_cid"
fi
if [[ -z "$cid" || "$cid" == *"="* || "$cid" == *"QMIND_"* || ${#cid} -lt 20 ]]; then
  echo "BAD_VITE_COGNITO_CLIENT_ID len=${#cid}" >&2
  exit 3
fi
echo "COGNITO_CLIENT_ID_LEN=${#cid}"

set -a
# shellcheck disable=SC1091
source .env
set +a

sudo docker compose -f docker-compose.homolog.yml build api worker web web_homolog
sudo docker compose -f docker-compose.homolog.yml up -d --remove-orphans
# Schema: aplicar migrations com identidade admin no container da API
sudo docker compose -f docker-compose.homolog.yml exec -T api \
  alembic upgrade head
sudo docker compose -f docker-compose.homolog.yml ps
echo PUBLISH_OK
'@

$remoteFile = Join-Path $dir "remote.sh"
Write-Lf $remoteFile $remote
scp @sshOpts $remoteFile "${sshTarget}:/tmp/publish-pilot.sh"
ssh @sshOpts $sshTarget "bash /tmp/publish-pilot.sh; rm -f /tmp/publish-pilot.sh"

Write-Host "== Done =="
Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
