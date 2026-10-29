#!/usr/bin/env bash
set -eu
ROOT=/var/www/leaction-platform
RB=/var/lib/leaction-platform/rollback-prompt78-$(date -u +%Y%m%dT%H%M%SZ)
sudo mkdir -p "$RB/backend/app/services" "$RB/backend/app/database" "$RB/backend/app/api"
for rel in \
  backend/app/__init__.py \
  backend/app/services/multivendor_orchestrator.py \
  backend/app/services/mercadolivre_service.py \
  backend/app/services/amazon_service.py \
  backend/app/services/marketplace_resilience.py \
  backend/app/database/models.py \
  backend/app/database/seed.py \
  backend/app/api/marketplace_routes.py \
  backend/app/api/curation_routes.py
do
  if [ -f "$ROOT/$rel" ]; then
    sudo cp -a "$ROOT/$rel" "$RB/$rel"
  fi
done
echo rollback $RB
SRC=/tmp/p78-hub
sudo cp -a "$SRC/offer_relevance.py" "$ROOT/backend/app/services/offer_relevance.py"
sudo cp -a "$SRC/offer_decisions.py" "$ROOT/backend/app/services/offer_decisions.py"
sudo cp -a "$SRC/multivendor_orchestrator.py" "$ROOT/backend/app/services/multivendor_orchestrator.py"
sudo cp -a "$SRC/mercadolivre_service.py" "$ROOT/backend/app/services/mercadolivre_service.py"
sudo cp -a "$SRC/amazon_service.py" "$ROOT/backend/app/services/amazon_service.py"
sudo cp -a "$SRC/marketplace_resilience.py" "$ROOT/backend/app/services/marketplace_resilience.py"
sudo cp -a "$SRC/models.py" "$ROOT/backend/app/database/models.py"
sudo cp -a "$SRC/seed.py" "$ROOT/backend/app/database/seed.py"
sudo cp -a "$SRC/marketplace_routes.py" "$ROOT/backend/app/api/marketplace_routes.py"
sudo cp -a "$SRC/curation_routes.py" "$ROOT/backend/app/api/curation_routes.py"
sudo cp -a "$SRC/__init__.py" "$ROOT/backend/app/__init__.py"
pm2 restart marketplace-api
sleep 4
curl -sS -o /tmp/p78-health.json -w "health %{http_code}\n" http://127.0.0.1:4012/api/marketplace/health
curl -sS -o /tmp/p78-vitrine.json -w "vitrine %{http_code}\n" -H "X-ActionHub-App-Id: lojadepaes" "http://127.0.0.1:4012/api/marketplace/vitrine?limit=8&origin=lojadepaes"
python3 - <<'PY'
import json
d=json.load(open("/tmp/p78-vitrine.json"))
print("origin", d.get("origin"))
for shelf in d.get("shelves") or []:
    print("SHELF", shelf.get("category"), "n", len(shelf.get("offers") or []))
    for o in shelf.get("offers") or []:
        print("  -", (o.get("title") or "")[:90])
PY
