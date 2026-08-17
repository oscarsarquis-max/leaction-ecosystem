#!/usr/bin/env python3
"""Remove homologadores/gestores/vínculos pelos e-mails listados (Escola Teste)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor
from db import get_conn

EMAILS = [
    e.strip().lower()
    for e in (os.environ.get("CLEAN_EMAILS") or "").split(",")
    if e.strip()
]
if not EMAILS:
    EMAILS = [
        "suiane@inove4us.com.br",
        "homologador@inove4us.com.br",
    ]


def main() -> int:
    report = {"emails": EMAILS, "actions": []}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for email in EMAILS:
                cur.execute(
                    "SELECT id, instituicao_id, nome FROM public.school_gestores WHERE lower(email)=%s",
                    (email,),
                )
                g = cur.fetchone()
                if g:
                    gid = str(g["id"])
                    # sessões desse homologador/gestor
                    cur.execute(
                        """
                        SELECT id FROM public.school_homologacao_sessoes
                        WHERE gestor_id=%s OR homologador_id IN (
                          SELECT id FROM public.school_homologadores WHERE gestor_id=%s
                        )
                        """,
                        (gid, gid),
                    )
                    sids = [str(r["id"]) for r in cur.fetchall()]
                    if sids:
                        cur.execute(
                            "DELETE FROM public.school_homologacao_eventos WHERE sessao_id = ANY(%s::uuid[])",
                            (sids,),
                        )
                        cur.execute(
                            "DELETE FROM public.school_roteiro_respostas WHERE sessao_id = ANY(%s::uuid[])",
                            (sids,),
                        )
                        cur.execute(
                            "DELETE FROM public.school_homologacao_sessoes WHERE id = ANY(%s::uuid[])",
                            (sids,),
                        )
                    cur.execute(
                        "DELETE FROM public.school_roteiro_respostas WHERE gestor_id=%s",
                        (gid,),
                    )
                    cur.execute(
                        "DELETE FROM public.school_homologadores WHERE gestor_id=%s",
                        (gid,),
                    )
                    cur.execute(
                        "DELETE FROM public.school_unidade_equipe WHERE gestor_id=%s",
                        (gid,),
                    )
                    cur.execute(
                        "DELETE FROM public.school_gestor_perfis WHERE gestor_id=%s",
                        (gid,),
                    )
                    cur.execute("DELETE FROM public.school_gestores WHERE id=%s", (gid,))
                    report["actions"].append(
                        {"email": email, "gestor_deleted": gid, "sessoes": sids}
                    )
                else:
                    report["actions"].append({"email": email, "gestor_deleted": None})

                # vínculos professor + alocações
                cur.execute(
                    """
                    SELECT id FROM public.school_professores_vinculo
                    WHERE lower(email_convite)=%s
                    """,
                    (email,),
                )
                vins = [str(r["id"]) for r in cur.fetchall()]
                for vid in vins:
                    cur.execute(
                        "DELETE FROM public.school_alocacoes_docentes WHERE professor_vinculo_id=%s",
                        (vid,),
                    )
                    cur.execute(
                        "DELETE FROM public.school_professores_vinculo WHERE id=%s",
                        (vid,),
                    )
                report["actions"][-1]["vinculos_deleted"] = vins

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("=== cleanup OK ===")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"CLEANUP_FAILED: {exc}", file=sys.stderr)
        raise