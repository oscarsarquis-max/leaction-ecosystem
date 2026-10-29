#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform
echo '=== 95 backup ==='
if [ -f /tmp/p91c-backup-dbs.sh ]; then
  sed -i 's/\r$//' /tmp/p91c-backup-dbs.sh
  bash /tmp/p91c-backup-dbs.sh
elif [ -f scripts/deploy/_prod-backup-dbs.sh ]; then
  bash scripts/deploy/_prod-backup-dbs.sh
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK=/var/lib/leaction-platform/backups/p95-$STAMP
mkdir -p "$BK"
cp -a frontend/action-hub/src/lib/client-branding.ts "$BK/" || true
cp -a frontend/action-hub/src/app/loja/page.tsx "$BK/" || true
cp -a frontend/action-hub/src/app/loja/contratar/page.tsx "$BK/" || true
cp -a frontend/action-hub/src/components/SiteHeader.tsx "$BK/" || true
cp -a frontend/action-hub/src/components/ClientCheckoutHeader.tsx "$BK/" || true
cp -a frontend/action-hub/src/components/CatalogPricingCards.tsx "$BK/" || true
cp -a frontend/action-hub/src/middleware.ts "$BK/" || true
cp -a frontend/action-hub/next.config.ts "$BK/" || true
if [ -f frontend/action-hub/.next/BUILD_ID ]; then
  cp -a frontend/action-hub/.next/BUILD_ID "$BK/BUILD_ID"
fi
echo "rollback_files $BK"

mkdir -p frontend/action-hub/src/lib frontend/action-hub/src/app/loja/contratar frontend/action-hub/src/components
install -m 644 /tmp/p95-client-branding.ts frontend/action-hub/src/lib/client-branding.ts
install -m 644 /tmp/p95-loja-return.ts frontend/action-hub/src/lib/loja-return.ts
install -m 644 /tmp/p95-loja-return.test.mjs frontend/action-hub/src/lib/loja-return.test.mjs
install -m 644 /tmp/p95-loja-page.tsx frontend/action-hub/src/app/loja/page.tsx
install -m 644 /tmp/p95-loja-contratar.tsx frontend/action-hub/src/app/loja/contratar/page.tsx
install -m 644 /tmp/p95-SiteHeader.tsx frontend/action-hub/src/components/SiteHeader.tsx
install -m 644 /tmp/p95-ClientCheckoutHeader.tsx frontend/action-hub/src/components/ClientCheckoutHeader.tsx
install -m 644 /tmp/p95-CatalogPricingCards.tsx frontend/action-hub/src/components/CatalogPricingCards.tsx
install -m 644 /tmp/p95-middleware.ts frontend/action-hub/src/middleware.ts
install -m 644 /tmp/p95-next.config.ts frontend/action-hub/next.config.ts

cd frontend/action-hub
node --test src/lib/loja-return.test.mjs
npm run build
pm2 restart action-hub --update-env
sleep 4
curl -s -o /dev/null -w "hub_fe=%{http_code}\n" http://127.0.0.1:4000/api/health
curl -s -o /dev/null -w "loja_plans=%{http_code}\n" http://127.0.0.1:4000/loja
curl -s -o /dev/null -w "loja_params=%{http_code}\n" "http://127.0.0.1:4000/loja?return_origin=https%3A%2F%2Flojadepaes.com.br&return_to=%2F%23biblioteca"
echo FE_OK
echo "new_build_id $(cat /var/www/leaction-platform/frontend/action-hub/.next/BUILD_ID)"
