#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform
echo '=== 91G backup ==='
if [ -f /tmp/p91c-backup-dbs.sh ]; then
  sed -i 's/\r$//' /tmp/p91c-backup-dbs.sh
  bash /tmp/p91c-backup-dbs.sh
elif [ -f scripts/deploy/_prod-backup-dbs.sh ]; then
  bash scripts/deploy/_prod-backup-dbs.sh
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK=/var/lib/leaction-platform/backups/p91g-$STAMP
mkdir -p "$BK"
cp -a services/gateway-api/domain/credits-ops.js "$BK/" || true
cp -a services/gateway-api/domain/credits-ops.test.js "$BK/" || true
cp -a services/gateway-api/domain/entitlements-api.js "$BK/" || true
cp -a services/gateway-api/domain/catalog-subscription.js "$BK/" || true
cp -a services/gateway-api/domain/catalog-subscription.test.js "$BK/" || true
cp -a frontend/action-hub/src/components/CatalogPricingCards.tsx "$BK/" || true
echo "rollback_files $BK"

install -m 644 /tmp/p91g-credits-ops.js services/gateway-api/domain/credits-ops.js
install -m 644 /tmp/p91g-credits-ops.test.js services/gateway-api/domain/credits-ops.test.js
install -m 644 /tmp/p91g-entitlements-api.js services/gateway-api/domain/entitlements-api.js
install -m 644 /tmp/p91g-catalog-subscription.js services/gateway-api/domain/catalog-subscription.js
install -m 644 /tmp/p91g-catalog-subscription.test.js services/gateway-api/domain/catalog-subscription.test.js
mkdir -p frontend/action-hub/src/components frontend/action-hub/src/app/loja/contratar
install -m 644 /tmp/p91g-CatalogPricingCards.tsx frontend/action-hub/src/components/CatalogPricingCards.tsx
install -m 644 /tmp/p91g-loja-page.tsx frontend/action-hub/src/app/loja/page.tsx
install -m 644 /tmp/p91g-loja-contratar.tsx frontend/action-hub/src/app/loja/contratar/page.tsx

cd services/gateway-api
node --test domain/credits-ops.test.js domain/catalog-subscription.test.js
cd /var/www/leaction-platform

pm2 restart gateway-api --update-env
sleep 3
curl -s -o /dev/null -w "hub_health=%{http_code}\n" http://127.0.0.1:4001/health
curl -s -o /dev/null -w "catalog=%{http_code}\n" http://127.0.0.1:4001/v1/catalog/lojadepaes

cd frontend/action-hub
npm run build
pm2 restart action-hub --update-env
sleep 4
curl -s -o /dev/null -w "hub_fe=%{http_code}\n" http://127.0.0.1:4000/api/health
curl -s -o /dev/null -w "loja_plans=%{http_code}\n" http://127.0.0.1:4000/loja
echo FE_OK
