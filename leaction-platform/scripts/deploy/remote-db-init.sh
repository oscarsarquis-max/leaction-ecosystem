#!/usr/bin/env bash
# Cria DB leaction_hub e aplica schema (primeira vez)
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "Defina DATABASE_URL"
  exit 1
fi

echo "==> Verificando database leaction_hub"
exists=$(psql "$DATABASE_URL" -tAc "SELECT 1 FROM pg_database WHERE datname='leaction_hub'" 2>/dev/null || true)
if [[ "$exists" != "1" ]]; then
  admin_url=$(echo "$DATABASE_URL" | sed 's|/leaction_hub|/postgres|')
  psql "$admin_url" -v ON_ERROR_STOP=1 -c "CREATE DATABASE leaction_hub;"
  echo "    Database leaction_hub criado."
fi

APP_ROOT="${APP_ROOT:-/var/www/leaction-platform}"
for f in "$APP_ROOT/shared/database/init.sql" \
         "$APP_ROOT/shared/database/patch_add_columns.sql" \
         "$APP_ROOT/shared/database/patch_subscriptions.sql" \
         "$APP_ROOT/shared/database/patch_orders_payment_columns.sql" \
         "$APP_ROOT/shared/database/patch_orders_fulfillment.sql"; do
  if [[ -f "$f" ]]; then
    echo "    -> $(basename "$f")"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
  fi
done
echo "==> Schema OK."
