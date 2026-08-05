#!/usr/bin/env bash
# Backup operacional homolog (Lightsail).
# Requer: docker compose com serviço db; awscli; /opt/qmind/secrets/backup-uploader.env (0600)
# Não usa credencial da aplicação.
set -euo pipefail

META="${QMIND_META:-/opt/qmind/INSTANCE_META.env}"
# shellcheck disable=SC1090
source "$META"

# Evita credencial residual do ambiente sobrescrever o uploader.
unset AWS_SESSION_TOKEN AWS_SECURITY_TOKEN AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY || true
# KEY=VAL sem "export" (formato docker env_file) — set -a exporta para o CLI aws.
set -a
# shellcheck disable=SC1091
source /opt/qmind/secrets/backup-uploader.env
set +a

COMPOSE_DIR="${COMPOSE_DIR:-/opt/qmind/infra/compose}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

RAW="$TMPDIR/qmind-${STAMP}.sql"
ENC="$TMPDIR/qmind-${STAMP}.sql.gpg"
KEY_ID="${BACKUP_GPG_RECIPIENT:-}"

cd "$COMPOSE_DIR"
POSTGRES_USER="${POSTGRES_USER:-qmind_admin}"
POSTGRES_DB="${POSTGRES_DB:-qmind}"
if [[ -f .env.homolog ]]; then
  POSTGRES_USER="$(awk -F= '/^POSTGRES_USER=/{print substr($0,15); exit}' .env.homolog)"
  POSTGRES_DB="$(awk -F= '/^POSTGRES_DB=/{print substr($0,13); exit}' .env.homolog)"
  POSTGRES_USER="${POSTGRES_USER:-qmind_admin}"
  POSTGRES_DB="${POSTGRES_DB:-qmind}"
fi

docker compose -f docker-compose.homolog.yml exec -T db \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --format=plain >"$RAW"

if [[ -n "$KEY_ID" ]]; then
  gpg --batch --yes --encrypt --recipient "$KEY_ID" --output "$ENC" "$RAW"
  UPLOAD_FILE="$ENC"
  REMOTE_NAME="${QMIND_BACKUP_PREFIX}qmind-${STAMP}.sql.gpg"
else
  OPENSSL_KEY_FILE="${BACKUP_OPENSSL_KEY_FILE:-/opt/qmind/secrets/backup-openssl.key}"
  if [[ ! -f "$OPENSSL_KEY_FILE" ]]; then
    echo "Defina BACKUP_GPG_RECIPIENT ou crie $OPENSSL_KEY_FILE (32 bytes, chmod 0600)" >&2
    exit 1
  fi
  ENC="$TMPDIR/qmind-${STAMP}.sql.enc"
  openssl enc -aes-256-cbc -salt -pbkdf2 -in "$RAW" -out "$ENC" -pass "file:${OPENSSL_KEY_FILE}"
  UPLOAD_FILE="$ENC"
  REMOTE_NAME="${QMIND_BACKUP_PREFIX}qmind-${STAMP}.sql.enc"
fi

# s3api PutObject: policy Put-only (sem Head/Get do aws s3 cp).
aws s3api put-object \
  --bucket "${QMIND_BACKUP_BUCKET}" \
  --key "${REMOTE_NAME}" \
  --body "${UPLOAD_FILE}" \
  --region "${QMIND_AWS_REGION}" >/dev/null

aws cloudwatch put-metric-data \
  --region "${QMIND_AWS_REGION}" \
  --namespace QMind/Homolog \
  --metric-data "MetricName=BackupSuccess,Value=1,Unit=Count,Dimensions=[{Name=Environment,Value=homolog}]"

echo "OK ${REMOTE_NAME}"
