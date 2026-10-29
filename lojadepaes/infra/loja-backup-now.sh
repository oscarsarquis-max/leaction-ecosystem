#!/usr/bin/env bash
set -euo pipefail
# Dump local do Postgres de produção. Não imprime URL nem senha.

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DIR=/opt/lojadepaes/backups
FILE="${DIR}/lojadepaes-${STAMP}.sql.gz"
mkdir -p "$DIR" 2>/dev/null || true
if [ ! -w "$DIR" ]; then
  FILE="/tmp/lojadepaes-${STAMP}.sql.gz"
fi
docker compose -f /opt/lojadepaes/app/infra/docker-compose.prod.yml exec -T db \
  pg_dump -U lojadepaes -d lojadepaes --no-owner --format=plain \
  | gzip -c > "$FILE"
if [ -d /opt/lojadepaes/backups ] && [ -w /opt/lojadepaes/backups ]; then
  :
elif [ -d /opt/lojadepaes/backups ]; then
  cp "$FILE" "/opt/lojadepaes/backups/lojadepaes-${STAMP}.sql.gz" 2>/dev/null || true
fi
echo "backup ok ${STAMP}"
