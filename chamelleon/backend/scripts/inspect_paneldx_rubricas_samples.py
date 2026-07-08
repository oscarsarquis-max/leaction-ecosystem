"""Amostras de rubricas PanelDX por tipo de questão."""
from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
parsed = urlparse(os.getenv("LEGACY_QUEST_DATABASE_URL", ""))
conn = psycopg2.connect(
    host=parsed.hostname or "127.0.0.1",
    port=parsed.port or 5432,
    dbname=(parsed.path or "/LeAction_SysF").lstrip("/").split("?")[0],
    user=unquote(parsed.username or "postgres"),
    password=unquote(parsed.password or ""),
    client_encoding="UTF8",
)
cur = conn.cursor(cursor_factory=RealDictCursor)

for prefu, label in [("P", "Presente"), ("F", "Futuro")]:
    cur.execute(
        """
        SELECT q.id_ques, q.prefu_ques, r.grad_rubr, r.label_rubr, r.desc_rubr
        FROM ctdi_quest q
        JOIN ctdi_rubricas r ON r.id_ques = q.id_ques
        WHERE q.id_dime = 1 AND UPPER(q.prefu_ques) = %s
        ORDER BY q.id_ques, r.grad_rubr
        LIMIT 8
        """,
        (prefu,),
    )
    print(f"\n=== {label} (id_dime=1) ===")
    for row in cur.fetchall():
        print(
            f"grad={row['grad_rubr']} | label={row['label_rubr']} | desc={row['desc_rubr'][:90]}"
        )

cur.execute(
    """
    SELECT DISTINCT array_agg(grad_rubr ORDER BY grad_rubr) AS grades, COUNT(*) 
    FROM (
      SELECT id_ques, grad_rubr FROM ctdi_rubricas GROUP BY id_ques, grad_rubr
    ) x
    GROUP BY id_ques
    ORDER BY COUNT(*) DESC
    LIMIT 5
    """
)
print("\nGrade patterns per question (top):")
for row in cur.fetchall():
    print(row)

cur.execute(
    """
    SELECT q.id_dime, UPPER(q.prefu_ques) AS prefu, 
           MIN(r.grad_rubr) AS min_g, MAX(r.grad_rubr) AS max_g, COUNT(*) AS rub_count
    FROM ctdi_quest q
    JOIN ctdi_rubricas r ON r.id_ques = q.id_ques
    WHERE q.id_dime IN (1,2,3,5)
    GROUP BY q.id_dime, UPPER(q.prefu_ques)
    ORDER BY q.id_dime, prefu
    """
)
print("\nGrade ranges by dime/prefu:")
for row in cur.fetchall():
    print(dict(row))

conn.close()
