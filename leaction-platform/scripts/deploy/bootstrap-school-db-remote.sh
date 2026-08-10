#!/usr/bin/env bash
# Cria inove4us_school no mesmo Postgres do Hub (paneldx RDS) e aplica migrations.
set -euo pipefail
APP_ROOT="${1:-/var/www/inove4us-school}"
MIG_DIR="$APP_ROOT/infra/db/migrations"
set -a
# shellcheck disable=SC1091
. /var/www/leaction-platform/.env
set +a
python3 - <<'PY'
import os, urllib.parse, subprocess, sys
u = os.environ["DATABASE_URL"]
p = urllib.parse.urlparse(u)
os.environ["PGPASSWORD"] = urllib.parse.unquote(p.password or "")
os.environ["PGHOST"] = p.hostname or ""
os.environ["PGPORT"] = str(p.port or 5432)
os.environ["PGUSER"] = p.username or ""
os.environ["PGSSLMODE"] = "require"
print(f"host={os.environ['PGHOST']} user={os.environ['PGUSER']}")
# create db if needed
r = subprocess.run(
    ["psql", "-d", "postgres", "-tAc", "SELECT 1 FROM pg_database WHERE datname='inove4us_school'"],
    capture_output=True, text=True, check=False,
)
if r.stdout.strip() != "1":
    print("CREATE DATABASE inove4us_school")
    subprocess.check_call(["psql", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c",
                           "CREATE DATABASE inove4us_school ENCODING 'UTF8' TEMPLATE template0;"])
else:
    print("DB inove4us_school already exists")
print("OK")
PY

export PGPASSWORD PGHOST PGPORT PGUSER PGSSLMODE
# re-export from python env already set in shell? need again
eval "$(python3 - <<'PY'
import os, urllib.parse
u = os.environ["DATABASE_URL"]
p = urllib.parse.urlparse(u)
print(f"export PGPASSWORD={urllib.parse.unquote(p.password or '')!r}")
print(f"export PGHOST={p.hostname!r}")
print(f"export PGPORT={p.port or 5432}")
print(f"export PGUSER={p.username!r}")
print("export PGSSLMODE=require")
PY
)"

shopt -s nullglob
migs=("$MIG_DIR"/[0-9][0-9][0-9]_*.sql)
# filter down
filtered=()
for f in "${migs[@]}"; do
  [[ "$f" == *.down.sql ]] && continue
  filtered+=("$f")
done
IFS=$'\n' sorted=($(printf '%s\n' "${filtered[@]}" | sort))
for f in "${sorted[@]}"; do
  echo "==> $(basename "$f")"
  psql -d inove4us_school -v ON_ERROR_STOP=1 -f "$f"
done
psql -d inove4us_school -c "SELECT count(*) AS school_tables FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'school_%';"
echo "DONE school db"
