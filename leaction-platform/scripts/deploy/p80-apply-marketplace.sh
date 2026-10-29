#!/usr/bin/env bash
set -eu
ROOT=/var/www/leaction-platform
RB=/var/lib/leaction-platform/rollback-prompt80-$(date -u +%Y%m%dT%H%M%SZ)
sudo mkdir -p "$RB/backend/app/services"
for rel in \
  backend/app/services/offer_relevance.py \
  backend/app/services/mercadolivre_service.py
do
  if [ -f "$ROOT/$rel" ]; then
    sudo cp -a "$ROOT/$rel" "$RB/$rel"
  fi
done
echo rollback $RB
SRC=/tmp/p80-hub
sudo cp -a "$SRC/offer_relevance.py" "$ROOT/backend/app/services/offer_relevance.py"
sudo cp -a "$SRC/mercadolivre_service.py" "$ROOT/backend/app/services/mercadolivre_service.py"
pm2 restart marketplace-api
sleep 4
curl -sS -o /tmp/p80-health.json -w "health %{http_code}\n" http://127.0.0.1:4012/api/marketplace/health
curl -sS -o /tmp/p80-vitrine.json -w "vitrine %{http_code}\n" -H "X-ActionHub-App-Id: lojadepaes" "http://127.0.0.1:4012/api/marketplace/vitrine?limit=8&origin=lojadepaes"
python3 - <<'PY'
import json
d=json.load(open("/tmp/p80-vitrine.json"))
print("origin", d.get("origin"))
for shelf in d.get("shelves") or []:
    print("SHELF", shelf.get("category"), "n", len(shelf.get("offers") or []))
    for o in shelf.get("offers") or []:
        print("  -", (o.get("title") or "")[:90])
PY
