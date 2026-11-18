#!/usr/bin/env bash
# GESTAO-002 — primeira preparação do servidor para o Gestão. Roda UMA vez, no host.
#  - cria /opt/lojadepaes-gestao/{deploy,secrets,backups,images}
#  - cria o banco "gestao" e os papéis gestao_app e gestao_reader no Postgres da Loja
#    (só CREATE e GRANT; nenhuma tabela da Loja é alterada)
#  - gera as senhas AQUI (openssl) e grava só em secrets/app.env (chmod 600)
# Nenhuma senha passa por argumento de linha de comando nem aparece na saída.
set -euo pipefail

GESTAO_HOME=${GESTAO_HOME:-/opt/lojadepaes-gestao}
DB_CONTAINER=${GESTAO_DB_CONTAINER:-infra-db-1}
DB_SUPERUSER=${GESTAO_DB_SUPERUSER:-lojadepaes}
SQL_DIR="${1:-$GESTAO_HOME/deploy/sql}"

psql_super() { docker exec -i "$DB_CONTAINER" psql -U "$DB_SUPERUSER" "$@"; }

mkdir -p "$GESTAO_HOME"/{deploy,secrets,backups,images}
chmod 700 "$GESTAO_HOME/secrets"

if [ -f "$GESTAO_HOME/secrets/app.env" ]; then
  echo "ERRO: $GESTAO_HOME/secrets/app.env já existe; nada foi feito." >&2
  exit 1
fi

for item in "pg_roles:rolname:gestao_app" "pg_roles:rolname:gestao_reader" "pg_database:datname:gestao"; do
  tabela=${item%%:*}; resto=${item#*:}; coluna=${resto%%:*}; nome=${resto#*:}
  achou=$(psql_super -d postgres -tAc "SELECT 1 FROM $tabela WHERE $coluna = '$nome'")
  if [ -n "$achou" ]; then
    echo "ERRO: '$nome' já existe no Postgres; nada foi feito." >&2
    exit 1
  fi
done

APP_PW=$(openssl rand -hex 24)
READER_PW=$(openssl rand -hex 24)
SESSION_SECRET=$(openssl rand -hex 32)

{
  printf '\\set gestao_app_pw %s\n' "'$APP_PW'"
  printf '\\set gestao_reader_pw %s\n' "'$READER_PW'"
  cat "$SQL_DIR/01-gestao-papeis-e-banco.sql"
  printf '\n\\c lojadepaes\n'
  cat "$SQL_DIR/02-gestao-reader-grants.sql"
} | psql_super -d postgres -v ON_ERROR_STOP=1 -q >/dev/null

umask 077
cat > "$GESTAO_HOME/secrets/app.env" <<EOF
GESTAO_ENV=production
GESTAO_DATABASE_URL=postgresql+psycopg://gestao_app:${APP_PW}@db:5432/gestao
GESTAO_LOJA_DATABASE_URL=postgresql+psycopg://gestao_reader:${READER_PW}@db:5432/lojadepaes
GESTAO_SESSION_SECRET=${SESSION_SECRET}
GESTAO_COOKIE_SECURE=true
GESTAO_BAKERY_TIMEZONE=America/Sao_Paulo
EOF
chmod 600 "$GESTAO_HOME/secrets/app.env"
unset APP_PW READER_PW SESSION_SECRET

echo "ok: banco gestao, papéis gestao_app e gestao_reader criados; segredos em $GESTAO_HOME/secrets/app.env (600)"
