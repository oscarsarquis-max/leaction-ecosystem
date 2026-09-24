#!/usr/bin/env bash
set -euo pipefail
# Dump do Postgres da Loja para S3. Rodar via cron no host.
# Não imprime a URL do banco.

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE="/tmp/lojadepaes-${STAMP}.sql.gz"
BUCKET="${LOJADEPAES_BACKUP_BUCKET:?}"
PREFIX="${LOJADEPAES_BACKUP_PREFIX:-lojadepaes-pg}"

docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T db \
  pg_dump -U lojadepaes -d lojadepaes --no-owner --format=plain \
  | gzip -c > "$FILE"

aws s3 cp "$FILE" "s3://${BUCKET}/${PREFIX}/${STAMP}.sql.gz" --only-show-errors
rm -f "$FILE"
echo "backup ok ${STAMP}"
