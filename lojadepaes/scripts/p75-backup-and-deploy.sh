#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
APPENV=/opt/lojadepaes/secrets/app.env
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz

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

sudo docker load -i /tmp/loja-prod-20261006i.tar
sudo docker image inspect lojadepaes:prod-20261006i >/dev/null
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
ensure_key LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED false
ensure_key LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED false
ensure_key LOJADEPAES_ACCOMPANIMENTS_PREVIEW false
ensure_key LOJADEPAES_ACTIONHUB_MARKETPLACE_URL https://actionhub.com.br/marketplace-api
ensure_key LOJADEPAES_ACTIONHUB_MARKETPLACE_TIMEOUT_SECONDS 2

if grep -q "^LOJADEPAES_API_IMAGE=" $INFRA/.env; then
  sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261006i/' $INFRA/.env
else
  echo LOJADEPAES_API_IMAGE=lojadepaes:prod-20261006i >> $INFRA/.env
fi
grep "^LOJADEPAES_API_IMAGE=" $INFRA/.env

sudo docker compose -f $COMPOSE up -d api
i=1
while [ $i -le 12 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p75-loja-health.json; then
    echo api_health_ok try=$i
    break
  fi
  i=$((i+1))
  sleep 4
  if [ $i -gt 12 ]; then
    echo api_health_fail
    sudo docker compose -f $COMPOSE logs --tail 80 api
    exit 1
  fi
done

sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic upgrade head
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
echo alembic_done
curl -fsS --max-time 10 https://lojadepaes.com.br/api/v1/health
echo
echo loja_done $STAMP
