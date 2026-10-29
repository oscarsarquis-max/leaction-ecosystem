#!/usr/bin/env bash
# Backup RDS: inove4us_school + leaction_hub (obrigatório antes de migration)
set -euo pipefail

PY=/var/www/inove4us-school/backend/.venv/bin/python
"$PY" <<'PY'
import os, urllib.parse, subprocess, datetime
from pathlib import Path

stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
out = Path("/var/lib/leaction-platform/backups")
out.mkdir(parents=True, exist_ok=True)

def load(path):
    env = {}
    p = Path(path)
    if not p.exists():
        return env
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

school = load("/var/www/inove4us-school/.env")
hub = load("/var/www/leaction-platform/.env")

def dump(dbname, host, port, user, password, sslmode="require"):
    dest = out / f"{dbname}_{stamp}.dump"
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    env["PGSSLMODE"] = sslmode
    cmd = [
        "pg_dump",
        "-h", host,
        "-p", str(port),
        "-U", user,
        "-d", dbname,
        "-Fc",
        "-f", str(dest),
    ]
    print("dumping", dbname, "->", dest)
    subprocess.check_call(cmd, env=env)
    print("ok", dest, "bytes", dest.stat().st_size)

sh_host = school.get("DB_HOST")
sh_user = school.get("DB_USER")
sh_pass = school.get("DB_PASS") or school.get("DB_PASSWORD")
sh_port = school.get("DB_PORT") or "5432"
sh_ssl = school.get("DB_SSLMODE") or "require"
dump("inove4us_school", sh_host, sh_port, sh_user, sh_pass, sh_ssl)

p = urllib.parse.urlparse(hub["DATABASE_URL"])
dump(
    "leaction_hub",
    p.hostname,
    p.port or 5432,
    p.username,
    urllib.parse.unquote(p.password or ""),
    "require",
)

print("BACKUP_STAMP", stamp)
for f in sorted(out.glob(f"*_{stamp}.dump")):
    print(f.name, f.stat().st_size)
PY
