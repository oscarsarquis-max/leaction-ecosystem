#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
APPENV=/opt/lojadepaes/secrets/app.env
sudo sed -i 's/^LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=.*/LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=true/' $APPENV
sudo grep "^LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED=" $APPENV
cd $INFRA
sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p77-health2.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
done
sudo docker compose -f $COMPOSE exec -T api python -c 'from app.core.config import get_settings; s=get_settings(); print("public_acc", s.public_accompaniments_enabled); print("gigio_acc", s.gigio_accompaniments_enabled); print("gigio", s.gigio_enabled)'
curl -fsS https://lojadepaes.com.br/api/v1/gigio/status
echo
