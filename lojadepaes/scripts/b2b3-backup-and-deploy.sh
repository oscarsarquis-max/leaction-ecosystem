#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz
IMAGE=lojadepaes:prod-20261125a
ROLLBACK=lojadepaes:prod-20261124e
SECRETS=/opt/lojadepaes/secrets/app.env
REV=e1f4a2b90c83

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

sudo docker load -i /tmp/loja-prod-20261125a.tar
sudo docker image inspect $IMAGE >/dev/null
echo image_loaded

if grep -q "^LOJADEPAES_API_IMAGE=" .env; then
  sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=${IMAGE}|" .env
else
  echo "LOJADEPAES_API_IMAGE=${IMAGE}" >> .env
fi

if sudo grep -q "^LOJADEPAES_MARKETPLACE_ENABLED=" "$SECRETS"; then
  sudo sed -i "s|^LOJADEPAES_MARKETPLACE_ENABLED=.*|LOJADEPAES_MARKETPLACE_ENABLED=false|" "$SECRETS"
else
  echo "LOJADEPAES_MARKETPLACE_ENABLED=false" | sudo tee -a "$SECRETS" >/dev/null
fi

rollback_with_downgrade() {
  echo migrate_or_health_fail downgrade_to_d8b3f1a65c92 then "${PREV:-$ROLLBACK}"
  sudo docker compose -f $COMPOSE run --rm --no-deps -T -w /app/database api alembic downgrade d8b3f1a65c92 || true
  if [ -n "${PREV:-}" ]; then
    sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=${PREV}|" .env
    sudo docker compose -f $COMPOSE up -d --force-recreate api || true
  fi
  exit 1
}

sudo docker compose -f $COMPOSE run --rm --no-deps -T -w /app/database api alembic upgrade head || rollback_with_downgrade
echo alembic_upgraded
sudo docker compose -f $COMPOSE up -d --force-recreate api

i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/b2b3-health.json \
    && sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/ready >/tmp/b2b3-ready.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
  if [ $i -gt 16 ]; then
    rollback_with_downgrade
  fi
done
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
sudo docker inspect --format '{{.Image}} {{.Config.Image}} {{.State.StartedAt}}' "$(sudo docker compose -f $COMPOSE ps -q api)"
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
curl -fsS https://lojadepaes.com.br/api/v1/ready
echo
sudo docker compose -f $COMPOSE exec -T db psql -U lojadepaes -d lojadepaes -tAc "SELECT 'orders_after=' || count(*) FROM orders;"
sudo docker compose -f $COMPOSE exec -T db psql -U lojadepaes -d lojadepaes -tAc "SELECT 'payment_records_after=' || count(*) FROM payment_records;"

echo deploy_b2b3_done $STAMP
echo expected_revision $REV
echo rollback_image $ROLLBACK
