#!/usr/bin/env bash
# Grava sites/lepain.caddy e recarrega o Caddy. Não altera o Caddyfile da Loja.
set -euo pipefail

SITES=${LEPAIN_CADDY_SITES:-/opt/lojadepaes/app/infra/caddy/sites}
CADDY_CONTAINER=${LEPAIN_CADDY_CONTAINER:-infra-caddy-1}
BLOG_HOME=${BLOG_HOME:-/opt/lojadepaes-blog}
BLOCK="${1:-$BLOG_HOME/deploy/caddy/lepain.caddy}"
DEST="$SITES/lepain.caddy"

if [ -e "$DEST" ]; then
  echo "ERRO: $DEST já existe; nada foi feito." >&2
  exit 1
fi
if [ ! -f "$BLOCK" ]; then
  echo "ERRO: bloco não encontrado: $BLOCK" >&2
  exit 1
fi

mkdir -p "$SITES"
cp "$BLOCK" "$DEST"
docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile || {
  rm -f "$DEST"
  exit 1
}
docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || {
  rm -f "$DEST"
  docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || true
  exit 1
}
echo "ok: sites/lepain.caddy gravado"
