#!/usr/bin/env bash
# Remove só o bloco do LePain e recarrega o Caddy. Não reinicia o contêiner.
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
docker exec -i "$CADDY_CONTAINER" sh -c 'cat > /tmp/Caddyfile.full' < "$CADDYFILE"
if ! docker exec "$CADDY_CONTAINER" grep -q '>>> gestao' /tmp/Caddyfile.full; then
  echo "ERRO: a cópia não contém o bloco da Gestão; o Caddy não foi recarregado." >&2
  cat "$BACKUP" > "$CADDYFILE"
  exit 1
fi
docker exec "$CADDY_CONTAINER" caddy validate --config /tmp/Caddyfile.full --adapter caddyfile || {
  cat "$BACKUP" > "$CADDYFILE"
  exit 1
}
docker exec "$CADDY_CONTAINER" caddy reload --config /tmp/Caddyfile.full --adapter caddyfile || {
  docker exec -i "$CADDY_CONTAINER" sh -c 'cat > /tmp/Caddyfile.full' < "$BACKUP"
  docker exec "$CADDY_CONTAINER" caddy reload --config /tmp/Caddyfile.full --adapter caddyfile || true
  cat "$BACKUP" > "$CADDYFILE"
  exit 1
}
echo "ok: bloco do LePain removido"
