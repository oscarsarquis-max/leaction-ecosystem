#!/usr/bin/env bash
set -eu
ROOT=/var/www/leaction-platform
RB=/var/lib/leaction-platform/rollback-prompt86-$(date -u +%Y%m%dT%H%M%SZ)
sudo mkdir -p "$RB/backend/app/services" "$RB/backend/app/database"
for rel in \
  backend/app/services/origin_profiles.py \
  backend/app/services/offer_relevance.py \
  backend/app/services/mercadolivre_service.py \
  backend/app/services/multivendor_orchestrator.py \
  backend/app/services/amazon_service.py \
  backend/app/services/curation_repository.py \
  backend/app/database/seed.py
do
  if [ -f "$ROOT/$rel" ]; then
    sudo mkdir -p "$RB/$(dirname "$rel")"
    sudo cp -a "$ROOT/$rel" "$RB/$rel"
  fi
done
echo rollback $RB
SRC=/tmp/p86-hub
sudo cp -a "$SRC/origin_profiles.py" "$ROOT/backend/app/services/origin_profiles.py"
sudo cp -a "$SRC/offer_relevance.py" "$ROOT/backend/app/services/offer_relevance.py"
sudo cp -a "$SRC/mercadolivre_service.py" "$ROOT/backend/app/services/mercadolivre_service.py"
sudo cp -a "$SRC/multivendor_orchestrator.py" "$ROOT/backend/app/services/multivendor_orchestrator.py"
sudo cp -a "$SRC/amazon_service.py" "$ROOT/backend/app/services/amazon_service.py"
sudo cp -a "$SRC/curation_repository.py" "$ROOT/backend/app/services/curation_repository.py"
sudo cp -a "$SRC/seed.py" "$ROOT/backend/app/database/seed.py"
pm2 restart marketplace-api
sleep 6
curl -sS -o /tmp/p86-health.json -w "health %{http_code}\n" http://127.0.0.1:4012/api/marketplace/health
curl -sS -o /tmp/p86-vitrine.json -w "vitrine %{http_code}\n" -H "X-ActionHub-App-Id: lojadepaes" "http://127.0.0.1:4012/api/marketplace/vitrine?limit=8&origin=lojadepaes"
python3 - <<'PY'
import json
d=json.load(open("/tmp/p86-vitrine.json"))
print("origin", d.get("origin"))
print("used_fallback", d.get("used_fallback"))
for shelf in d.get("shelves") or []:
    offers = shelf.get("offers") or []
    print("SHELF", shelf.get("category"), "n", len(offers))
    for o in offers[:4]:
        print("  -", (o.get("title") or "")[:90], "verified", o.get("availability_verified"), "src", o.get("availability_source") or "-")
PY
