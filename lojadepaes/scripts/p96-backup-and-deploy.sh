#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz
IMAGE=lojadepaes:prod-20261009a

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

sudo docker load -i /tmp/loja-prod-20261009a.tar
sudo docker image inspect $IMAGE >/dev/null
echo image_loaded

if grep -q "^LOJADEPAES_API_IMAGE=" $INFRA/.env; then
  sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261009a/' $INFRA/.env
else
  echo LOJADEPAES_API_IMAGE=lojadepaes:prod-20261009a >> $INFRA/.env
fi
grep "^LOJADEPAES_API_IMAGE=" $INFRA/.env

sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p96-health.json; then
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

sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic upgrade head
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
sudo docker compose -f $COMPOSE exec -T api python -c 'from datetime import date; from sqlalchemy.orm import sessionmaker; from app.core.config import get_settings; from app.db.session import get_engine; from app.domain.admin_auth import actor_ref_for; from app.domain.schedule_closures import ensure_authorized_closure, serialize_closure, commitments_in_range; s=get_settings(); db=sessionmaker(bind=get_engine(), expire_on_commit=False)(); row=ensure_authorized_closure(db,s,start_date=date(2026,10,10),end_date=date(2026,10,18),first_eligible_date=date(2026,10,21),pause_intake=False,internal_reason="Viagem",actor_ref=actor_ref_for(s.admin_username.strip() or "desconhecido")); db.commit(); p=serialize_closure(db,s,row); c=commitments_in_range(db,date(2026,10,10),date(2026,10,20)); print("closure", p["id"], p["status"], p["blocked_until"], p["pause_intake"], p["created_by"], "orders", c["order_count"], "requests", c["date_request_count"]); db.close()'
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
curl -fsS -X POST https://lojadepaes.com.br/api/v1/schedule/preview -H "Content-Type: application/json" -d '{"start":"2026-10-10","end":"2026-10-24"}'
echo
echo deploy_96_done $STAMP
echo rollback_image lojadepaes:prod-20261008g
