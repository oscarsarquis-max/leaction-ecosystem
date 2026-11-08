#!/usr/bin/env bash
# Remove só o bloco do LePain e recarrega o Caddy. Não executar neste ciclo.
set -euo pipefail

CADDYFILE=${LEPAIN_CADDYFILE:-/opt/lojadepaes/app/infra/Caddyfile}
CADDY_CONTAINER=${LEPAIN_CADDY_CONTAINER:-infra-caddy-1}
BLOG_HOME=${BLOG_HOME:-/opt/lojadepaes-blog}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$BLOG_HOME/backups/Caddyfile.pre-remove-$STAMP"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

if ! grep -q '>>> lepain' "$CADDYFILE"; then
  echo "o bloco do LePain não está no Caddyfile; nada a remover"
  exit 0
fi

cp -p "$CADDYFILE" "$BACKUP"
awk '
  /# >>> lepain/ { skip = 1 }
  !skip { print }
  /# <<< lepain/ { skip = 0 }
' "$CADDYFILE" > "$TMP"
cat "$TMP" > "$CADDYFILE"
docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
echo "ok: bloco do LePain removido"
