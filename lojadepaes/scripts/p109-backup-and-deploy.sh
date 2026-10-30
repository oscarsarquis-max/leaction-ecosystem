#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE=/tmp/lojadepaes-${STAMP}.sql.gz
IMAGE=lojadepaes:prod-20261030a
ROLLBACK=lojadepaes:prod-20261029d

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

sudo docker load -i /tmp/loja-prod-20261030a.tar
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

sudo docker compose -f $COMPOSE run --rm --no-deps -T -w /app/database api alembic upgrade head
echo alembic_upgraded
sudo docker compose -f $COMPOSE up -d --force-recreate api

i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p109-health.json \
    && sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/ready >/tmp/p109-ready.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
  if [ $i -gt 16 ]; then
    restore_previous
  fi
done
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
sudo docker inspect --format '{{.Image}} {{.Config.Image}} {{.State.StartedAt}}' "$(sudo docker compose -f $COMPOSE ps -q api)"
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
curl -fsS https://lojadepaes.com.br/api/v1/ready
echo

sudo docker compose -f $COMPOSE exec -T -w /app/backend api python - <<'PY'
import json
import urllib.request
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.db.session import get_engine
from app.domain.admin_auth import SESSION_COOKIE, _issue_session
from app.models.admin import AdminSession

settings = get_settings()
db = sessionmaker(bind=get_engine())()
token, _csrf, row = _issue_session(
    db,
    settings,
    username=(settings.admin_username or "leitura").strip() or "leitura",
    client_host="127.0.0.1",
)
session_id = row.id
db.commit()
cookie = f"{SESSION_COOKIE}={token}"

def fetch(path):
    request = urllib.request.Request(
        "http://127.0.0.1:8080" + path,
        headers={"Cookie": cookie},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.load(response)

try:
    status, summary = fetch("/api/v1/admin/ops/attendance-summary")
    lenses = summary.get("queue_lenses") or []
    print("summary", status, "lenses", len(lenses), "keys", ",".join(item.get("key", "") for item in lenses))
    status, listing = fetch("/api/v1/admin/orders?lens=work:needs_action&page_size=1")
    print("needs_action", status, "total", listing.get("total"))
finally:
    cleanup = sessionmaker(bind=get_engine())()
    stored = cleanup.get(AdminSession, session_id)
    if stored is not None:
        cleanup.delete(stored)
    cleanup.commit()
    cleanup.close()
    db.close()
PY

echo deploy_109_done $STAMP
echo rollback_image $ROLLBACK
