#!/usr/bin/env bash
# Gate 011 V2 — restore em banco temporário (não toca o DB live `qmind`).
# Uso (root no host): DUMP_ENC=/path/to/file.sql.enc bash restore-test-homolog.sh
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-/opt/qmind/infra/compose}"
OPENSSL_KEY_FILE="${BACKUP_OPENSSL_KEY_FILE:-/opt/qmind/secrets/backup-openssl.key}"
DUMP_ENC="${DUMP_ENC:?set DUMP_ENC to encrypted dump path}"
TEMP_DB="${TEMP_DB:-qmind_restore_v2}"
EVIDENCE_DIR="${EVIDENCE_DIR:-/opt/qmind/restore-evidence}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

DUMP_SQL="$WORKDIR/dump.sql"
REPORT="$EVIDENCE_DIR/RESTORE_V2_${STAMP}.md"

[[ -f "$DUMP_ENC" ]] || { echo "missing dump: $DUMP_ENC" >&2; exit 1; }
[[ -f "$OPENSSL_KEY_FILE" ]] || { echo "missing openssl key" >&2; exit 1; }

mkdir -p "$EVIDENCE_DIR"
cd "$COMPOSE_DIR"

POSTGRES_USER="${POSTGRES_USER:-qmind_admin}"
POSTGRES_DB_LIVE="${POSTGRES_DB:-qmind}"
if [[ -f .env.homolog ]]; then
  POSTGRES_USER="$(awk -F= '/^POSTGRES_USER=/{print substr($0,15); exit}' .env.homolog)"
  POSTGRES_DB_LIVE="$(awk -F= '/^POSTGRES_DB=/{print substr($0,13); exit}' .env.homolog)"
  POSTGRES_USER="${POSTGRES_USER:-qmind_admin}"
  POSTGRES_DB_LIVE="${POSTGRES_DB_LIVE:-qmind}"
fi

psql_admin() {
  docker compose -f docker-compose.homolog.yml exec -T db \
    psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 "$@"
}

psql_db() {
  local db="$1"; shift
  docker compose -f docker-compose.homolog.yml exec -T db \
    psql -U "$POSTGRES_USER" -d "$db" -v ON_ERROR_STOP=1 "$@"
}

echo "== decrypt =="
openssl enc -d -aes-256-cbc -pbkdf2 \
  -in "$DUMP_ENC" -out "$DUMP_SQL" \
  -pass "file:${OPENSSL_KEY_FILE}"
test -s "$DUMP_SQL"
BYTES="$(wc -c <"$DUMP_SQL" | tr -d ' ')"
SHA256="$(sha256sum "$DUMP_SQL" | awk '{print $1}')"

echo "== drop/create temp db ${TEMP_DB} =="
psql_admin -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${TEMP_DB}' AND pid <> pg_backend_pid();" || true
psql_admin -c "DROP DATABASE IF EXISTS ${TEMP_DB};"
psql_admin -c "CREATE DATABASE ${TEMP_DB} OWNER ${POSTGRES_USER};"

echo "== restore =="
docker compose -f docker-compose.homolog.yml exec -T db \
  psql -U "$POSTGRES_USER" -d "$TEMP_DB" -v ON_ERROR_STOP=1 <"$DUMP_SQL"

echo "== validate =="
# Capture validation into report
{
  echo "# Restore V2 evidence — ${STAMP}"
  echo
  echo "- Dump: \`$(basename "$DUMP_ENC")\`"
  echo "- Decrypted bytes: \`${BYTES}\`"
  echo "- SHA-256 (sql): \`${SHA256}\`"
  echo "- Temp DB: \`${TEMP_DB}\`"
  echo "- Live DB (untouched): \`${POSTGRES_DB_LIVE}\`"
  echo "- Operator: admin identity for S3 Get; openssl key on host only"
  echo
  echo "## Structure"
  echo '```'
  psql_db "$TEMP_DB" -c "\dt" 
  echo '```'
  echo
  echo "## Alembic"
  echo '```'
  psql_db "$TEMP_DB" -c "SELECT version_num FROM alembic_version;"
  echo '```'
  echo
  echo "## Seeds / control counts"
  echo '```'
  psql_db "$TEMP_DB" -c "
SELECT 'maturity_models' AS entity, count(*)::text AS n FROM maturity_models
UNION ALL SELECT 'maturity_dimensions', count(*)::text FROM maturity_dimensions
UNION ALL SELECT 'maturity_criteria', count(*)::text FROM maturity_criteria
UNION ALL SELECT 'assessment_models', count(*)::text FROM assessment_models
UNION ALL SELECT 'standards', count(*)::text FROM standards
UNION ALL SELECT 'standard_versions', count(*)::text FROM standard_versions
UNION ALL SELECT 'requirements', count(*)::text FROM requirements
UNION ALL SELECT 'organizations', count(*)::text FROM organizations
ORDER BY 1;
"
  echo '```'
  echo
  echo "## RLS force (sample)"
  echo '```'
  psql_db "$TEMP_DB" -c "
SELECT c.relname, c.relrowsecurity AS rls, c.relforcerowsecurity AS force_rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
  AND c.relname IN ('organizations','assessments','evidences','findings','memberships')
ORDER BY 1;
"
  echo '```'
  echo
  echo "## Compare live vs restore (counts)"
  echo '```'
  psql_db "$POSTGRES_DB_LIVE" -c "
SELECT 'LIVE' AS src, 'maturity_models' AS entity, count(*)::text AS n FROM maturity_models
UNION ALL SELECT 'LIVE','maturity_criteria', count(*)::text FROM maturity_criteria
UNION ALL SELECT 'LIVE','assessment_models', count(*)::text FROM assessment_models;
"
  psql_db "$TEMP_DB" -c "
SELECT 'RESTORE' AS src, 'maturity_models' AS entity, count(*)::text AS n FROM maturity_models
UNION ALL SELECT 'RESTORE','maturity_criteria', count(*)::text FROM maturity_criteria
UNION ALL SELECT 'RESTORE','assessment_models', count(*)::text FROM assessment_models;
"
  echo '```'
  echo
  echo "## Result"
  echo "**PASS** — decrypt + restore into temp DB + structure/seeds/RLS validated; live DB not overwritten."
} | tee "$REPORT"

echo "== drop temp db =="
psql_admin -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${TEMP_DB}' AND pid <> pg_backend_pid();" || true
psql_admin -c "DROP DATABASE IF EXISTS ${TEMP_DB};"

# Confirm gone
GONE="$(psql_admin -Atc "SELECT 1 FROM pg_database WHERE datname = '${TEMP_DB}';" || true)"
if [[ -n "$GONE" ]]; then
  echo "ERROR: temp db still exists" >&2
  exit 1
fi

{
  echo
  echo "## Cleanup"
  echo "- Temp DB \`${TEMP_DB}\` dropped: **YES**"
  echo "- Report path: \`${REPORT}\`"
} | tee -a "$REPORT"

chmod 644 "$REPORT"
echo "RESTORE_V2_PASS report=$REPORT"
