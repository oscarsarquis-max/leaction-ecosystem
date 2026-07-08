"""Inspeciona ctdi_rubricas no banco PanelDX legado."""
from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
url = os.getenv("LEGACY_QUEST_DATABASE_URL")
if not url:
    raise SystemExit("LEGACY_QUEST_DATABASE_URL não configurado")

parsed = urlparse(url)
dbname = (parsed.path or "/LeAction_SysF").lstrip("/").split("?")[0]
conn = psycopg2.connect(
    host=parsed.hostname or "127.0.0.1",
    port=parsed.port or 5432,
    dbname=dbname,
    user=unquote(parsed.username or "postgres"),
    password=unquote(parsed.password or ""),
)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute(
    """
    SELECT
      COUNT(*) AS total,
      COUNT(*) FILTER (WHERE desc_rubr IS NULL OR TRIM(desc_rubr) = '') AS sem_desc,
      COUNT(*) FILTER (WHERE label_rubr IS NULL OR TRIM(label_rubr) = '') AS sem_label
    FROM ctdi_rubricas
    """
)
print("Stats:", dict(cur.fetchone()))

cur.execute(
    """
    SELECT grad_rubr, label_rubr, desc_rubr
    FROM ctdi_rubricas
    WHERE id_ques = (
      SELECT id_ques FROM ctdi_quest WHERE id_dime IN (1, 2, 3, 5) LIMIT 1
    )
    ORDER BY grad_rubr
  """
)
print("\nSample universal question:")
for row in cur.fetchall():
    print(f"  grad={row['grad_rubr']} label={row['label_rubr']!r}")
    print(f"    desc={row['desc_rubr'][:120]!r}...")

cur.execute(
    """
    SELECT q.id_dime, COUNT(DISTINCT r.id_ques) AS quests, COUNT(*) AS rubrics,
           COUNT(*) FILTER (WHERE r.desc_rubr IS NULL OR TRIM(r.desc_rubr) = '') AS sem_desc
    FROM ctdi_rubricas r
    JOIN ctdi_quest q ON q.id_ques = r.id_ques
    GROUP BY q.id_dime
    ORDER BY q.id_dime
    """
)
print("\nBy id_dime:")
for row in cur.fetchall():
    print(dict(row))

conn.close()
