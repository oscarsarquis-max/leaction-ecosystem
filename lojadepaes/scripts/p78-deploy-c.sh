#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
APPENV=/opt/lojadepaes/secrets/app.env
sudo docker load -i /tmp/loja-prod-20261007c.tar
sudo docker image inspect lojadepaes:prod-20261007c >/dev/null
sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007c/' $INFRA/.env
grep "^LOJADEPAES_API_IMAGE=" $INFRA/.env
sudo grep "^LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=" $APPENV
cd $INFRA
sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p78-health.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
done
sudo docker compose -f $COMPOSE exec -T api python -c 'from app.core.config import get_settings; s=get_settings(); print("public_acc", s.public_accompaniments_enabled); print("gigio_acc", s.gigio_accompaniments_enabled)'
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
sleep 3
curl -sS -o /tmp/p78-acc.json https://lojadepaes.com.br/api/v1/accompaniments
curl -sS -o /tmp/p78-wine.json "https://lojadepaes.com.br/api/v1/accompaniments?cats=vinhos"
curl -sS -o /tmp/p78-cold.json "https://lojadepaes.com.br/api/v1/accompaniments?cats=frios"
python3 - <<'PY'
import json
def load(p):
    return json.load(open(p))
d=load("/tmp/p78-acc.json"); w=load("/tmp/p78-wine.json"); c=load("/tmp/p78-cold.json")
print("generic", d.get("enabled"), d.get("source_status"), "n", len(d.get("items") or []))
print("wine n", len(w.get("items") or []), [i.get("name","")[:50] for i in (w.get("items") or [])])
print("frios n", len(c.get("items") or []), [i.get("name","")[:50] for i in (c.get("items") or [])])
print("noise", [i.get("name") for i in (d.get("items") or []) if any(x in (i.get("name") or "").casefold() for x in ["gravata","3drose","livro","chaveiro","mikasa"])])
PY
curl -fsS https://lojadepaes.com.br/acompanhar | grep -oE '/assets/index-[A-Za-z0-9]+\.(js|css)' | head
