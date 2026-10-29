#!/usr/bin/env bash
set -euo pipefail
APP=/var/www/leaction-platform/frontend/action-hub
install -m 644 /tmp/PaymentsOps.tsx "$APP/src/components/admin/PaymentsOps.tsx"
install -m 644 /tmp/admin-api.ts "$APP/src/lib/admin-api.ts"
cd "$APP"
grep -n "Cobrado\|Pago\|charged_amount_cents" src/components/admin/PaymentsOps.tsx | head -8
echo "==> next build"
npm run build
echo "==> restart action-hub"
pm2 restart action-hub --update-env
sleep 5
curl -s -o /dev/null -w "hub_fe_health=%{http_code}\n" http://127.0.0.1:4000/api/health
pm2 describe action-hub | sed -n '1,20p'
test -f "$APP/.next/BUILD_ID" && echo "BUILD_ID=$(cat "$APP/.next/BUILD_ID")"
echo FE_PUBLISH_OK
