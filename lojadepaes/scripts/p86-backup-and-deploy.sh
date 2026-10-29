#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
APPENV=/opt/lojadepaes/secrets/app.env
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz
IMAGE=lojadepaes:prod-20261007n

echo start $STAMP
cd $INFRA
sudo docker compose -f $COMPOSE exec -T db pg_dump -U lojadepaes -d lojadepaes --no-owner --format=plain | gzip -c > $FILE
BYTES=$(wc -c < $FILE)
if [ "$BYTES" -lt 1000 ]; then
  echo backup_too_small $BYTES
  exit 1
fi
sudo mkdir -p /opt/lojadepaes/backups
sudo cp $FILE /opt/lojadepaes/backups/lojadepaes-${STAMP}.sql.gz
echo backup_ok $STAMP bytes $BYTES

sudo docker load -i /tmp/loja-prod-20261007n.tar
sudo docker image inspect $IMAGE >/dev/null
echo image_loaded

ensure_key() {
  key=$1
  value=$2
  if sudo grep -q "^${key}=" $APPENV; then
    echo keep $key
  else
    printf '%s=%s\n' "$key" "$value" | sudo tee -a $APPENV >/dev/null
    echo append $key
  fi
}
ensure_key LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED true
sudo sed -i 's/^LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=.*/LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true/' $APPENV
sudo sed -i 's/^LOJADEPAES_ACTIONHUB_MARKETPLACE_TIMEOUT_SECONDS=.*/LOJADEPAES_ACTIONHUB_MARKETPLACE_TIMEOUT_SECONDS=4/' $APPENV
sudo grep "^LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_GIGIO_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_ACTIONHUB_MARKETPLACE_TIMEOUT_SECONDS=" $APPENV

if grep -q "^LOJADEPAES_API_IMAGE=" $INFRA/.env; then
  sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007n/' $INFRA/.env
else
  echo LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007n >> $INFRA/.env
fi
grep "^LOJADEPAES_API_IMAGE=" $INFRA/.env

sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p86-health.json; then
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

sudo docker compose -f $COMPOSE exec -T api python -c 'from app.core.config import get_settings; from app.domain.gigio.rules import PROCESS_RULES_VERSION; from app.domain.accompaniment_context import ALLOWED_CATEGORIES; s=get_settings(); print("pairing", s.gigio_pairing_refs_enabled); print("gigio", s.gigio_enabled); print("gigio_acc", s.gigio_accompaniments_enabled); print("public_acc", s.public_accompaniments_enabled); print("timeout", s.actionhub_marketplace_timeout_seconds); print("rules", PROCESS_RULES_VERSION); print("cats", ",".join(sorted(ALLOWED_CATEGORIES)))'
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
echo deploy_n_done $STAMP
