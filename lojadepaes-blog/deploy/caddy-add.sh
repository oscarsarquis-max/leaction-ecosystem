#!/usr/bin/env bash
# Acrescenta o bloco do LePain ao Caddyfile e recarrega. Não reinicia o Caddy.
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
if ! docker inspect "$CADDY_CONTAINER" --format '{{range .Mounts}}{{.Source}}={{.Destination}}{{"\n"}}{{end}}' \
     | grep -qx "$CADDYFILE=/etc/caddy/Caddyfile"; then
  echo "ERRO: $CADDYFILE não é o arquivo montado em /etc/caddy/Caddyfile de $CADDY_CONTAINER." >&2
  exit 1
fi

mkdir -p "$BLOG_HOME/backups"
cp -p "$CADDYFILE" "$BACKUP"
echo "cópia do Caddyfile: $BACKUP"
if [ -n "$(tail -c1 "$CADDYFILE")" ]; then echo >> "$CADDYFILE"; fi
{ echo; cat "$BLOCK"; } >> "$CADDYFILE"

# O bind de arquivo único pode ficar num inode antigo (nlink 0, só leitura).
# Recarregar esse arquivo apaga a Gestão. O processo lê a cópia em /tmp.
docker exec -i "$CADDY_CONTAINER" sh -c 'cat > /tmp/Caddyfile.full' < "$CADDYFILE"
if ! docker exec "$CADDY_CONTAINER" grep -q '>>> gestao' /tmp/Caddyfile.full; then
  echo "ERRO: a cópia não contém o bloco da Gestão; o Caddy não foi recarregado." >&2
  cat "$BACKUP" > "$CADDYFILE"
  exit 1
fi
if ! docker exec "$CADDY_CONTAINER" grep -q '>>> lepain' /tmp/Caddyfile.full; then
  echo "ERRO: a cópia não contém o bloco do LePain; o Caddy não foi recarregado." >&2
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
echo "ok: bloco do LePain adicionado"
