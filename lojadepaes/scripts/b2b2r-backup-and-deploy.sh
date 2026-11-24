#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz
IMAGE=lojadepaes:prod-20261124d
ROLLBACK=lojadepaes:prod-20261124c

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

sudo docker load -i /tmp/loja-prod-20261124d.tar
sudo docker image inspect $IMAGE >/dev/null
echo image_loaded

if grep -q "^LOJADEPAES_API_IMAGE=" .env; then
  sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=${IMAGE}|" .env
else
  echo "LOJADEPAES_API_IMAGE=${IMAGE}" >> .env
fi

restore_previous() {
  echo health_fail restoring "${PREV:-$ROLLBACK}"
  if [ -n "${PREV:-}" ]; then
    sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=${PREV}|" .env
    sudo docker compose -f $COMPOSE up -d --force-recreate api || true
  fi
  exit 1
}

echo "B2B2R: sem migracao"
sudo docker compose -f $COMPOSE up -d --force-recreate api

i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/b2b2r-health.json \
    && sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/ready >/tmp/b2b2r-ready.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
  if [ $i -gt 16 ]; then
    restore_previous
  fi
done
sudo docker inspect --format '{{.Image}} {{.Config.Image}} {{.State.StartedAt}}' "$(sudo docker compose -f $COMPOSE ps -q api)"
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
curl -fsS https://lojadepaes.com.br/api/v1/ready
echo

echo deploy_b2b2r_done $STAMP
echo rollback_image $ROLLBACK
