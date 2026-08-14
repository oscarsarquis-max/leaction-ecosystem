#!/bin/bash
set -euo pipefail
set -a
# shellcheck disable=SC1091
. /var/www/inove4us-school/.env
set +a
export PGPASSWORD="$DB_PASS"
export PGSSLMODE="${DB_SSLMODE:-require}"

echo "=== precheck 033/034 ==="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT
  (SELECT count(*) FROM school_turmas WHERE curso_id IS NULL) AS turmas_sem_curso,
  (SELECT count(*) FROM school_disciplinas WHERE curso_id IS NULL) AS disc_sem_curso,
  (SELECT count(*) FROM school_disciplinas) AS disc_total,
  (SELECT to_regclass('public.school_curso_disciplinas') IS NOT NULL) AS nn_existe;
"

echo "=== applied ==="
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT filename FROM school_schema_migrations WHERE filename LIKE '03%' ORDER BY 1;"
