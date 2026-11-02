#!/usr/bin/env bash
# GESTAO-002 — troca a imagem do contêiner do Gestão. Roda no host.
# Uso: remote-deploy.sh <arquivo-tar-da-imagem> <tag>
# Só mexe no projeto compose "lojadepaes-gestao". Nenhum serviço da Loja é tocado.
set -euo pipefail

TAR="${1:?uso: remote-deploy.sh <tar> <tag>}"
TAG="${2:?uso: remote-deploy.sh <tar> <tag>}"
GESTAO_HOME=${GESTAO_HOME:-/opt/lojadepaes-gestao}
COMPOSE=(docker compose -f "$GESTAO_HOME/deploy/docker-compose.prod.yml" --env-file "$GESTAO_HOME/deploy/.env")
IMAGE="lojadepaes-gestao:${TAG}"
ENV_FILE="$GESTAO_HOME/deploy/.env"

previous=""
if [ -f "$ENV_FILE" ]; then
  previous=$(grep -E '^GESTAO_IMAGE=' "$ENV_FILE" | cut -d= -f2- || true)
fi

echo "== carregando imagem"
docker load -i "$TAR" >/dev/null
docker image inspect "$IMAGE" >/dev/null

echo "== migrações do banco gestao (contêiner efêmero)"
docker run --rm --network infra_default --env-file "$GESTAO_HOME/secrets/app.env" \
  --workdir /app/database --entrypoint alembic "$IMAGE" -c alembic.ini upgrade head

printf 'GESTAO_IMAGE=%s\n' "$IMAGE" > "$ENV_FILE"

echo "== subindo gestao-api"
"${COMPOSE[@]}" up -d --force-recreate gestao-api

health() {
  docker exec gestao-api python -c "
import sys, urllib.request as u
for caminho in ('/api/v1/health', '/api/v1/ready'):
    try:
        u.urlopen('http://127.0.0.1:8090' + caminho, timeout=4)
    except Exception as erro:
        print(caminho, 'falhou:', erro); sys.exit(1)
" 2>&1
}

ok=0
for i in $(seq 1 20); do
  if health >/dev/null; then ok=1; break; fi
  sleep 3
done

if [ "$ok" -ne 1 ]; then
  echo "ERRO: gestao-api não ficou saudável. Última checagem:" >&2
  health >&2 || true
  docker logs --tail 40 gestao-api >&2 || true
  if [ -n "$previous" ] && docker image inspect "$previous" >/dev/null 2>&1; then
    echo "== voltando para a imagem anterior $previous" >&2
    printf 'GESTAO_IMAGE=%s\n' "$previous" > "$ENV_FILE"
    "${COMPOSE[@]}" up -d --force-recreate gestao-api
  else
    echo "== sem imagem anterior: parando só o Gestão" >&2
    "${COMPOSE[@]}" down
  fi
  exit 1
fi

echo "ok: gestao-api saudável com $IMAGE (anterior: ${previous:-nenhuma})"
