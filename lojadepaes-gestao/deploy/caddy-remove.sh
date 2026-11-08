#!/usr/bin/env bash
# Apaga sites/gestao.caddy e recarrega o Caddy. Não altera o Caddyfile da Loja.
set -euo pipefail

SITES=${GESTAO_CADDY_SITES:-/opt/lojadepaes/app/infra/caddy/sites}
CADDY_CONTAINER=${GESTAO_CADDY_CONTAINER:-infra-caddy-1}
GESTAO_HOME=${GESTAO_HOME:-/opt/lojadepaes-gestao}
DEST="$SITES/gestao.caddy"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$GESTAO_HOME/backups/gestao.caddy.pre-remove-$STAMP"

if [ ! -e "$DEST" ]; then
  echo "sites/gestao.caddy não existe; nada a remover"
  exit 0
fi

mkdir -p "$GESTAO_HOME/backups"
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
echo "ok: sites/gestao.caddy apagado"
