#!/usr/bin/env bash
# GESTAO-002 — backup próprio do banco "gestao" (o backup da Loja só cobre o banco lojadepaes).
# Gera /opt/lojadepaes-gestao/backups/gestao-<UTC>.sql.gz e guarda as 14 últimas.
# Envio ao S3 só acontece se GESTAO_BACKUP_S3=s3://bucket/prefixo estiver definido.
# Agendamento (cron) NÃO é instalado por este script: depende de autorização do Oscar.
set -euo pipefail

GESTAO_HOME=${GESTAO_HOME:-/opt/lojadepaes-gestao}
DB_CONTAINER=${GESTAO_DB_CONTAINER:-infra-db-1}
DIR="$GESTAO_HOME/backups"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE="$DIR/gestao-${STAMP}.sql.gz"

mkdir -p "$DIR"
umask 077
docker exec "$DB_CONTAINER" pg_dump -U gestao_app -d gestao --no-owner --format=plain | gzip -c > "$FILE"

if [ ! -s "$FILE" ] || ! gzip -t "$FILE"; then
  rm -f "$FILE"
  echo "ERRO: backup vazio ou corrompido" >&2
  exit 1
fi

if [ -n "${GESTAO_BACKUP_S3:-}" ]; then
  aws s3 cp "$FILE" "${GESTAO_BACKUP_S3%/}/gestao-${STAMP}.sql.gz" --only-show-errors
fi

# retenção: as 14 mais novas
ls -1t "$DIR"/gestao-*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f

echo "backup ok ${STAMP} ($(stat -c %s "$FILE") bytes)"
