#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml

sudo docker compose -f $COMPOSE exec -T -w /app/backend api python -m app.domain.gigio.publish_pilot

sudo docker compose -f $COMPOSE exec -T api python -c 'from app.core.config import get_settings; from app.domain.gigio.rules import PROCESS_RULES_VERSION; s=get_settings(); print("pairing", s.gigio_pairing_refs_enabled); print("rules", PROCESS_RULES_VERSION)'
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
curl -fsS https://lojadepaes.com.br/api/v1/gigio/status | head -c 400
echo
echo publish_84_done
