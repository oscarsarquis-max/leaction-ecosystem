"""Inspeciona questões TA no Chamelleon e rubricas setoriais no PanelDX."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from urllib.parse import unquote, urlparse

import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def connect(url: str):
    p = urlparse(url)
    return psycopg2.connect(
        host=p.hostname or "127.0.0.1",
        port=p.port or 5432,
        dbname=(p.path or "").lstrip("/").split("?")[0],
        user=unquote(p.username or "postgres"),
        password=unquote(p.password or ""),
        client_encoding="UTF8",
    )


def main() -> None:
    cham = connect(os.environ["DATABASE_URL"])
    cur = cham.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT framework_id, axis, question_text, options, item_metadata
        FROM assessment_items
        WHERE axis LIKE 'TA%'
        ORDER BY axis
        """
    )
    rows = cur.fetchall()
    print(f"=== Chamelleon TA items: {len(rows)} ===")
    for row in rows[:3]:
        print("\nAXIS:", row["axis"][:80])
        print("Q:", row["question_text"][:100])
        opts = row["options"] or []
        print("Options:", len(opts))
        for o in opts[:3]:
            print(" ", json.dumps(o, ensure_ascii=False)[:180])
    cham.close()

    legacy = connect(os.environ["LEGACY_QUEST_DATABASE_URL"])
    cur2 = legacy.cursor(cursor_factory=RealDictCursor)
    cur2.execute(
        """
        SELECT DISTINCT UPPER(setor_ques) AS setor, COUNT(*) 
        FROM ctdi_quest WHERE id_dime = 4 GROUP BY UPPER(setor_ques)
        """
    )
    print("\n=== PanelDX id_dime=4 (LA setorial) setores ===")
    for r in cur2.fetchall():
        print(dict(r))

    cur2.execute(
        """
        SELECT q.setor_ques, q.desc_ques, r.grad_rubr, r.label_rubr, LEFT(r.desc_rubr, 80) AS desc
        FROM ctdi_quest q
        JOIN ctdi_rubricas r ON r.id_ques = q.id_ques
        WHERE q.id_dime = 4 AND UPPER(COALESCE(q.setor_ques,'')) LIKE '%TEL%'
        ORDER BY q.id_ques, r.grad_rubr
        LIMIT 12
        """
    )
    print("\n=== PanelDX telecom/LA sample ===")
    for r in cur2.fetchall():
        print(f"grad={r['grad_rubr']} {r['label_rubr']}: {r['desc']}")
    legacy.close()


if __name__ == "__main__":
    main()
