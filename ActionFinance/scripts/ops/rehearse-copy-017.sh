#!/bin/bash
set -eu
echo "AF_COPY_017 start"
echo "origin_host=${PGHOST}"
echo "destination=local-ephemeral-in-task"
psql -v ON_ERROR_STOP=1 -A -t -c "SELECT 'before_flyway=' || string_agg(version, ',' ORDER BY installed_rank) FROM actionfinance.flyway_schema_history WHERE success;"
psql -v ON_ERROR_STOP=1 -A -t -c "SELECT 'before_v13=' || coalesce((SELECT checksum::text FROM actionfinance.flyway_schema_history WHERE version='13' AND success),'missing');"
psql -v ON_ERROR_STOP=1 -A -t -c "SELECT 'before_titles=' || (SELECT count(*) FROM actionfinance.financial_title) || ' counterparties=' || (SELECT count(*) FROM actionfinance.counterparty) || ' amount_sum=' || coalesce((SELECT sum(amount_minor) FROM actionfinance.financial_title),0);"
psql -v ON_ERROR_STOP=1 -A -t -c "SELECT 'before_ids=' || coalesce(string_agg(id::text, ',' ORDER BY id), '');" -c "SELECT id FROM actionfinance.counterparty ORDER BY id;" >/tmp/before_ids.txt
BEFORE_IDS=$(psql -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(string_agg(id::text, ',' ORDER BY id),'') FROM actionfinance.counterparty;")
BEFORE_TITLES=$(psql -v ON_ERROR_STOP=1 -A -t -c "SELECT count(*) FROM actionfinance.financial_title;")
BEFORE_AMOUNT=$(psql -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(sum(amount_minor),0) FROM actionfinance.financial_title;")
echo "before_party_ids=${BEFORE_IDS}"
echo "dumping schema actionfinance only"
pg_dump --schema=actionfinance --format=custom --file=/tmp/origin.dump --no-password
DUMP_SHA=$(sha256sum /tmp/origin.dump | awk '{print $1}')
DUMP_BYTES=$(wc -c < /tmp/origin.dump)
echo "dump_sha256=${DUMP_SHA}"
echo "dump_bytes=${DUMP_BYTES}"
echo "starting isolated postgres"
export POSTGRES_PASSWORD=bootstrap-test
export POSTGRES_USER=actionfinance_bootstrap
export POSTGRES_DB=actionfinance
dockerless_pg() {
  mkdir -p /var/lib/postgresql/rehearsal
  chown -R postgres:postgres /var/lib/postgresql/rehearsal
  su - postgres -c "/usr/lib/postgresql/17/bin/initdb -D /var/lib/postgresql/rehearsal"
  echo "listen_addresses='127.0.0.1'" >> /var/lib/postgresql/rehearsal/postgresql.conf
  su - postgres -c "/usr/lib/postgresql/17/bin/pg_ctl -D /var/lib/postgresql/rehearsal -o '-p 55432' -w start"
}
# The official image already runs as postgres entrypoint; we use a second cluster via pg_ctl when available.
if [ -x /usr/lib/postgresql/17/bin/initdb ]; then
  dockerless_pg
else
  echo "initdb missing; using createdb on default cluster after local start is not available in this image mode"
  exit 20
fi
export PGPASSWORD_ORIGIN="$PGPASSWORD"
unset PGPASSWORD
psql -h 127.0.0.1 -p 55432 -U postgres -d postgres -v ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE actionfinance_migrator LOGIN PASSWORD 'migrator-test';
CREATE ROLE actionfinance_runtime LOGIN PASSWORD 'runtime-test';
CREATE DATABASE actionfinance OWNER actionfinance_migrator;
SQL
echo "restoring dump into isolated cluster"
PGPASSWORD=migrator-test pg_restore --no-owner --no-acl --dbname=postgresql://actionfinance_migrator:migrator-test@127.0.0.1:55432/actionfinance /tmp/origin.dump
AFTER_RESTORE_IDS=$(PGPASSWORD=migrator-test psql -h 127.0.0.1 -p 55432 -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(string_agg(id::text, ',' ORDER BY id),'') FROM actionfinance.counterparty;")
AFTER_RESTORE_TITLES=$(PGPASSWORD=migrator-test psql -h 127.0.0.1 -p 55432 -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT count(*) FROM actionfinance.financial_title;")
AFTER_RESTORE_AMOUNT=$(PGPASSWORD=migrator-test psql -h 127.0.0.1 -p 55432 -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(sum(amount_minor),0) FROM actionfinance.financial_title;")
echo "restore_party_ids=${AFTER_RESTORE_IDS}"
if [ "${BEFORE_IDS}" != "${AFTER_RESTORE_IDS}" ] || [ "${BEFORE_TITLES}" != "${AFTER_RESTORE_TITLES}" ] || [ "${BEFORE_AMOUNT}" != "${AFTER_RESTORE_AMOUNT}" ]; then
  echo "RESTORE_MISMATCH"
  exit 21
fi
echo "migrating V14-V19 on copy"
flyway -url=jdbc:postgresql://127.0.0.1:55432/actionfinance -user=actionfinance_migrator -password=migrator-test -schemas=actionfinance -defaultSchema=actionfinance -locations=filesystem:/opt/af-migrations migrate
AFTER_IDS=$(PGPASSWORD=migrator-test psql -h 127.0.0.1 -p 55432 -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(string_agg(id::text, ',' ORDER BY id),'') FROM actionfinance.counterparty;")
AFTER_TITLES=$(PGPASSWORD=migrator-test psql -h 127.0.0.1 -p 55432 -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT count(*) FROM actionfinance.financial_title;")
AFTER_AMOUNT=$(PGPASSWORD=migrator-test psql -h 127.0.0.1 -p 55432 -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT coalesce(sum(amount_minor),0) FROM actionfinance.financial_title;")
AFTER_FLYWAY=$(PGPASSWORD=migrator-test psql -h 127.0.0.1 -p 55432 -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT string_agg(version, ',' ORDER BY installed_rank) FROM actionfinance.flyway_schema_history WHERE success;")
V13=$(PGPASSWORD=migrator-test psql -h 127.0.0.1 -p 55432 -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT checksum FROM actionfinance.flyway_schema_history WHERE version='13' AND success;")
PENDING=$(PGPASSWORD=migrator-test psql -h 127.0.0.1 -p 55432 -U actionfinance_migrator -d actionfinance -v ON_ERROR_STOP=1 -A -t -c "SELECT count(*) FROM actionfinance.counterparty WHERE document_pending;")
echo "after_flyway=${AFTER_FLYWAY}"
echo "after_v13=${V13}"
echo "after_party_ids=${AFTER_IDS}"
echo "after_document_pending=${PENDING}"
if [ "${BEFORE_IDS}" != "${AFTER_IDS}" ] || [ "${BEFORE_TITLES}" != "${AFTER_TITLES}" ] || [ "${BEFORE_AMOUNT}" != "${AFTER_AMOUNT}" ]; then
  echo "MIGRATE_DATA_LOSS"
  exit 22
fi
echo "${AFTER_FLYWAY}" | grep -q ',19$' || echo "${AFTER_FLYWAY}" | grep -q '^19$' || { echo "NOT_V19"; exit 23; }
test "${V13}" = "728072343" || { echo "V13_CHECKSUM_CHANGED"; exit 24; }
shred -u /tmp/origin.dump || rm -f /tmp/origin.dump
echo "dump_destroyed=1"
echo "retention=task-ephemeral-until-stop"
echo "COPY_REHEARSAL_OK"
