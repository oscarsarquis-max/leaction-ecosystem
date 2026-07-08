"""Neutraliza enunciados das 4 dimensões universais já persistidos no banco."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.data.legacy_quest_loader import (  # noqa: E402
    is_universal_assessment_axis,
    sanitize_universal_question_text,
)


def _connect():
    import psycopg2

    url = os.getenv("DATABASE_URL", "postgresql://postgres:Cmgv6190!%40@127.0.0.1:5432/chamelleon")
    parsed = urlparse(url)
    dbname = parsed.path.lstrip("/").split("?")[0]
    return psycopg2.connect(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 5432,
        dbname=dbname,
        user=unquote(parsed.username or "postgres"),
        password=unquote(parsed.password or ""),
        client_encoding="UTF8",
    )


def main() -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id::text, framework_id, axis, question_text, item_metadata
        FROM assessment_items
        ORDER BY framework_id, axis, id
        """
    )
    rows = cur.fetchall()
    updated = 0

    for item_id, framework_id, axis, question_text, item_metadata in rows:
        if not is_universal_assessment_axis(axis):
            continue

        original = question_text or ""
        cleaned = sanitize_universal_question_text(original)
        if not cleaned or cleaned == original:
            continue

        meta = dict(item_metadata or {})
        meta.setdefault("legacy_question_text", original)
        meta["text_hygiene"] = "education_terms_removed"

        cur.execute(
            """
            UPDATE assessment_items
            SET question_text = %s, item_metadata = %s::jsonb
            WHERE id = %s::uuid
            """,
            (cleaned, json.dumps(meta), item_id),
        )
        updated += 1
        print(f"[{framework_id}] {item_id[:8]} …")
        print(f"  antes: {original}")
        print(f"  depois: {cleaned}")
        print()

    conn.commit()
    cur.close()
    conn.close()
    print(f"Concluído: {updated} questão(ões) universal(is) atualizada(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
