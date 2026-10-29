#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform
pm2 restart gateway-api --update-env
sleep 3
curl -s -o /dev/null -w "hub_health=%{http_code}\n" http://127.0.0.1:4001/health
curl -s -o /dev/null -w "subs=%{http_code}\n" "http://127.0.0.1:4001/v1/subscriptions"
curl -s -o /dev/null -w "credits=%{http_code}\n" -X POST http://127.0.0.1:4001/v1/credits/reserve -H 'Content-Type: application/json' -d '{}'
install -m 644 /tmp/p91d-dashboard-page.tsx frontend/action-hub/src/app/dashboard/page.tsx
cd frontend/action-hub
npm run build
pm2 restart action-hub --update-env
sleep 4
curl -s -o /dev/null -w "hub_fe=%{http_code}\n" http://127.0.0.1:4000/api/health
echo FE_OK
