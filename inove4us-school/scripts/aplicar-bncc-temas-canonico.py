#!/usr/bin/env python3
"""Publica o recorte BNCC como catálogo servido no seletor (só após OK do Oscar).

Não edita bncc_habilidades_oficial nem a ementa da escola.

Uso:
  python scripts/aplicar-bncc-temas-canonico.py --approve
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from bncc_oficial import ORIGEM, STATUS_APROVADO  # noqa: E402
from db import get_conn  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approve", action="store_true", required=True)
    args = ap.parse_args()
    if not args.approve:
        return 2
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.school_bncc_temas_canonico
                   SET status = %s,
                       aprovado_em = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                 WHERE origem = %s
                   AND status = 'pendente_revisao'
                """,
                (STATUS_APROVADO, ORIGEM),
            )
            n = cur.rowcount
    print(f"==> aprovados={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
