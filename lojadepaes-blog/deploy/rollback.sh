#!/usr/bin/env bash
# Para só o lepain e tira o bloco do Caddy. A Loja e a Gestão seguem.
set -euo pipefail

BLOG_HOME=${BLOG_HOME:-/opt/lojadepaes-blog}

docker compose -f "$BLOG_HOME/deploy/docker-compose.prod.yml" --env-file "$BLOG_HOME/deploy/.env" down
bash "$BLOG_HOME/deploy/caddy-remove.sh"
echo "rollback feito: lepain parado e fora do Caddy"
