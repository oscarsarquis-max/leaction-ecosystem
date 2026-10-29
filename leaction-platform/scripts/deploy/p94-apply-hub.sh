#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform
echo '=== 94 backup ==='
if [ -f /tmp/p91c-backup-dbs.sh ]; then
  sed -i 's/\r$//' /tmp/p91c-backup-dbs.sh
  bash /tmp/p91c-backup-dbs.sh
elif [ -f scripts/deploy/_prod-backup-dbs.sh ]; then
  bash scripts/deploy/_prod-backup-dbs.sh
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK=/var/lib/leaction-platform/backups/p94-$STAMP
mkdir -p "$BK"
cp -a services/gateway-api/domain/credits-ops.js "$BK/" || true
cp -a services/gateway-api/domain/outbox-worker.js "$BK/" || true
cp -a services/gateway-api/domain/catalog-subscription.js "$BK/" || true
echo "rollback_files $BK"

install -m 644 /tmp/p94-credits-ops.js services/gateway-api/domain/credits-ops.js
install -m 644 /tmp/p94-credits-ops.test.js services/gateway-api/domain/credits-ops.test.js
install -m 644 /tmp/p94-outbox-worker.js services/gateway-api/domain/outbox-worker.js
install -m 644 /tmp/p94-outbox-worker.plans.test.js services/gateway-api/domain/outbox-worker.plans.test.js
install -m 644 /tmp/p94-loja-plans-notify.js services/gateway-api/domain/loja-plans-notify.js
install -m 644 /tmp/p94-catalog-subscription.js services/gateway-api/domain/catalog-subscription.js

cd services/gateway-api
node --test domain/credits-ops.test.js domain/outbox-worker.plans.test.js domain/catalog-subscription.test.js
cd /var/www/leaction-platform

# Recepção da Loja sobe antes. A URL isolada só é ligada se o ingresso /plans já responder.
# O gateway lê /var/www/leaction-platform/.env (não services/gateway-api/.env).
ROOT_ENV=/var/www/leaction-platform/.env
if curl -fsS -o /dev/null -w "%{http_code}" https://lojadepaes.com.br/api/v1/health | grep -q 200; then
  if curl -s -o /tmp/p94-plans-probe.txt -w "%{http_code}" -X POST https://lojadepaes.com.br/api/v1/webhooks/actionhub/plans -H "Content-Type: application/json" -d '{"token":"xxxxxxxxxxxxxxxxxxxx"}' | grep -Eq '401|403|422'; then
    if [ -f "$ROOT_ENV" ]; then
      if grep -q '^APP_PLANS_WEBHOOK_URL_LOJADEPAES=' "$ROOT_ENV"; then
        sed -i 's|^APP_PLANS_WEBHOOK_URL_LOJADEPAES=.*|APP_PLANS_WEBHOOK_URL_LOJADEPAES=https://lojadepaes.com.br/api/v1/webhooks/actionhub/plans|' "$ROOT_ENV"
      else
        printf '\nAPP_PLANS_WEBHOOK_URL_LOJADEPAES=%s\n' 'https://lojadepaes.com.br/api/v1/webhooks/actionhub/plans' >> "$ROOT_ENV"
      fi
      echo plans_url_set
    else
      echo plans_url_skipped_missing_root_env
    fi
  else
    echo plans_url_skipped_ingress_not_ready
  fi
fi

pm2 restart gateway-api --update-env
sleep 3
curl -s -o /dev/null -w "hub_health=%{http_code}\n" http://127.0.0.1:4001/health
curl -s -o /dev/null -w "catalog=%{http_code}\n" http://127.0.0.1:4001/v1/catalog/lojadepaes
echo HUB_94_OK "$STAMP"
echo rollback_files "$BK"
