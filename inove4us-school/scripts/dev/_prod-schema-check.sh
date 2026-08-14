#!/bin/bash
set -euo pipefail
set -a
# shellcheck disable=SC1091
. /var/www/inove4us-school/.env
set +a
export PGPASSWORD="$DB_PASS"
export PGSSLMODE="${DB_SSLMODE:-require}"

echo "=== env bridge keys ==="
for k in SCHOOL_INTEGRATION_API_KEY SCHOOL_B2C_SHARED_SECRET INOVE4US_B2C_API_URL INOVE4US_B2C_WEBHOOK_URL SCHOOL_SYSTEM_LOCKED PRODUCTION_MASTER_KEY; do
  eval "v=\${$k-}"
  if [ -n "$v" ]; then echo "$k=present"; else echo "$k=MISSING"; fi
done

echo "=== school_schema_migrations table ==="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT to_regclass('public.school_schema_migrations');"

echo "=== migration files ==="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT filename FROM school_schema_migrations ORDER BY filename;" 2>&1 || true

echo "=== catalog ==="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
  "SELECT count(*) AS total, count(*) FILTER (WHERE origem='padrao') AS padrao FROM school_metodologias_catalogo;"

echo "=== 034 objects ==="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT to_regclass('public.school_curso_disciplinas');"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT column_name FROM information_schema.columns WHERE table_name='school_disciplinas' AND column_name='curso_id';"
