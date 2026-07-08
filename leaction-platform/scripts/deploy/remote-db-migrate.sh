#!/usr/bin/env bash
# Aplica apenas patches idempotentes no leaction_hub (deploy incremental)
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "Defina DATABASE_URL"
  exit 1
fi

APP_ROOT="${APP_ROOT:-/var/www/leaction-platform}"
echo "==> Patches leaction_hub"
for f in "$APP_ROOT"/shared/database/patch_*.sql "$APP_ROOT"/shared/database/*_migration.sql; do
  if [[ -f "$f" ]]; then
    echo "    -> $(basename "$f")"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
  fi
done
echo "==> Patches aplicados."
