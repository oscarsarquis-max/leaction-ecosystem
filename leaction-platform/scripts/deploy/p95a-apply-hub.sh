#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform
echo '=== 95A backup ==='
if [ -f /tmp/p91c-backup-dbs.sh ]; then
  sed -i 's/\r$//' /tmp/p91c-backup-dbs.sh
  bash /tmp/p91c-backup-dbs.sh
elif [ -f scripts/deploy/_prod-backup-dbs.sh ]; then
  bash scripts/deploy/_prod-backup-dbs.sh
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK=/var/lib/leaction-platform/backups/p95a-$STAMP
mkdir -p "$BK"
cp -a frontend/action-hub/src/components/ClientCheckoutHeader.tsx "$BK/" || true
if [ -f frontend/action-hub/public/brands/lojadepaes.png ]; then
  cp -a frontend/action-hub/public/brands/lojadepaes.png "$BK/" || true
fi
if [ -f frontend/action-hub/.next/BUILD_ID ]; then
  cp -a frontend/action-hub/.next/BUILD_ID "$BK/BUILD_ID"
fi
echo "rollback_files $BK"

mkdir -p frontend/action-hub/public/brands frontend/action-hub/src/components frontend/action-hub/src/lib
install -m 644 /tmp/p95a-lojadepaes.png frontend/action-hub/public/brands/lojadepaes.png
install -m 644 /tmp/p95a-ClientCheckoutHeader.tsx frontend/action-hub/src/components/ClientCheckoutHeader.tsx
install -m 644 /tmp/p95a-loja-brand-asset.test.mjs frontend/action-hub/src/lib/loja-brand-asset.test.mjs

cd frontend/action-hub
node --test src/lib/loja-brand-asset.test.mjs
npm run build
pm2 restart action-hub --update-env
sleep 4
curl -s -o /dev/null -w "hub_fe=%{http_code}\n" http://127.0.0.1:4000/api/health
curl -s -o /dev/null -w "logo=%{http_code} %{content_type} %{size_download}\n" http://127.0.0.1:4000/brands/lojadepaes.png
curl -s -o /dev/null -w "loja_plans=%{http_code}\n" http://127.0.0.1:4000/loja
echo FE_OK
echo "new_build_id $(cat /var/www/leaction-platform/frontend/action-hub/.next/BUILD_ID)"
