#!/usr/bin/env bash
# GESTAO-002 — rollback do Gestão (não toca na Loja):
#   1) para o compose do Gestão
#   2) remove o bloco do Caddyfile e faz caddy reload
# O banco "gestao" e os papéis ficam (nada é apagado). Para apagar de vez, ver o README.
set -euo pipefail

GESTAO_HOME=${GESTAO_HOME:-/opt/lojadepaes-gestao}

docker compose -f "$GESTAO_HOME/deploy/docker-compose.prod.yml" --env-file "$GESTAO_HOME/deploy/.env" down
bash "$GESTAO_HOME/deploy/caddy-remove.sh"
echo "rollback feito: Gestão parado e fora do Caddy"
