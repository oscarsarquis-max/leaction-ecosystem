#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
APPENV=/opt/lojadepaes/secrets/app.env
sudo docker load -i /tmp/loja-prod-20261007a.tar
sudo docker image inspect lojadepaes:prod-20261007a >/dev/null
sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007a/' $INFRA/.env
grep "^LOJADEPAES_API_IMAGE=" $INFRA/.env
sudo grep "^LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=" $APPENV
cd $INFRA
sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p77-health.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
done
echo FLAGS
sudo docker compose -f $COMPOSE exec -T api python -c 'from app.core.config import get_settings; s=get_settings(); print("public_acc", s.public_accompaniments_enabled); print("gigio_acc", s.gigio_accompaniments_enabled); print("preview", s.accompaniments_preview); print("gigio", s.gigio_enabled)'
echo ALEMBIC
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
curl -sS -o /tmp/p77-acc.json -w "acc_http %{http_code}\n" https://lojadepaes.com.br/api/v1/accompaniments
curl -sS -o /tmp/p77-wine.json -w "wine_http %{http_code}\n" "https://lojadepaes.com.br/api/v1/accompaniments?cats=vinhos"
python3 - <<'PY'
import json
d=json.load(open("/tmp/p77-acc.json"))
w=json.load(open("/tmp/p77-wine.json"))
print("generic", d.get("enabled"), d.get("source_status"), "n", len(d.get("items") or []))
print("delivery", (d.get("delivery_help") or {}).get("text"))
print("wine_ctx", (w.get("context") or {}), "n", len(w.get("items") or []))
print("wine_names", [i.get("name","")[:40] for i in (w.get("items") or [])[:8]])
PY
curl -fsS https://lojadepaes.com.br/acompanhar | grep -oE '/assets/index-[A-Za-z0-9]+\.(js|css)' | head
curl -fsS https://lojadepaes.com.br/api/v1/gigio/status
echo
