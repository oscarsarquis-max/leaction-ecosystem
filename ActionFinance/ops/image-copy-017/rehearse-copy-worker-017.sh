#!/bin/bash
set -eu
echo "AF_COPY_017 worker"
echo "origin=${PGHOST}"
echo "copy=${COPY_HOST}"
echo "destination_kind=fargate-sidecar-ephemeral"
psql -v ON_ERROR_STOP=1 -A -t -c "SELECT 'before_flyway=' || string_agg(version, ',' ORDER BY installed_rank) FROM actionfinance.flyway_schema_history WHERE success;"
BEFORE_IDS=$(psql -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(string_agg(id::text, ',' ORDER BY id),'') FROM actionfinance.counterparty;")
BEFORE_TITLES=$(psql -v ON_ERROR_STOP=1 -A -t -c "SELECT count(*) FROM actionfinance.financial_title;")
BEFORE_AMOUNT=$(psql -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(sum(amount_minor),0) FROM actionfinance.financial_title;")
BEFORE_V13=$(psql -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce((SELECT checksum::text FROM actionfinance.flyway_schema_history WHERE version='13' AND success),'missing');")
echo "before_party_ids=${BEFORE_IDS}"
echo "before_titles=${BEFORE_TITLES}"
echo "before_amount=${BEFORE_AMOUNT}"
echo "before_v13=${BEFORE_V13}"
pg_dump --schema=actionfinance --format=custom --file=/tmp/origin.dump --no-password
DUMP_SHA=$(sha256sum /tmp/origin.dump | awk '{print $1}')
echo "dump_sha256=${DUMP_SHA}"
echo "dump_bytes=$(wc -c < /tmp/origin.dump)"
for i in $(seq 1 40); do
  if PGSSLMODE=disable PGPASSWORD=bootstrap-test psql -h "${COPY_HOST}" -U actionfinance_bootstrap -d actionfinance -c "SELECT 1" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
PGSSLMODE=disable PGPASSWORD=bootstrap-test psql -h "${COPY_HOST}" -U actionfinance_bootstrap -d actionfinance -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE actionfinance_migrator LOGIN PASSWORD 'migrator-test';
CREATE ROLE actionfinance_runtime LOGIN PASSWORD 'runtime-test';
GRANT ALL ON DATABASE actionfinance TO actionfinance_migrator;
GRANT CREATE ON DATABASE actionfinance TO actionfinance_migrator;
SQL
PGSSLMODE=disable PGPASSWORD=migrator-test pg_restore --exit-on-error --no-owner --no-acl --dbname="postgresql://actionfinance_migrator:migrator-test@${COPY_HOST}:5432/actionfinance" /tmp/origin.dump
RESTORE_IDS=$(PGSSLMODE=disable PGPASSWORD=migrator-test psql -h "${COPY_HOST}" -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(string_agg(id::text, ',' ORDER BY id),'') FROM actionfinance.counterparty;")
RESTORE_TITLES=$(PGSSLMODE=disable PGPASSWORD=migrator-test psql -h "${COPY_HOST}" -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT count(*) FROM actionfinance.financial_title;")
RESTORE_AMOUNT=$(PGSSLMODE=disable PGPASSWORD=migrator-test psql -h "${COPY_HOST}" -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(sum(amount_minor),0) FROM actionfinance.financial_title;")
echo "restore_party_ids=${RESTORE_IDS}"
if [ "${BEFORE_IDS}" != "${RESTORE_IDS}" ] || [ "${BEFORE_TITLES}" != "${RESTORE_TITLES}" ] || [ "${BEFORE_AMOUNT}" != "${RESTORE_AMOUNT}" ]; then
  echo "RESTORE_MISMATCH"
  exit 21
fi
flyway -url="jdbc:postgresql://${COPY_HOST}:5432/actionfinance" -user=actionfinance_migrator -password=migrator-test -schemas=actionfinance -defaultSchema=actionfinance -locations=filesystem:/opt/af-migrations migrate
AFTER_IDS=$(PGSSLMODE=disable PGPASSWORD=migrator-test psql -h "${COPY_HOST}" -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(string_agg(id::text, ',' ORDER BY id),'') FROM actionfinance.counterparty;")
AFTER_TITLES=$(PGSSLMODE=disable PGPASSWORD=migrator-test psql -h "${COPY_HOST}" -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT count(*) FROM actionfinance.financial_title;")
AFTER_AMOUNT=$(PGSSLMODE=disable PGPASSWORD=migrator-test psql -h "${COPY_HOST}" -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(sum(amount_minor),0) FROM actionfinance.financial_title;")
AFTER_FLYWAY=$(PGSSLMODE=disable PGPASSWORD=migrator-test psql -h "${COPY_HOST}" -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT string_agg(version, ',' ORDER BY installed_rank) FROM actionfinance.flyway_schema_history WHERE success;")
AFTER_V13=$(PGSSLMODE=disable PGPASSWORD=migrator-test psql -h "${COPY_HOST}" -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT checksum FROM actionfinance.flyway_schema_history WHERE version='13' AND success;")
PENDING=$(PGSSLMODE=disable PGPASSWORD=migrator-test psql -h "${COPY_HOST}" -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT count(*) FROM actionfinance.counterparty WHERE document_pending;")
echo "after_flyway=${AFTER_FLYWAY}"
echo "after_v13=${AFTER_V13}"
echo "after_party_ids=${AFTER_IDS}"
echo "after_document_pending=${PENDING}"
if [ "${BEFORE_IDS}" != "${AFTER_IDS}" ] || [ "${BEFORE_TITLES}" != "${AFTER_TITLES}" ] || [ "${BEFORE_AMOUNT}" != "${AFTER_AMOUNT}" ]; then
  echo "MIGRATE_DATA_LOSS"
  exit 22
fi
echo "${AFTER_FLYWAY}" | grep -q "19" || { echo "NOT_V19"; exit 23; }
test "${AFTER_V13}" = "728072343" || { echo "V13_CHECKSUM_CHANGED"; exit 24; }
shred -u /tmp/origin.dump 2>/dev/null || rm -f /tmp/origin.dump
echo "dump_destroyed=1"
echo "retention=fargate-ephemeral-until-task-stop"
echo "COPY_REHEARSAL_OK"
