#!/usr/bin/env bash
set -eu
INFRA=/opt/lojadepaes/app/infra
COMPOSE=$INFRA/docker-compose.prod.yml
APPENV=/opt/lojadepaes/secrets/app.env
sudo docker load -i /tmp/loja-prod-20261007d.tar
sudo docker image inspect lojadepaes:prod-20261007d >/dev/null
sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261007d/' $INFRA/.env
grep "^LOJADEPAES_API_IMAGE=" $INFRA/.env
sudo grep "^LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED=" $APPENV
sudo grep "^LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED=" $APPENV
cd $INFRA
sudo docker compose -f $COMPOSE up -d --force-recreate api
i=1
while [ $i -le 16 ]; do
  if sudo docker compose -f $COMPOSE exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p80-health.json; then
    echo health_ok $i
    break
  fi
  i=$((i+1))
  sleep 3
done
sudo docker compose -f $COMPOSE exec -T api python -c 'from app.core.config import get_settings; s=get_settings(); print("public_acc", s.public_accompaniments_enabled); print("gigio_acc", s.gigio_accompaniments_enabled); print("rules", "80")'
sudo docker compose -f $COMPOSE exec -T -w /app/database api alembic current
sleep 3
curl -sS -o /tmp/p80-acc.json https://lojadepaes.com.br/api/v1/accompaniments
curl -sS -o /tmp/p80-wine.json "https://lojadepaes.com.br/api/v1/accompaniments?cats=vinhos&mesa=leitao,salada"
curl -sS -o /tmp/p80-status.json https://lojadepaes.com.br/api/v1/gigio/status
python3 - <<'PY'
import json
d=json.load(open("/tmp/p80-acc.json"))
w=json.load(open("/tmp/p80-wine.json"))
s=json.load(open("/tmp/p80-status.json"))
print("generic", d.get("enabled"), d.get("source_status"), "n", len(d.get("items") or []))
print("wine title", w.get("title"), "n", len(w.get("items") or []))
print("wine stories", [(st.get("title"), [i.get("name") for i in st.get("items") or []]) for st in w.get("stories") or []])
print("filters", (w.get("context") or {}).get("filters"))
print("gigio", s.get("enabled"), s.get("rules_version"))
print("noise", [i.get("name") for i in (d.get("items") or []) if any(x in (i.get("name") or "").casefold() for x in ["gravata","3drose","livro","chaveiro","mikasa"])])
print("repeat_header", any((st.get("title") or "") in {i.get("name") for i in st.get("items") or []} for st in w.get("stories") or []))
PY
curl -fsS https://lojadepaes.com.br/acompanhar | grep -oE '/assets/index-[A-Za-z0-9]+\.(js|css)' | head
