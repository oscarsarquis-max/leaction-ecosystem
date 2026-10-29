#!/usr/bin/env bash
set -euo pipefail
ROOT=/var/www/leaction-platform
ENV="$ROOT/.env"
URL='https://lojadepaes.com.br/api/v1/webhooks/actionhub/plans'
STRAY="$ROOT/services/gateway-api/.env"

if [ ! -f "$ENV" ]; then
  echo missing_root_env
  exit 1
fi
cp -a "$ENV" "/var/lib/leaction-platform/backups/p94-root-env-$(date -u +%Y%m%dT%H%M%SZ).bak"
if grep -q '^APP_PLANS_WEBHOOK_URL_LOJADEPAES=' "$ENV"; then
  sed -i "s|^APP_PLANS_WEBHOOK_URL_LOJADEPAES=.*|APP_PLANS_WEBHOOK_URL_LOJADEPAES=$URL|" "$ENV"
else
  printf '\nAPP_PLANS_WEBHOOK_URL_LOJADEPAES=%s\n' "$URL" >> "$ENV"
fi
grep -c '^APP_PLANS_WEBHOOK_URL_LOJADEPAES=' "$ENV"
if [ -f "$STRAY" ] && [ "$(wc -c < "$STRAY")" -lt 200 ]; then
  rm -f "$STRAY"
  echo stray_removed
fi
pm2 restart gateway-api --update-env
sleep 3
curl -s -o /dev/null -w "hub_health=%{http_code}\n" http://127.0.0.1:4001/health
curl -s -o /dev/null -w "catalog=%{http_code}\n" http://127.0.0.1:4001/v1/catalog/lojadepaes
curl -s -o /dev/null -w "marketplace=%{http_code}\n" http://127.0.0.1:4012/api/marketplace/health
curl -s -o /dev/null -w "hub_fe=%{http_code}\n" http://127.0.0.1:4000/api/health
echo PLANS_URL_OK
