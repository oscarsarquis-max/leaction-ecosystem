#!/usr/bin/env python3
from pathlib import Path
import psycopg2

env = {}
for line in Path("/var/www/inove4us-school/.env").read_text().splitlines():
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k] = v.strip().strip('"').strip("'")
c = psycopg2.connect(
    host=env["DB_HOST"],
    port=env.get("DB_PORT", 5432),
    user=env["DB_USER"],
    password=env.get("DB_PASS") or env.get("DB_PASSWORD"),
    dbname="inove4us_school",
    sslmode=env.get("DB_SSLMODE", "require"),
)
cur = c.cursor()
cur.execute("SELECT count(*) FROM school_metodologias_aliases")
print("aliases_rows", cur.fetchone()[0])
cur.execute(
    "SELECT filename, applied_at FROM school_schema_migrations WHERE filename LIKE %s",
    ("038%",),
)
print("038", cur.fetchone())
c.close()
