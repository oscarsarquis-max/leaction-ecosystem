#!/usr/bin/env bash
# Atualiza só /checkout/seller (cabeçalho) com SELLER_PAYMENTS_ENABLED=false.
set -euo pipefail
cd /var/www/leaction-platform
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK=/var/lib/leaction-platform/backups/p1-loja-seller-$STAMP
mkdir -p "$BK" frontend/action-hub/src/app/checkout/seller
if [ -f frontend/action-hub/src/app/checkout/seller/page.tsx ]; then
  cp -a frontend/action-hub/src/app/checkout/seller/page.tsx "$BK/page.tsx"
fi
if [ -f frontend/action-hub/.next/BUILD_ID ]; then
  cp -a frontend/action-hub/.next/BUILD_ID "$BK/BUILD_ID"
fi
echo "rollback $BK"
install -m 644 /tmp/p1-checkout-seller-page.tsx frontend/action-hub/src/app/checkout/seller/page.tsx
grep -n 'SELLER_PAYMENTS_ENABLED' .env || true
cd frontend/action-hub
npm run build
cd /var/www/leaction-platform
pm2 restart action-hub --update-env
sleep 4
curl -s -o /dev/null -w "hub_fe=%{http_code}\n" http://127.0.0.1:4000/api/health
curl -s -o /dev/null -w "seller_page=%{http_code}\n" 'http://127.0.0.1:4000/checkout/seller?charge=x&t=y'
curl -s -o /dev/null -w "sellers=%{http_code}\n" -X POST http://127.0.0.1:4001/v1/sellers/connect-link -H 'Content-Type: application/json' -d '{}'
echo "new_build_id $(cat frontend/action-hub/.next/BUILD_ID)"
echo P1_LOJA_SELLER_PAGE_OK
