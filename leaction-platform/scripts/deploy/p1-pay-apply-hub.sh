#!/usr/bin/env bash
# P1-Pay: módulo sellers desligado (SELLER_PAYMENTS_ENABLED=false). Aditivo.
set -euo pipefail
cd /var/www/leaction-platform

echo '=== P1-Pay backup dbs ==='
if [ -f /tmp/p91c-backup-dbs.sh ]; then
  sed -i 's/\r$//' /tmp/p91c-backup-dbs.sh
  bash /tmp/p91c-backup-dbs.sh
elif [ -f scripts/deploy/_prod-backup-dbs.sh ]; then
  bash scripts/deploy/_prod-backup-dbs.sh
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK=/var/lib/leaction-platform/backups/p1-pay-$STAMP
mkdir -p "$BK"
cp -a services/gateway-api/server.js "$BK/server.js"
if [ -f frontend/action-hub/.next/BUILD_ID ]; then
  cp -a frontend/action-hub/.next/BUILD_ID "$BK/BUILD_ID"
fi
cp -a .env "$BK/env" 2>/dev/null || true
echo "rollback_files $BK"

mkdir -p services/gateway-api/lib services/gateway-api/domain shared/database
mkdir -p frontend/action-hub/src/app/checkout/seller

install -m 644 /tmp/p1-seller-crypto.js services/gateway-api/lib/seller-crypto.js
install -m 644 /tmp/p1-sellers-oauth.js services/gateway-api/domain/sellers-oauth.js
install -m 644 /tmp/p1-seller-charges.js services/gateway-api/domain/seller-charges.js
install -m 644 /tmp/p1-sellers-pay.test.js services/gateway-api/domain/sellers-pay.test.js
install -m 644 /tmp/p1-patch_seller_payments.sql shared/database/patch_seller_payments.sql
install -m 644 /tmp/p1-checkout-seller-page.tsx frontend/action-hub/src/app/checkout/seller/page.tsx

# Uma linha em server.js (idempotente)
if ! grep -q "registerSellerRoutes" services/gateway-api/server.js; then
  sed -i "/registerAmountCheckoutRoutes(app, pool);/a require('./domain/sellers-oauth').registerSellerRoutes(app, pool);" \
    services/gateway-api/server.js
fi
grep -n "registerSellerRoutes\|registerAmountCheckoutRoutes\|registerSpiderPayLookup" services/gateway-api/server.js | head -20

# Flag desligada + apps (sem secrets MP_CLIENT_* / SELLER_TOKEN_* neste passo)
ENV_FILE=/var/www/leaction-platform/.env
touch "$ENV_FILE"
set_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    printf '\n%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}
set_env SELLER_PAYMENTS_ENABLED false
set_env SELLER_APP_IDS lojadepaes
set_env MP_SELLER_REDIRECT_URI 'https://api.actionhub.com.br/v1/sellers/oauth/callback'
grep -E '^(SELLER_PAYMENTS_ENABLED|SELLER_APP_IDS|MP_SELLER_REDIRECT_URI)=' "$ENV_FILE" || true

echo '=== migrate seller tables ==='
(cd services/gateway-api && NODE_TLS_REJECT_UNAUTHORIZED=0 node -e "
const {Pool}=require('pg');
require('dotenv').config({path:'../../.env',override:true});
const fs=require('fs');
let url=String(process.env.DATABASE_URL||'');
url=url.replace(/([?&])sslmode=[^&]*/g,'\$1').replace(/[?&]$/,'').replace(/\?&/,'?');
const p=new Pool({connectionString:url,ssl:{rejectUnauthorized:false}});
const sql=fs.readFileSync('../../shared/database/patch_seller_payments.sql','utf8');
p.query(sql).then(async ()=>{
  const a=await p.query(\"SELECT to_regclass('public.seller_accounts') AS t\");
  const c=await p.query(\"SELECT to_regclass('public.seller_charges') AS t\");
  console.log('seller_accounts', a.rows[0].t);
  console.log('seller_charges', c.rows[0].t);
  await p.end();
}).catch(e=>{console.error('migrate', e.message); process.exit(1);});
")

echo '=== gateway sellers modules load ==='
(cd services/gateway-api && node -e "require('./lib/seller-crypto'); require('./domain/sellers-oauth'); require('./domain/seller-charges'); console.log('sellers_modules_ok')")

echo '=== build frontend ==='
cd frontend/action-hub
npm run build
cd /var/www/leaction-platform

pm2 restart gateway-api --update-env
pm2 restart action-hub --update-env
sleep 5

curl -s -o /dev/null -w "gateway_health=%{http_code}\n" http://127.0.0.1:4001/health
curl -s -o /dev/null -w "hub_fe=%{http_code}\n" http://127.0.0.1:4000/api/health
curl -s -o /dev/null -w "sellers_connect=%{http_code}\n" -X POST http://127.0.0.1:4001/v1/sellers/connect-link -H 'Content-Type: application/json' -d '{}'
curl -s -o /dev/null -w "seller_page=%{http_code}\n" "http://127.0.0.1:4000/checkout/seller?charge=00000000-0000-4000-8000-000000000001&t=x"
curl -s -o /dev/null -w "sellers_webhook=%{http_code}\n" -X POST http://127.0.0.1:4001/webhook/sellers -H 'Content-Type: application/json' -d '{}'

echo "new_build_id $(cat frontend/action-hub/.next/BUILD_ID)"
echo P1_PAY_OK
