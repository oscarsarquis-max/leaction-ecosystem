#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform
echo '=== 91D backup ==='
if [ -f /tmp/p91c-backup-dbs.sh ]; then
  sed -i 's/\r$//' /tmp/p91c-backup-dbs.sh
  bash /tmp/p91c-backup-dbs.sh
elif [ -f scripts/deploy/_prod-backup-dbs.sh ]; then
  bash scripts/deploy/_prod-backup-dbs.sh
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK=/var/lib/leaction-platform/backups/p91d-$STAMP
mkdir -p "$BK"
cp -a services/gateway-api/domain/catalog-public.js "$BK/" || true
cp -a services/gateway-api/domain/checkout-sessions.js "$BK/" || true
cp -a services/gateway-api/domain/mp-webhooks.js "$BK/" || true
cp -a services/gateway-api/domain/mercadopago.js "$BK/" 2>/dev/null || true
cp -a services/gateway-api/mercadopago.js "$BK/" || true
cp -a services/gateway-api/server.js "$BK/" || true
echo "rollback_files $BK"

install -m 644 /tmp/p91d-catalog-subscription.js services/gateway-api/domain/catalog-subscription.js
install -m 644 /tmp/p91d-catalog-subscription.test.js services/gateway-api/domain/catalog-subscription.test.js
install -m 644 /tmp/p91d-catalog-public.js services/gateway-api/domain/catalog-public.js
install -m 644 /tmp/p91d-checkout-sessions.js services/gateway-api/domain/checkout-sessions.js
install -m 644 /tmp/p91d-mp-webhooks.js services/gateway-api/domain/mp-webhooks.js
install -m 644 /tmp/p91d-mercadopago.js services/gateway-api/mercadopago.js
install -m 644 /tmp/p91d-server.js services/gateway-api/server.js
install -m 644 /tmp/p91d-credits-ops.js services/gateway-api/domain/credits-ops.js
mkdir -p shared/database
install -m 644 /tmp/p91d-patch-subscription-cycles.sql shared/database/patch_subscription_cycles.sql

python3 - <<'PY'
from pathlib import Path
text = Path('services/gateway-api/server.js').read_text()
print('server_has_sub_routes', 'registerCatalogSubscriptionRoutes' in text)
print('mp_has_authorized', 'fetchAuthorizedPayment' in Path('services/gateway-api/mercadopago.js').read_text())
PY

cd services/gateway-api
node --test domain/catalog-subscription.test.js domain/credits-ops.test.js
cd /var/www/leaction-platform

# apply table via gateway later; also try psql if DATABASE_URL works
(cd services/gateway-api && node -e "const {Pool}=require('pg');require('dotenv').config({path:'../../.env',override:true});const p=new Pool({connectionString:process.env.DATABASE_URL,ssl:{rejectUnauthorized:false}});const fs=require('fs');p.query(fs.readFileSync('../../shared/database/patch_subscription_cycles.sql','utf8')).then(()=>{console.log('cycles_table=ok');return p.end();}).catch(e=>{console.error('cycles_table',e.message);process.exit(1);})")

pm2 restart gateway-api --update-env
sleep 3
curl -s -o /dev/null -w "hub_health=%{http_code}\n" http://127.0.0.1:4001/health
curl -s -o /dev/null -w "subs_no_auth=%{http_code}\n" http://127.0.0.1:4001/v1/subscriptions

install -m 644 /tmp/p91d-dashboard-page.tsx frontend/action-hub/src/app/dashboard/page.tsx
cd frontend/action-hub
npm run build
pm2 restart action-hub --update-env
sleep 4
curl -s -o /dev/null -w "hub_fe=%{http_code}\n" http://127.0.0.1:4000/api/health
echo FE_OK
