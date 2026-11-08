#!/usr/bin/env bash
# GESTAO-002 — remove o bloco do Gestão e faz caddy reload.
# Grava no mesmo inode (cat > arquivo). Recusa se o inode do host e o do contêiner diferirem.
set -euo pipefail

CADDYFILE=${GESTAO_CADDYFILE:-/opt/lojadepaes/app/infra/Caddyfile}
CADDY_CONTAINER=${GESTAO_CADDY_CONTAINER:-infra-caddy-1}
GESTAO_HOME=${GESTAO_HOME:-/opt/lojadepaes-gestao}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$GESTAO_HOME/backups/Caddyfile.pre-remove-$STAMP"
NEW="$GESTAO_HOME/backups/Caddyfile.without-gestao-$STAMP"

if ! grep -q '>>> gestao' "$CADDYFILE"; then
  echo "o bloco do Gestão não está no Caddyfile; nada a remover"
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

mkdir -p "$GESTAO_HOME/backups"
cp -p "$CADDYFILE" "$BACKUP"
awk '
  /# >>> gestao/ { skip = 1; next }
  /# <<< gestao/ { skip = 0; next }
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
echo "ok: bloco removido (cópia anterior em $BACKUP) e caddy reload feito"
