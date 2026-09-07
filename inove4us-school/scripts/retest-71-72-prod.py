#!/usr/bin/env python3
"""Reteste prompts 71+72 no School de produção — sem senhas no stdout."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor
from db import get_conn

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"
PEI = "88da0eae-5446-4ec7-9c96-f88f63d37c33"
PERIOD = "68a38cc9-b975-4411-815e-b1fcef171c3d"


def j(v):
    if isinstance(v, (datetime, date, UUID)):
        return str(v)
    return v


def main() -> int:
    from app import app

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT g.id, g.instituicao_id, g.unidade_id, g.nome, g.email, g.cargo,
                       i.razao_social AS instituicao_nome,
                       COALESCE(array_agg(p.zona ORDER BY p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                FROM public.school_gestores g
                JOIN public.school_instituicoes i ON i.id = g.instituicao_id
                LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                WHERE g.instituicao_id = %s AND lower(g.email) = %s
                GROUP BY g.id, i.razao_social
                """,
                (INST, HOMOLOG),
            )
            gestor = cur.fetchone()
            if not gestor:
                raise SystemExit("Homologador não encontrado")
            cur.execute(
                """
                SELECT id, titulo, tipo, data, turma_id
                FROM public.school_planejamento_escolar
                WHERE instituicao_id = %s
                ORDER BY data DESC
                LIMIT 8
                """,
                (INST,),
            )
            plans = [dict(r) for r in cur.fetchall() or []]
            cur.execute(
                """
                SELECT id, nome_completo, periodo_letivo_id,
                       assinado_coordenador, assinado_psicopedagogo, status
                FROM public.school_pei_alunos
                WHERE id = %s
                """,
                (PEI,),
            )
            pei_db = cur.fetchone()

    user = {
        "id": str(gestor["id"]),
        "instituicao_id": str(gestor["instituicao_id"]),
        "instituicao_nome": gestor.get("instituicao_nome"),
        "unidade_id": str(gestor["unidade_id"]) if gestor.get("unidade_id") else None,
        "nome": gestor["nome"],
        "email": gestor["email"],
        "cargo": gestor["cargo"],
        "zonas": list(gestor["zonas"] or []),
    }

    out = {
        "pei_db_antes": {k: j(v) for k, v in dict(pei_db or {}).items()},
        "planejamento_db": [
            {k: j(v) for k, v in p.items()} for p in plans
        ],
        "tests": {},
    }

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["school_gestor"] = user

    # PEI list + report gate
    res = client.get("/api/pei/alunos")
    body = res.get_json(silent=True) or []
    lucas = next((r for r in body if r.get("id") == PEI), None)
    out["tests"]["pei_listagem"] = {
        "http": res.status_code,
        "encontrado": bool(lucas),
        "periodo_letivo_id": (lucas or {}).get("periodo_letivo_id"),
        "periodo_rotulo": (lucas or {}).get("periodo_rotulo"),
        "valido": (lucas or {}).get("valido"),
        "sem_periodo": not bool((lucas or {}).get("periodo_letivo_id")),
    }

    res_pdf = client.get(f"/api/pei/alunos/{PEI}/relatorio-execucao")
    out["tests"]["relatorio_execucao"] = {
        "http": res_pdf.status_code,
        "content_type": res_pdf.headers.get("Content-Type"),
        "bytes": len(res_pdf.data or b""),
        "error": None if res_pdf.status_code == 200 else (res_pdf.get_json(silent=True) or {}).get("error"),
    }

    # PUT período em PEI assinado (caminho real)
    res_put = client.put(
        f"/api/pei/alunos/{PEI}",
        json={"periodo_letivo_id": PERIOD},
        content_type="application/json",
    )
    put_body = res_put.get_json(silent=True) or {}
    out["tests"]["put_periodo_assinado"] = {
        "http": res_put.status_code,
        "periodo_letivo_id": put_body.get("periodo_letivo_id"),
        "periodo_rotulo": put_body.get("periodo_rotulo"),
        "valido": put_body.get("valido"),
        "assinado_coordenador": put_body.get("assinado_coordenador"),
        "assinado_psicopedagogo": put_body.get("assinado_psicopedagogo"),
        "error": put_body.get("error"),
    }

    # Radar: planejamento no recorte
    dates = [str(p.get("data") or "")[:10] for p in plans if p.get("data")]
    probe = dates[0] if dates else "2026-09-04"
    res_cal = client.get(
        f"/api/pedagogico/calendario-pedagogico?data_inicio={probe}&data_fim={probe}"
    )
    cal = res_cal.get_json(silent=True) or []
    if not isinstance(cal, list):
        cal = []
    plan_items = [x for x in cal if str(x.get("id") or "").startswith("plan-") or x.get("origem_planejamento")]
    out["tests"]["radar_planejamento"] = {
        "http": res_cal.status_code,
        "data_probe": probe,
        "itens_no_dia": len(cal),
        "itens_planejamento": len(plan_items),
        "titulos": [x.get("aula_titulo") for x in plan_items[:5]],
    }

    dist = ROOT / "frontend" / "dist" / "assets"
    js_files = list(dist.glob("index-*.js"))
    blob = js_files[0].read_text(encoding="utf-8", errors="replace") if js_files else ""
    out["tests"]["bundle"] = {
        "js": js_files[0].name if js_files else None,
        "enumerateDaysISO": "enumerateDaysISO" in blob,
        "planToCalItem": "planToCalItem" in blob or "source:\"planejamento\"" in blob or 'source:"planejamento"' in blob,
        "axisDates": "enumerateDaysISO" in blob,
    }

    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
