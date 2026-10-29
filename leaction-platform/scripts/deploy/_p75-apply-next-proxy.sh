#!/usr/bin/env bash
set -euo pipefail
ROOT=/var/www/leaction-platform
FE=$ROOT/frontend/action-hub
RB=$(cat /tmp/p75-rollback-dir)
mkdir -p "$RB/frontend/action-hub/src/app/marketplace-api/vitrine"
mkdir -p "$RB/frontend/action-hub/src/app/marketplace-api/offers"
cp -a "$FE/src/app/marketplace-api/vitrine/route.ts" "$RB/frontend/action-hub/src/app/marketplace-api/vitrine/route.ts"
cp -a "$FE/src/app/marketplace-api/offers/route.ts" "$RB/frontend/action-hub/src/app/marketplace-api/offers/route.ts"
if [ -d "$FE/.next" ]; then
  rm -rf "$RB/next-build"
  cp -a "$FE/.next" "$RB/next-build"
  echo "next_backup $RB/next-build"
  echo "$(cat $FE/.next/BUILD_ID)" > "$RB/BUILD_ID"
fi
sed -i 's/\r$//' /tmp/p75/vitrine.route.ts /tmp/p75/offers.route.ts
install -m 644 /tmp/p75/vitrine.route.ts "$FE/src/app/marketplace-api/vitrine/route.ts"
install -m 644 /tmp/p75/offers.route.ts "$FE/src/app/marketplace-api/offers/route.ts"
cd "$FE"
npm run build
cd "$ROOT"
pm2 restart action-hub --update-env
sleep 3
echo "new_build_id $(cat $FE/.next/BUILD_ID)"
curl -fsS --max-time 8 https://actionhub.com.br/api/health || true
echo
echo "next_done"
