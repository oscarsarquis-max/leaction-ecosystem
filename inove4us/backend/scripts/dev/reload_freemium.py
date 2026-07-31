"""Recarrega créditos IA / alivia quota freemium para conta de teste local."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

for env_path in (ROOT / ".env", ROOT.parent / ".env"):
    if not env_path.exists():
        continue
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

from psycopg2.extras import RealDictCursor  # noqa: E402

from db import (  # noqa: E402
    aulas_simples_quota,
    get_conn,
    get_creditos_ia,
)


EMAIL = (sys.argv[1] if len(sys.argv) > 1 else "inovador@inove4us.com.br").strip().lower()
TARGET_CREDITS = int(sys.argv[2]) if len(sys.argv) > 2 else 20


def main() -> None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_clie, mail_clie, creditos_ia, plan_tier,
                       COALESCE(is_test, FALSE) AS is_test
                  FROM public.ctdi_clie
                 WHERE mail_clie IS NOT NULL
                   AND LOWER(TRIM(mail_clie)) = %s
                 ORDER BY id_clie DESC
                 LIMIT 1
                """,
                (EMAIL,),
            )
            row = cur.fetchone()
            if not row:
                print(f"Cliente não encontrado: {EMAIL}")
                sys.exit(1)

            id_clie = int(row["id_clie"])
            antes = int(row["creditos_ia"] or 0)
            print(
                f"Antes: id_clie={id_clie} mail={row['mail_clie']} "
                f"creditos={antes} tier={row['plan_tier']} test={row['is_test']}"
            )
            print(f"Quota aulas: {aulas_simples_quota(id_clie)}")

            # Recarrega créditos IA para o alvo
            cur.execute(
                """
                UPDATE public.ctdi_clie
                   SET creditos_ia = %s,
                       is_test = TRUE
                 WHERE id_clie = %s
             RETURNING creditos_ia, plan_tier
                """,
                (TARGET_CREDITS, id_clie),
            )
            novo = cur.fetchone()

            # Alivia limite mensal de aulas simples (starter) movendo created_at
            # das aulas deste mês para o mês anterior — só conta de teste.
            cur.execute(
                """
                UPDATE public.inove_aulas_simples
                   SET created_at = created_at - INTERVAL '32 days'
                 WHERE id_clie = %s
                   AND date_trunc('month', COALESCE(created_at, CURRENT_TIMESTAMP))
                       = date_trunc('month', CURRENT_TIMESTAMP)
                """,
                (id_clie,),
            )
            aulas_ajustadas = cur.rowcount

    print(
        f"Depois: creditos={novo['creditos_ia']} tier={novo['plan_tier']} "
        f"aulas_ajustadas={aulas_ajustadas}"
    )
    print(f"Saldo lido: {get_creditos_ia(id_clie)}")
    print(f"Quota aulas: {aulas_simples_quota(id_clie)}")
    print("OK — recarregue a página / faça login de novo se o saldo na UI não atualizar.")


if __name__ == "__main__":
    main()
