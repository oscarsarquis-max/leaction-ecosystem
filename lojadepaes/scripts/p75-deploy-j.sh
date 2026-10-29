#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
sudo docker load -i /tmp/loja-prod-20261006j.tar
sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261006j/' $INFRA/.env
grep "^LOJADEPAES_API_IMAGE=" $INFRA/.env
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
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
code=$(curl -sS -o /tmp/p75-acc.json -w "%{http_code}" https://lojadepaes.com.br/api/v1/accompaniments)
echo acc_http $code
python3 - <<'PY'
import json
d=json.load(open("/tmp/p75-acc.json"))
items=d.get("items") or []
print("enabled", d.get("enabled"), "source", d.get("source_status"), "preview", d.get("preview"), "n", len(items))
with_img=sum(1 for i in items if i.get("image_url"))
print("with_image", with_img)
for item in items[:8]:
    print("-", item.get("hub_offer_id"), item.get("name","")[:70])
    print("  img", (item.get("image_url") or "")[:90])
    print("  href", item.get("outbound_href"))
    print("  cta", item.get("outbound_label"), "demo", item.get("demo"))
PY
curl -fsS https://lojadepaes.com.br/api/v1/gigio/status
echo
curl -fsS https://lojadepaes.com.br/api/v1/health
echo
