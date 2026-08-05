#!/usr/bin/env bash
# Bootstrap host Lightsail quando user-data falhou ou em reinstall.
# Rodar como root: sudo bash bootstrap-lightsail-host.sh
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

API_HOST="${QMIND_API_HOST:-api.homolog.qmind.com.br}"
APP_HOST="${QMIND_APP_HOST:-app.homolog.qmind.com.br}"
PILOT_API_HOST="${QMIND_PILOT_API_HOST:-api.qmind.com.br}"
PILOT_APP_HOST="${QMIND_PILOT_APP_HOST:-qmind.com.br}"
PILOT_WWW_HOST="${QMIND_PILOT_WWW_HOST:-www.qmind.com.br}"
EVIDENCE_BUCKET="${QMIND_EVIDENCE_BUCKET:?set QMIND_EVIDENCE_BUCKET}"
BACKUP_BUCKET="${QMIND_BACKUP_BUCKET:?set QMIND_BACKUP_BUCKET}"
BACKUP_PREFIX="${QMIND_BACKUP_PREFIX:-pgdump/}"
AWS_REGION="${QMIND_AWS_REGION:-us-east-2}"

apt-get update -y
apt-get install -y ca-certificates curl gnupg openssl unzip

if ! command -v aws >/dev/null 2>&1; then
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  unzip -q /tmp/awscliv2.zip -d /tmp
  /tmp/aws/install
  rm -rf /tmp/aws /tmp/awscliv2.zip
fi

if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

systemctl enable --now docker
usermod -aG docker ubuntu || true

mkdir -p /opt/qmind/secrets /opt/qmind/bin
chmod 700 /opt/qmind/secrets

cat >/opt/qmind/INSTANCE_META.env <<META
QMIND_PROFILE=lightsail
QMIND_API_HOST=${API_HOST}
QMIND_APP_HOST=${APP_HOST}
QMIND_PILOT_API_HOST=${PILOT_API_HOST}
QMIND_PILOT_APP_HOST=${PILOT_APP_HOST}
QMIND_PILOT_WWW_HOST=${PILOT_WWW_HOST}
QMIND_EVIDENCE_BUCKET=${EVIDENCE_BUCKET}
QMIND_BACKUP_BUCKET=${BACKUP_BUCKET}
QMIND_BACKUP_PREFIX=${BACKUP_PREFIX}
QMIND_AWS_REGION=${AWS_REGION}
META
chmod 0644 /opt/qmind/INSTANCE_META.env

if [[ ! -f /opt/qmind/secrets/backup-openssl.key ]]; then
  openssl rand -out /opt/qmind/secrets/backup-openssl.key 32
  chmod 0600 /opt/qmind/secrets/backup-openssl.key
fi

echo "Place IAM keys in /opt/qmind/secrets/*.env chmod 0600 — see CREDENTIALS.md" > /opt/qmind/secrets/README
chmod 0644 /opt/qmind/secrets/README

echo "BOOTSTRAP_OK"
docker --version
docker compose version
