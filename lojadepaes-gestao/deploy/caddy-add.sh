#!/usr/bin/env bash
# GESTAO-002 — acrescenta o bloco do Gestão ao Caddyfile do servidor e faz `caddy reload`.
#  - grava NO MESMO ARQUIVO (>>), para não trocar o inode do bind mount de arquivo único
#  - guarda cópia do Caddyfile antes, valida antes do reload e desfaz se algo falhar
#  - reload é gracioso: a Loja não perde conexão
set -euo pipefail

CADDYFILE=${GESTAO_CADDYFILE:-/opt/lojadepaes/app/infra/Caddyfile}
CADDY_CONTAINER=${GESTAO_CADDY_CONTAINER:-infra-caddy-1}
GESTAO_HOME=${GESTAO_HOME:-/opt/lojadepaes-gestao}
BLOCK="${1:-$GESTAO_HOME/deploy/gestao.caddy}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$GESTAO_HOME/backups/Caddyfile.bak-$STAMP"

if grep -q '>>> gestao' "$CADDYFILE"; then
  echo "ERRO: o bloco do Gestão já está no Caddyfile; nada foi feito." >&2
  exit 1
fi
if ! docker inspect "$CADDY_CONTAINER" --format '{{range .Mounts}}{{.Source}}={{.Destination}}{{"\n"}}{{end}}' \
     | grep -qx "$CADDYFILE=/etc/caddy/Caddyfile"; then
  echo "ERRO: $CADDYFILE não é o arquivo montado em /etc/caddy/Caddyfile de $CADDY_CONTAINER." >&2
  exit 1
fi

cp -p "$CADDYFILE" "$BACKUP"
echo "cópia do Caddyfile: $BACKUP"

restaurar() {
  echo "ERRO: restaurando o Caddyfile original" >&2
  cat "$BACKUP" > "$CADDYFILE"   # mesmo inode
  docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile >&2 || true
  exit 1
}

# garante quebra de linha no fim e acrescenta (>> preserva o inode)
if [ -n "$(tail -c1 "$CADDYFILE")" ]; then echo >> "$CADDYFILE"; fi
{ echo; cat "$BLOCK"; } >> "$CADDYFILE"

docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1 || {
  docker exec "$CADDY_CONTAINER" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >&2 || true
  restaurar
}
docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile || restaurar
echo "ok: bloco do Gestão adicionado e caddy reload feito"
