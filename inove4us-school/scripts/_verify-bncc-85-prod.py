#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from db import get_conn

with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS school_schema_migrations (filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        cur.execute(
            "INSERT INTO school_schema_migrations(filename) VALUES (%s) ON CONFLICT DO NOTHING",
            ("044_school_bncc_oficial.sql",),
        )
        cur.execute("SELECT COUNT(*) FROM bncc_habilidades_oficial")
        n1 = cur.fetchone()[0]
        cur.execute("SELECT status, COUNT(*) FROM school_bncc_temas_canonico GROUP BY 1 ORDER BY 1")
        st = cur.fetchall()
print("oficial", n1, "temas", st)
