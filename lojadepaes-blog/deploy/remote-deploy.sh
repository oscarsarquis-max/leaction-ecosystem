#!/usr/bin/env bash
# Sobe só o contêiner lepain. Não toca na Loja nem na Gestão.
# Uso: remote-deploy.sh <arquivo-tar-da-imagem> <tag>
set -euo pipefail

TAR="${1:?uso: remote-deploy.sh <tar> <tag>}"
TAG="${2:?uso: remote-deploy.sh <tar> <tag>}"
BLOG_HOME=${BLOG_HOME:-/opt/lojadepaes-blog}
COMPOSE=(docker compose -f "$BLOG_HOME/deploy/docker-compose.prod.yml" --env-file "$BLOG_HOME/deploy/.env")
IMAGE="lojadepaes-blog:${TAG}"
ENV_FILE="$BLOG_HOME/deploy/.env"

previous=""
if [ -f "$ENV_FILE" ]; then
  previous=$(grep -E '^LEPAIN_IMAGE=' "$ENV_FILE" | cut -d= -f2- || true)
fi

echo "== carregando imagem"
docker load -i "$TAR" >/dev/null
docker image inspect "$IMAGE" >/dev/null

printf 'LEPAIN_IMAGE=%s\n' "$IMAGE" > "$ENV_FILE"

echo "== subindo lepain"
"${COMPOSE[@]}" up -d --force-recreate lepain

health() {
  docker exec lepain python -c "
import sys, urllib.request as u
try:
    u.urlopen('http://127.0.0.1:8091/api/v1/health', timeout=4)
except Exception as erro:
    print('health falhou:', erro); sys.exit(1)
" 2>&1
}

ok=0
for _ in $(seq 1 20); do
  if health >/dev/null; then ok=1; break; fi
  sleep 3
done

if [ "$ok" -ne 1 ]; then
  echo "ERRO: lepain não ficou saudável. Última checagem:" >&2
  health >&2 || true
  docker logs --tail 40 lepain >&2 || true
  if [ -n "$previous" ] && docker image inspect "$previous" >/dev/null 2>&1; then
    echo "== voltando para a imagem anterior $previous" >&2
    printf 'LEPAIN_IMAGE=%s\n' "$previous" > "$ENV_FILE"
    "${COMPOSE[@]}" up -d --force-recreate lepain
  else
    echo "== sem imagem anterior: parando só o lepain" >&2
    "${COMPOSE[@]}" down
  fi
  exit 1
fi

echo "ok: lepain saudável com $IMAGE (anterior: ${previous:-nenhuma})"
