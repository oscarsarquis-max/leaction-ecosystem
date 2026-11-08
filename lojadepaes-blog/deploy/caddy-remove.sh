#!/usr/bin/env bash
# Remove só o bloco do LePain e recarrega o Caddy. Não reinicia o contêiner.
# Grava no mesmo inode (cat > arquivo). Recusa se o inode do host e o do contêiner diferirem.
set -euo pipefail

CADDYFILE=${LEPAIN_CADDYFILE:-/opt/lojadepaes/app/infra/Caddyfile}
CADDY_CONTAINER=${LEPAIN_CADDY_CONTAINER:-infra-caddy-1}
BLOG_HOME=${BLOG_HOME:-/opt/lojadepaes-blog}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$BLOG_HOME/backups/Caddyfile.pre-remove-$STAMP"
NEW="$BLOG_HOME/backups/Caddyfile.without-lepain-$STAMP"

if ! grep -q '>>> lepain' "$CADDYFILE"; then
  echo "o bloco do LePain não está no Caddyfile; nada a remover"
  exit 0
fi
if ! docker inspect "$CADDY_CONTAINER" --format '{{range .Mounts}}{{.Source}}={{.Destination}}{{"\n"}}{{end}}' \
     | grep -qx "$CADDYFILE=/etc/caddy/Caddyfile"; then
  echo "ERRO: $CADDYFILE não é o arquivo montado em /etc/caddy/Caddyfile de $CADDY_CONTAINER." >&2
  exit 1
fi

host_inode=$(stat -c %i "$CADDYFILE")
box_inode=$(docker exec "$CADDY_CONTAINER" stat -c %i /etc/caddy/Caddyfile)
if [ "$host_inode" != "$box_inode" ]; then
  echo "ERRO: inode do host ($host_inode) difere do contêiner ($box_inode). Nada foi alterado." >&2
  exit 1
fi

mkdir -p "$BLOG_HOME/backups"
cp -p "$CADDYFILE" "$BACKUP"
awk '
  /# >>> lepain/ { skip = 1; next }
  /# <<< lepain/ { skip = 0; next }
  !skip { print }
' "$CADDYFILE" > "$NEW"
cat "$NEW" > "$CADDYFILE"
rm -f "$NEW"

if [ "$(stat -c %i "$CADDYFILE")" != "$host_inode" ]; then
  echo "ERRO: a gravação trocou o inode. Restaurando a cópia." >&2
  cat "$BACKUP" > "$CADDYFILE" || true
  exit 1
fi

docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile || {
  cat "$BACKUP" > "$CADDYFILE"
  exit 1
}
docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || {
  cat "$BACKUP" > "$CADDYFILE"
  docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || true
  exit 1
}
echo "ok: bloco do LePain removido"
