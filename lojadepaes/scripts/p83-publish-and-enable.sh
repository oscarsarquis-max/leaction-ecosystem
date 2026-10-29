#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
APPENV=/opt/lojadepaes/secrets/app.env

sudo docker compose -f $COMPOSE exec -T -w /app/backend api python -m app.domain.gigio.publish_pilot

sudo sed -i 's/^LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=.*/LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true/' $APPENV
sudo grep "^LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED=" $APPENV

sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p83-health2.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
  if [ $i -gt 16 ]; then
    echo health_fail
    sudo docker compose -f $COMPOSE logs --tail 80 api
    exit 1
  fi
done

sudo docker compose -f $COMPOSE exec -T api python -c 'from app.core.config import get_settings; s=get_settings(); print("pairing", s.gigio_pairing_refs_enabled); print("gigio", s.gigio_enabled); print("gigio_acc", s.gigio_accompaniments_enabled); print("public_acc", s.public_accompaniments_enabled); print("rules", __import__("app.domain.gigio.rules", fromlist=["PROCESS_RULES_VERSION"]).PROCESS_RULES_VERSION)'
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
curl -fsS https://lojadepaes.com.br/api/v1/gigio/status | head -c 400
echo
echo enable_done
