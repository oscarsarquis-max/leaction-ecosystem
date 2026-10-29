#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz
IMAGE=lojadepaes:prod-20261024b

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

sudo docker load -i /tmp/loja-prod-20261024b.tar
sudo docker image inspect $IMAGE >/dev/null
echo image_loaded

if grep -q "^LOJADEPAES_API_IMAGE=" $INFRA/.env; then
  sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261024b/' $INFRA/.env
else
  echo LOJADEPAES_API_IMAGE=lojadepaes:prod-20261024b >> $INFRA/.env
fi
grep "^LOJADEPAES_API_IMAGE=" $INFRA/.env

sudo docker compose -f $COMPOSE run --rm --no-deps -T -w /app/database api alembic upgrade head
echo alembic_upgraded

sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p102a-health.json; then
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

sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
echo deploy_102a_done $STAMP
echo rollback_image lojadepaes:prod-20261024a
