"""
Exporta tabelas de domínio do Postgres local (Docker leaction_db / MAtivas)
para um JSON usado por sync_domain_to_prod.py.

Uso:
  python scripts/export_domain_snapshot.py [saida.json]
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TABLES = {
    "problema_mativa": [
        "id",
        "metodologia",
        "grupo",
        "problemas_combinados",
        "observacao_automatizacao",
        "publico_preferencial",
        "publico_complementar",
        "modalidade_preferencial",
        "modalidades_alternativas",
    ],
    "ui_content": [
        "id",
        "content_key",
        "content_value",
        "content_type",
        "label",
        "is_active",
    ],
    "vocabulary_rules": [
        "id",
        "keyword",
        "rule_type",
        "replacement",
        "is_active",
    ],
}

DOCKER_DB = ("docker", "exec", "leaction_db", "psql", "-U", "admin", "-d", "MAtivas", "-At", "-c")


def _psql_json(query: str):
    out = subprocess.check_output([*DOCKER_DB, query], text=True).strip()
    if not out or out == "null":
        return []
    return json.loads(out)


def main() -> int:
    out_path = Path(sys.argv[1] if len(sys.argv) > 1 else "domain_snapshot.json")
    snap = {"columns": {t: cols for t, cols in TABLES.items()}}
    for table, cols in TABLES.items():
        col_sql = ", ".join(cols)
        q = (
            f"SELECT json_agg(t) FROM ("
            f"SELECT {col_sql} FROM {table} ORDER BY id"
            f") t"
        )
        rows = _psql_json(q)
        snap[table] = rows
        print(f"{table}: {len(rows)}")
    out_path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
