"""
Sincroniza tabelas de domínio do MAtivas para o banco apontado pelo app
(produção quando rodado dentro do container mativas_prod_backend).

Uso no container:
  PYTHONPATH=/app python /tmp/sync_domain_to_prod.py /tmp/domain_snapshot.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text
from database.models import get_engine

TABLES = ("problema_mativa", "ui_content", "vocabulary_rules")


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: sync_domain_to_prod.py <snapshot.json>", file=sys.stderr)
        return 2

    snapshot = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    engine = get_engine()

    with engine.begin() as conn:
        for table in TABLES:
            rows = snapshot.get(table) or []
            cols = snapshot["columns"][table]
            col_list = ", ".join(cols)
            placeholders = ", ".join(f":{c}" for c in cols)

            before = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))

            for row in rows:
                params = {c: row.get(c) for c in cols}
                conn.execute(
                    text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"),
                    params,
                )

            # Ajusta sequence se houver coluna id
            if "id" in cols and rows:
                max_id = max(int(r["id"]) for r in rows if r.get("id") is not None)
                seq = f"{table}_id_seq"
                conn.execute(text(f"SELECT setval('{seq}', {max_id}, true)"))

            after = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"{table}: {before} -> {after}")

    print("domain_sync_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
