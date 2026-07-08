"""Amostra rubricas setoriais no PanelDX legado."""
from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
url = os.getenv("LEGACY_QUEST_DATABASE_URL")
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
    SELECT q.setor_ques, r.grad_rubr, r.label_rubr, r.desc_rubr
    FROM ctdi_quest q
    JOIN ctdi_rubricas r ON r.id_ques = q.id_ques
    WHERE UPPER(COALESCE(q.setor_ques, 'GERAL')) != 'GERAL'
    ORDER BY q.id_ques, r.grad_rubr
    LIMIT 18
    """
)
for row in cur.fetchall():
    print(
        f"setor={row['setor_ques']} grad={row['grad_rubr']} "
        f"label={row['label_rubr']!r} desc={row['desc_rubr'][:70]!r}"
    )
conn.close()
