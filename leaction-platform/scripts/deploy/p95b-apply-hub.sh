#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform
echo '=== 95B backup ==='
if [ -f /tmp/p91c-backup-dbs.sh ]; then
  sed -i 's/\r$//' /tmp/p91c-backup-dbs.sh
  bash /tmp/p91c-backup-dbs.sh
elif [ -f scripts/deploy/_prod-backup-dbs.sh ]; then
  bash scripts/deploy/_prod-backup-dbs.sh
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK=/var/lib/leaction-platform/backups/p95b-$STAMP
mkdir -p "$BK"
for f in \
  frontend/action-hub/src/lib/client-branding.ts \
  frontend/action-hub/src/lib/catalog-api.ts \
  frontend/action-hub/src/components/ClientCheckoutHeader.tsx \
  frontend/action-hub/src/components/CheckoutChrome.tsx \
  frontend/action-hub/src/components/MercadoPagoSubscriptionBrick.tsx \
  frontend/action-hub/src/app/loja/page.tsx \
  frontend/action-hub/src/app/loja/contratar/page.tsx \
  frontend/action-hub/src/app/dashboard/page.tsx
do
  if [ -f "$f" ]; then
    mkdir -p "$BK/$(dirname "$f")"
    cp -a "$f" "$BK/$f"
  fi
done
if [ -f frontend/action-hub/.next/BUILD_ID ]; then
  cp -a frontend/action-hub/.next/BUILD_ID "$BK/BUILD_ID"
fi
echo "rollback_files $BK"

install -m 644 /tmp/p95b-loja-checkout-copy.ts frontend/action-hub/src/lib/loja-checkout-copy.ts
install -m 644 /tmp/p95b-loja-checkout-copy.test.mjs frontend/action-hub/src/lib/loja-checkout-copy.test.mjs
install -m 644 /tmp/p95b-client-branding.ts frontend/action-hub/src/lib/client-branding.ts
install -m 644 /tmp/p95b-catalog-api.ts frontend/action-hub/src/lib/catalog-api.ts
install -m 644 /tmp/p95b-ClientCheckoutHeader.tsx frontend/action-hub/src/components/ClientCheckoutHeader.tsx
install -m 644 /tmp/p95b-CheckoutChrome.tsx frontend/action-hub/src/components/CheckoutChrome.tsx
install -m 644 /tmp/p95b-MercadoPagoSubscriptionBrick.tsx frontend/action-hub/src/components/MercadoPagoSubscriptionBrick.tsx
install -m 644 /tmp/p95b-loja-page.tsx frontend/action-hub/src/app/loja/page.tsx
install -m 644 /tmp/p95b-loja-contratar.tsx frontend/action-hub/src/app/loja/contratar/page.tsx
install -m 644 /tmp/p95b-dashboard.tsx frontend/action-hub/src/app/dashboard/page.tsx

cd frontend/action-hub
node --test src/lib/loja-checkout-copy.test.mjs src/lib/loja-brand-asset.test.mjs
npm run build
pm2 restart action-hub --update-env
sleep 4
curl -s -o /dev/null -w "hub_fe=%{http_code}\n" http://127.0.0.1:4000/api/health
curl -s -o /dev/null -w "loja_plans=%{http_code}\n" http://127.0.0.1:4000/loja
curl -s -o /dev/null -w "loja_contratar=%{http_code}\n" http://127.0.0.1:4000/loja/contratar
echo FE_OK
echo "new_build_id $(cat /var/www/leaction-platform/frontend/action-hub/.next/BUILD_ID)"
