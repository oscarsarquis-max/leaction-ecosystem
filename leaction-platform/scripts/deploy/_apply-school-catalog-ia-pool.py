#!/usr/bin/env python3
"""Apply Hub catalog IA-pool patch. Prints no secrets."""
from pathlib import Path
import os
import subprocess
import sys

env_path = Path("/var/www/leaction-platform/.env")
url = ""
for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#"):
        continue
    if raw.startswith("DATABASE_URL="):
        url = raw.split("=", 1)[1].strip().strip("'").strip('"')
        break
if not url:
    print("no DATABASE_URL")
    sys.exit(1)
sql = "/tmp/patch_inove4us_school_catalog_ia_pool.sql"
r = subprocess.run(
    ["psql", url, "-v", "ON_ERROR_STOP=1", "-f", sql],
    check=False,
    capture_output=True,
    text=True,
)
print("psql_exit", r.returncode)
print((r.stdout or "")[-800:])
if r.returncode != 0:
    err = r.stderr or ""
    # redact possible connection strings
    print("psql_err_len", len(err))
    sys.exit(r.returncode)
r2 = subprocess.run(
    [
        "psql",
        url,
        "-tAc",
        "SELECT sku, (features::text LIKE '%IA%') AS has_ia FROM catalog_plans WHERE app_id='inove4us-school' AND active",
    ],
    check=False,
    capture_output=True,
    text=True,
)
print((r2.stdout or "").strip())
