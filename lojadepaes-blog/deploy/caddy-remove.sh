#!/usr/bin/env bash
# Apaga sites/lepain.caddy e recarrega o Caddy. Não altera o Caddyfile da Loja.
set -euo pipefail

SITES=${LEPAIN_CADDY_SITES:-/opt/lojadepaes/app/infra/caddy/sites}
CADDY_CONTAINER=${LEPAIN_CADDY_CONTAINER:-infra-caddy-1}
BLOG_HOME=${BLOG_HOME:-/opt/lojadepaes-blog}
DEST="$SITES/lepain.caddy"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$BLOG_HOME/backups/lepain.caddy.pre-remove-$STAMP"

if [ ! -e "$DEST" ]; then
  echo "sites/lepain.caddy não existe; nada a remover"
  exit 0
fi

mkdir -p "$BLOG_HOME/backups"
cp -p "$DEST" "$BACKUP"
rm -f "$DEST"
docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile || {
  cp -p "$BACKUP" "$DEST"
  exit 1
}
docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || {
  cp -p "$BACKUP" "$DEST"
  docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || true
  exit 1
}
echo "ok: sites/lepain.caddy apagado"
