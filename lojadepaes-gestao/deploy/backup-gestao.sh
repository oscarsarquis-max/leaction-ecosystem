#!/usr/bin/env bash
# GESTAO-003 — backup diário do banco "gestao" (e só dele).
#
#   1. pg_dump -Fc do banco gestao, dentro do contêiner do Postgres da Loja;
#   2. confere o arquivo (pg_restore --list);
#   3. envia ao bucket S3 privado, com a credencial de /etc/gestao/backup.env;
#   4. guarda os 7 dias mais novos no host.
#
# Agenda: /etc/cron.d/gestao-backup (diário, 03:17 de Brasília). Rollback: apagar esse arquivo de cron.
# A credencial (usuário IAM gestao-backup: só s3:PutObject e s3:ListBucket naquele bucket) fica em
# /etc/gestao/backup.env, dono root, modo 600. Este script nunca imprime a credencial.
set -euo pipefail

GESTAO_HOME=${GESTAO_HOME:-/opt/lojadepaes-gestao}
ENV_FILE=${GESTAO_BACKUP_ENV:-/etc/gestao/backup.env}
DB_CONTAINER=${GESTAO_DB_CONTAINER:-infra-db-1}
DIR="$GESTAO_HOME/backups"
MANTER_DIAS=${GESTAO_BACKUP_DIAS:-7}
INICIO=$(date +%s)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
ARQUIVO="$DIR/gestao-${STAMP}.dump"

if [ ! -r "$ENV_FILE" ]; then
  echo "ERRO: não consigo ler $ENV_FILE" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
: "${GESTAO_BACKUP_BUCKET:?falta GESTAO_BACKUP_BUCKET em $ENV_FILE}"
: "${AWS_ACCESS_KEY_ID:?falta a credencial em $ENV_FILE}"
: "${AWS_SECRET_ACCESS_KEY:?falta a credencial em $ENV_FILE}"
export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-2}

mkdir -p "$DIR"
umask 077

# só o banco gestao: nunca lojadepaes
docker exec "$DB_CONTAINER" pg_dump -U gestao_app -d gestao --no-owner --format=custom > "$ARQUIVO"

if [ ! -s "$ARQUIVO" ] || ! docker exec -i "$DB_CONTAINER" pg_restore --list < "$ARQUIVO" > /dev/null; then
  rm -f "$ARQUIVO"
  echo "ERRO: backup vazio ou ilegível" >&2
  exit 1
fi

python3 "$GESTAO_HOME/deploy/s3_put.py" "$ARQUIVO" "$GESTAO_BACKUP_BUCKET" "gestao/$(basename "$ARQUIVO")"

# retenção local: os últimos N dias
find "$DIR" -maxdepth 1 -name 'gestao-*.dump' -mtime +"$((MANTER_DIAS - 1))" -delete
# restos do formato antigo (.sql.gz, GESTAO-002) seguem a mesma regra
find "$DIR" -maxdepth 1 -name 'gestao-*.sql.gz' -mtime +"$((MANTER_DIAS - 1))" -delete

FIM=$(date +%s)
echo "backup ok ${STAMP} $(stat -c %s "$ARQUIVO") bytes, $((FIM - INICIO)) s, enviado a s3://${GESTAO_BACKUP_BUCKET}/gestao/$(basename "$ARQUIVO")"
