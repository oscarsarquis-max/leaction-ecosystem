#!/usr/bin/env bash
set -euo pipefail
# Prompt 75 — só contrato de perfil do marketplace. Não toca gateway, pagamento nem tema.

ROOT=/var/www/leaction-platform
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
RB=/var/lib/leaction-platform/rollback-prompt75-${STAMP}
mkdir -p "$RB/backend" "$RB/frontend"

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
backup frontend/action-hub/src/app/marketplace-api/vitrine/route.ts
backup frontend/action-hub/src/app/marketplace-api/offers/route.ts
if [ -f "$ROOT/frontend/action-hub/.next/BUILD_ID" ]; then
  cp -a "$ROOT/frontend/action-hub/.next/BUILD_ID" "$RB/BUILD_ID"
fi
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
install_file /tmp/p75/vitrine.route.ts "$ROOT/frontend/action-hub/src/app/marketplace-api/vitrine/route.ts"
install_file /tmp/p75/offers.route.ts "$ROOT/frontend/action-hub/src/app/marketplace-api/offers/route.ts"

echo "files_installed"
pm2 restart marketplace-api --update-env
sleep 3
curl -fsS --max-time 8 http://127.0.0.1:4012/api/marketplace/health >/tmp/p75-mkt-health.json
echo "marketplace_health_ok"

# Rebuild só do frontend Action Hub (rotas do proxy). Sem npm ci.
cd "$ROOT/frontend/action-hub"
if [ ! -f .env.production ]; then
  echo "ERRO: .env.production ausente" >&2
  exit 1
fi
npm run build
cd "$ROOT"
pm2 restart action-hub --update-env
sleep 2
echo "action_hub_restarted"
echo "new_build_id $(cat $ROOT/frontend/action-hub/.next/BUILD_ID)"
echo "done $STAMP"
