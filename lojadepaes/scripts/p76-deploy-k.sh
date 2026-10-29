#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
sudo docker load -i /tmp/loja-prod-20261006k.tar
sudo docker image inspect lojadepaes:prod-20261006k >/dev/null
sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261006k/' $INFRA/.env
grep "^LOJADEPAES_API_IMAGE=" $INFRA/.env
cd $INFRA
sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p76-health.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
done
echo FLAGS
sudo docker compose -f $COMPOSE exec -T api python -c 'from app.core.config import get_settings; s=get_settings(); print("public_acc", s.public_accompaniments_enabled); print("gigio_acc", s.gigio_accompaniments_enabled); print("preview", s.accompaniments_preview); print("gigio", s.gigio_enabled); print("payments", s.public_payments_enabled); print("orders", s.public_orders_enabled)'
echo ALEMBIC
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
code=$(curl -sS -o /tmp/p76-acc.json -w "%{http_code}" https://lojadepaes.com.br/api/v1/accompaniments)
echo acc_http $code
python3 - <<'PY'
import json
d=json.load(open("/tmp/p76-acc.json"))
items=d.get("items") or []
print("enabled", d.get("enabled"), "source", d.get("source_status"), "preview", d.get("preview"), "n", len(items))
print("first", (items[0].get("name") if items else "")[:70])
print("last", (items[-1].get("name") if items else "")[:70])
PY
echo HTML
curl -fsS https://lojadepaes.com.br/acompanhar | grep -oE '/assets/index-[A-Za-z0-9]+\.(js|css)' | head
curl -fsS https://lojadepaes.com.br/api/v1/gigio/status
echo
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
