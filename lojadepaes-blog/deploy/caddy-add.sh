#!/usr/bin/env bash
# Acrescenta o bloco do LePain ao Caddyfile e recarrega. Não executar neste ciclo.
set -euo pipefail

CADDYFILE=${LEPAIN_CADDYFILE:-/opt/lojadepaes/app/infra/Caddyfile}
CADDY_CONTAINER=${LEPAIN_CADDY_CONTAINER:-infra-caddy-1}
BLOG_HOME=${BLOG_HOME:-/opt/lojadepaes-blog}
BLOCK="${1:-$BLOG_HOME/deploy/caddy/lepain.caddy}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$BLOG_HOME/backups/Caddyfile.bak-$STAMP"

if grep -q '>>> lepain' "$CADDYFILE"; then
  echo "ERRO: o bloco do LePain já está no Caddyfile; nada foi feito." >&2
  exit 1
fi

cp -p "$CADDYFILE" "$BACKUP"
if [ -n "$(tail -c1 "$CADDYFILE")" ]; then echo >> "$CADDYFILE"; fi
{ echo; cat "$BLOCK"; } >> "$CADDYFILE"

docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile || {
  cat "$BACKUP" > "$CADDYFILE"
  exit 1
}
docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || {
  cat "$BACKUP" > "$CADDYFILE"
  docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || true
  exit 1
}
echo "ok: bloco do LePain adicionado"
