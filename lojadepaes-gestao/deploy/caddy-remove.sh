#!/usr/bin/env bash
# GESTAO-002 (rollback) — remove o bloco do Gestão do Caddyfile e faz `caddy reload`.
# Remove só o trecho entre os marcadores ">>> gestao" e "<<< gestao"; o resto fica intacto.
set -euo pipefail

CADDYFILE=${GESTAO_CADDYFILE:-/opt/lojadepaes/app/infra/Caddyfile}
CADDY_CONTAINER=${GESTAO_CADDY_CONTAINER:-infra-caddy-1}
GESTAO_HOME=${GESTAO_HOME:-/opt/lojadepaes-gestao}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$GESTAO_HOME/backups/Caddyfile.pre-remove-$STAMP"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

if ! grep -q '>>> gestao' "$CADDYFILE"; then
  echo "o bloco do Gestão não está no Caddyfile; nada a remover"
  exit 0
fi

cp -p "$CADDYFILE" "$BACKUP"
awk '
  /# >>> gestao/ { skip = 1 }
  !skip { print }
  /# <<< gestao/ { skip = 0 }
' "$CADDYFILE" > "$TMP"

cat "$TMP" > "$CADDYFILE"   # mesmo inode
docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null
docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
echo "ok: bloco removido (cópia anterior em $BACKUP) e caddy reload feito"
