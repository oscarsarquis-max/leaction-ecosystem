#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz
IMAGE=lojadepaes:prod-20261125c
ROLLBACK=lojadepaes:prod-20261125b
SECRETS=/opt/lojadepaes/secrets/app.env

echo start $STAMP
cd $INFRA
PREV=$(grep '^LOJADEPAES_API_IMAGE=' .env | cut -d= -f2- || true)
echo previous_image "${PREV:-unknown}"

sudo docker compose -f $COMPOSE exec -T db psql -U lojadepaes -d lojadepaes -tAc "SELECT 'orders_before=' || count(*) FROM orders;"
sudo docker compose -f $COMPOSE exec -T db psql -U lojadepaes -d lojadepaes -tAc "SELECT 'payment_records_before=' || count(*) FROM payment_records;"

sudo docker compose -f $COMPOSE exec -T db pg_dump -U lojadepaes -d lojadepaes --no-owner --format=plain | gzip -c > $FILE
BYTES=$(wc -c < $FILE)
if [ "$BYTES" -lt 1000 ]; then
  echo backup_too_small $BYTES
  exit 1
fi
sudo mkdir -p /opt/lojadepaes/backups
sudo cp $FILE /opt/lojadepaes/backups/lojadepaes-${STAMP}.sql.gz
echo backup_ok $STAMP bytes $BYTES

sudo docker load -i /tmp/loja-prod-20261125c.tar
sudo docker image inspect $IMAGE >/dev/null
echo image_loaded

if grep -q "^LOJADEPAES_API_IMAGE=" .env; then
  sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=${IMAGE}|" .env
else
  echo "LOJADEPAES_API_IMAGE=${IMAGE}" >> .env
fi

# Liga o marketplace; leads continua ligado.
if sudo grep -q "^LOJADEPAES_MARKETPLACE_ENABLED=" "$SECRETS"; then
  sudo sed -i "s|^LOJADEPAES_MARKETPLACE_ENABLED=.*|LOJADEPAES_MARKETPLACE_ENABLED=true|" "$SECRETS"
else
  echo "LOJADEPAES_MARKETPLACE_ENABLED=true" | sudo tee -a "$SECRETS" >/dev/null
fi
if sudo grep -q "^LOJADEPAES_MARKETPLACE_LEADS_ENABLED=" "$SECRETS"; then
  sudo sed -i "s|^LOJADEPAES_MARKETPLACE_LEADS_ENABLED=.*|LOJADEPAES_MARKETPLACE_LEADS_ENABLED=true|" "$SECRETS"
else
  echo "LOJADEPAES_MARKETPLACE_LEADS_ENABLED=true" | sudo tee -a "$SECRETS" >/dev/null
fi

rollback_image() {
  echo health_fail MARKETPLACE_ENABLED=false then "${PREV:-$ROLLBACK}"
  if sudo grep -q "^LOJADEPAES_MARKETPLACE_ENABLED=" "$SECRETS"; then
    sudo sed -i "s|^LOJADEPAES_MARKETPLACE_ENABLED=.*|LOJADEPAES_MARKETPLACE_ENABLED=false|" "$SECRETS"
  fi
  if [ -n "${PREV:-}" ]; then
    sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=${PREV}|" .env
    sudo docker compose -f $COMPOSE up -d --force-recreate api || true
  fi
  exit 1
}

sudo docker compose -f $COMPOSE up -d --force-recreate api

i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/b2b4a-health.json \
    && sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/ready >/tmp/b2b4a-ready.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
  if [ $i -gt 16 ]; then
    rollback_image
  fi
done
sudo docker inspect --format '{{.Image}} {{.Config.Image}} {{.State.StartedAt}}' "$(sudo docker compose -f $COMPOSE ps -q api)"
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
curl -fsS https://lojadepaes.com.br/api/v1/ready
echo
sudo docker compose -f $COMPOSE exec -T api printenv | grep -E 'MARKETPLACE_ENABLED|PUBLIC_PAYMENTS' || true
sudo docker compose -f $COMPOSE exec -T db psql -U lojadepaes -d lojadepaes -tAc "SELECT 'orders_after=' || count(*) FROM orders;"
sudo docker compose -f $COMPOSE exec -T db psql -U lojadepaes -d lojadepaes -tAc "SELECT 'payment_records_after=' || count(*) FROM payment_records;"

echo deploy_b2b4a_done $STAMP
echo rollback_image $ROLLBACK
