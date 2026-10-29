#!/usr/bin/env bash
set -euo pipefail
# Prompt 75 fase 1 — só plugin Flask do marketplace.

ROOT=/var/www/leaction-platform
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
RB=/var/lib/leaction-platform/rollback-prompt75-${STAMP}
mkdir -p "$RB/backend/app/services" "$RB/backend/app/api" "$RB/backend/app/database"

backup() {
  local rel="$1"
  if [ -f "$ROOT/$rel" ]; then
    mkdir -p "$RB/$(dirname "$rel")"
    cp -a "$ROOT/$rel" "$RB/$rel"
  fi
}

backup backend/app/__init__.py
backup backend/app/api/marketplace_routes.py
backup backend/app/database/seed.py
backup backend/app/services/amazon_service.py
backup backend/app/services/contextual_vitrine.py
backup backend/app/services/curation_repository.py
backup backend/app/services/mercadolivre_fallback.py
backup backend/app/services/multivendor_orchestrator.py
echo "$RB" > /tmp/p75-rollback-dir
echo "rollback_dir $RB"

install_file() {
  local src="$1" dest="$2"
  sed -i 's/\r$//' "$src"
  install -m 644 "$src" "$dest"
}

install_file /tmp/p75/origin_profiles.py "$ROOT/backend/app/services/origin_profiles.py"
install_file /tmp/p75/__init__.py "$ROOT/backend/app/__init__.py"
install_file /tmp/p75/marketplace_routes.py "$ROOT/backend/app/api/marketplace_routes.py"
install_file /tmp/p75/seed.py "$ROOT/backend/app/database/seed.py"
install_file /tmp/p75/amazon_service.py "$ROOT/backend/app/services/amazon_service.py"
install_file /tmp/p75/contextual_vitrine.py "$ROOT/backend/app/services/contextual_vitrine.py"
install_file /tmp/p75/curation_repository.py "$ROOT/backend/app/services/curation_repository.py"
install_file /tmp/p75/mercadolivre_fallback.py "$ROOT/backend/app/services/mercadolivre_fallback.py"
install_file /tmp/p75/multivendor_orchestrator.py "$ROOT/backend/app/services/multivendor_orchestrator.py"

pm2 restart marketplace-api --update-env
sleep 4
curl -fsS --max-time 8 http://127.0.0.1:4012/api/marketplace/health >/tmp/p75-mkt-health.json
python3 - <<'PY'
import json
from pathlib import Path
p = json.loads(Path("/tmp/p75-mkt-health.json").read_text())
assert p.get("status") == "ok", p
print("marketplace_health_ok")
PY
echo "flask_done $STAMP"
