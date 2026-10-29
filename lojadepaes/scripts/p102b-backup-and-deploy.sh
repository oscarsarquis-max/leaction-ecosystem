#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz
IMAGE=lojadepaes:prod-20261024c

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

sudo docker load -i /tmp/loja-prod-20261024c.tar
sudo docker image inspect $IMAGE >/dev/null
echo image_loaded

if grep -q "^LOJADEPAES_API_IMAGE=" $INFRA/.env; then
  sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=${IMAGE}|" $INFRA/.env
else
  echo "LOJADEPAES_API_IMAGE=${IMAGE}" >> $INFRA/.env
fi

sudo docker compose -f $COMPOSE run --rm --no-deps -T -w /app/database api alembic upgrade head
echo alembic_upgraded
sudo docker compose -f $COMPOSE up -d --force-recreate api

if grep -q "^LOJADEPAES_VAPID_PUBLIC_KEY=." $INFRA/.env; then
  echo vapid_present
else
  cid=$(sudo docker compose -f $COMPOSE ps -q api)
  sudo docker cp /tmp/p102b-vapid.py "$cid":/tmp/p102b-vapid.py
  sudo docker compose -f $COMPOSE exec -T api python /tmp/p102b-vapid.py > /tmp/vapid.snippet
  sudo tee -a $INFRA/.env < /tmp/vapid.snippet >/dev/null
  sudo rm -f /tmp/vapid.snippet
  echo vapid_created
  sudo docker compose -f $COMPOSE up -d --force-recreate api
fi

i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p102b-health.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
  if [ $i -gt 16 ]; then
    echo health_fail
    exit 1
  fi
done
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
echo deploy_102b_done $STAMP
echo rollback_image lojadepaes:prod-20261024b
