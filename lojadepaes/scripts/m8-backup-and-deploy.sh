#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz
IMAGE=lojadepaes:prod-20261124e
ROLLBACK=lojadepaes:prod-20261124d
SECRETS=/opt/lojadepaes/secrets/app.env
REV=d8b3f1a65c92

echo start $STAMP
cd $INFRA
PREV=$(grep '^LOJADEPAES_API_IMAGE=' .env | cut -d= -f2- || true)
echo previous_image "${PREV:-unknown}"

sudo docker compose -f $COMPOSE exec -T db pg_dump -U lojadepaes -d lojadepaes --no-owner --format=plain | gzip -c > $FILE
BYTES=$(wc -c < $FILE)
if [ "$BYTES" -lt 1000 ]; then
  echo backup_too_small $BYTES
  exit 1
fi
sudo mkdir -p /opt/lojadepaes/backups
sudo cp $FILE /opt/lojadepaes/backups/lojadepaes-${STAMP}.sql.gz
echo backup_ok $STAMP bytes $BYTES

sudo docker load -i /tmp/loja-prod-20261124e.tar
sudo docker image inspect $IMAGE >/dev/null
echo image_loaded

if grep -q "^LOJADEPAES_API_IMAGE=" .env; then
  sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=${IMAGE}|" .env
else
  echo "LOJADEPAES_API_IMAGE=${IMAGE}" >> .env
fi

# Marketplace permanece desligado (M8).
if sudo grep -q "^LOJADEPAES_MARKETPLACE_ENABLED=" "$SECRETS"; then
  sudo sed -i "s|^LOJADEPAES_MARKETPLACE_ENABLED=.*|LOJADEPAES_MARKETPLACE_ENABLED=false|" "$SECRETS"
else
  echo "LOJADEPAES_MARKETPLACE_ENABLED=false" | sudo tee -a "$SECRETS" >/dev/null
fi

restore_previous() {
  echo health_fail restoring "${PREV:-$ROLLBACK}"
  if [ -n "${PREV:-}" ]; then
    sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=${PREV}|" .env
    sudo docker compose -f $COMPOSE up -d --force-recreate api || true
  fi
  exit 1
}

rollback_with_downgrade() {
  echo migrate_or_health_fail downgrade_to_c4e8b2a91f70 then "${PREV:-$ROLLBACK}"
  sudo docker compose -f $COMPOSE run --rm --no-deps -T -w /app/database api alembic downgrade c4e8b2a91f70 || true
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
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/m8-health.json \
    && sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/ready >/tmp/m8-ready.json; then
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

echo deploy_m8_done $STAMP
echo expected_revision $REV
echo rollback_image $ROLLBACK
