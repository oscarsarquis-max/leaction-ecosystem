#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
APPENV=/opt/lojadepaes/secrets/app.env

sudo sed -i 's/^LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED=.*/LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED=true/' $APPENV
sudo grep "^LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_ACCOMPANIMENTS_PREVIEW=" $APPENV

cd $INFRA
sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 12 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p75-health.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
done

echo ACC
code=$(curl -sS -o /tmp/p75-acc.json -w "%{http_code}" https://lojadepaes.com.br/api/v1/accompaniments)
echo acc_http $code
python3 - <<'PY'
import json
d=json.load(open("/tmp/p75-acc.json"))
print("enabled", d.get("enabled"), "source", d.get("source_status"), "preview", d.get("preview"), "items", len(d.get("items") or []), "stories", len(d.get("stories") or []))
for item in (d.get("items") or [])[:12]:
    print("-", item.get("id") or item.get("hub_offer_id"), item.get("title","")[:70])
    print("  ", item.get("outbound_href") or item.get("link"))
    print("   demo", item.get("demo"), "cta", item.get("cta_label"))
PY

echo OPS
curl -fsS https://lojadepaes.com.br/api/v1/operations > /tmp/p75-ops.json
python3 - <<'PY'
import json
d=json.load(open("/tmp/p75-ops.json"))
print("accompaniments_visible", d.get("accompaniments_visible"))
print("keys_ok", "products" in d or "showcase" in d or "calendar" in d)
PY

echo FOR_PRODUCT
curl -sS https://lojadepaes.com.br/api/v1/accompaniments/for-product/pao-fermentacao-natural-de-trigo
echo
echo LOGS
sudo docker compose -f $COMPOSE logs --tail 30 api | grep -E "marketplace|ERROR|Traceback|accompaniment" || true
