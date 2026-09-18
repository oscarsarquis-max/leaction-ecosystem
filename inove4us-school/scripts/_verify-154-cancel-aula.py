#!/usr/bin/env python3
"""154 — cancelar aula some da agenda B2C e libera o slot 104. Homologador. Limpa o que criar."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

HOMOLOG = "homologador@leaction.com.br"
MARKER = "[TRIAGEM 154]"
TZ = ZoneInfo("America/Sao_Paulo")


def user():
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
                 WHERE lower(g.email) = %s
                 GROUP BY g.id, i.razao_social
                 LIMIT 1
                """,
                (HOMOLOG,),
            )
            r = cur.fetchone()
    return {
        "id": str(r["id"]),
        "instituicao_id": str(r["instituicao_id"]),
        "instituicao_nome": r.get("instituicao_nome"),
        "unidade_id": str(r["unidade_id"]) if r.get("unidade_id") else None,
        "nome": r["nome"],
        "email": r["email"],
        "cargo": r["cargo"],
        "zonas": list(r["zonas"] or []),
    }


def slim(r):
    body = r.get_json(silent=True) or {}
    item = body.get("item") or {}
    return {
        "http": r.status_code,
        "error": body.get("error"),
        "code": body.get("code"),
        "id": item.get("id"),
        "tipo": item.get("tipo_evento"),
        "status": item.get("status"),
        "message": body.get("message"),
        "origem_plan": item.get("origem_planejamento_id"),
        "b2c_ok": (body.get("b2c_dispatch") or {}).get("ok"),
    }


def lookup(plan_id, prof_id):
    from b2c_integration_service import lookup_planejamento_b2c

    return lookup_planejamento_b2c(id_externo=str(plan_id), professor_b2c_id=prof_id)


def main():
    from app import app

    u = user()
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = u

    out = {"git": None}
    h = c.get("/api/health")
    out["git"] = (h.get_json(silent=True) or {}).get("git_sha")

    alocs = (c.get("/api/secretaria/alocacoes").get_json(silent=True) or {}).get("items") or []
    picked = next((x for x in alocs if x.get("turma_id") and x.get("ativo")), None)
    if not picked:
        print(json.dumps({"ok": False, "error": "sem alocacao"}, ensure_ascii=True))
        return 1
    prof_id = picked.get("professor_b2c_id")
    try:
        prof_id = int(prof_id) if prof_id else None
    except (TypeError, ValueError):
        prof_id = None

    day = date.today() + timedelta(days=52)
    start = datetime(day.year, day.month, day.day, 8, 0, tzinfo=TZ)
    payload = {
        "tipo_evento": "aula",
        "titulo": f"{MARKER} aula",
        "descricao": MARKER,
        "data_hora_inicio": start.isoformat(),
        "data_hora_fim": start.replace(minute=50).isoformat(),
        "turma_id": picked["turma_id"],
        "disciplina_id": picked["disciplina_id"],
    }

    r1 = c.post("/api/secretaria/eventos", json=payload)
    b1 = slim(r1)
    plan_id = b1.get("origem_plan")
    na_agenda = lookup(plan_id, prof_id) if plan_id else {}
    resp_ag = na_agenda.get("response") if isinstance(na_agenda.get("response"), dict) else {}
    out["criar_aparece_b2c"] = {
        "create": b1,
        "lookup": {
            "http": na_agenda.get("status_code"),
            "na_agenda": resp_ag.get("na_agenda"),
            "n_agenda": len(resp_ag.get("agenda") or []),
        },
        "ok": b1.get("http") in (200, 201) and bool(resp_ag.get("na_agenda")),
    }

    r_can = c.patch(f"/api/secretaria/eventos/{b1.get('id')}", json={"status": "cancelado"})
    b_can = slim(r_can)
    after = lookup(plan_id, prof_id) if plan_id else {}
    resp_after = after.get("response") if isinstance(after.get("response"), dict) else {}
    again = lookup(plan_id, prof_id) if plan_id else {}
    resp_again = again.get("response") if isinstance(again.get("response"), dict) else {}
    out["cancelar_some_b2c"] = {
        "cancel": b_can,
        "lookup": {"na_agenda": resp_after.get("na_agenda"), "n_agenda": len(resp_after.get("agenda") or [])},
        "ok": b_can.get("http") == 200 and resp_after.get("na_agenda") is False,
    }
    out["persistiu_reabrir"] = {
        "na_agenda": resp_again.get("na_agenda"),
        "ok": resp_again.get("na_agenda") is False,
    }

    r2 = c.post(
        "/api/secretaria/eventos",
        json={**payload, "titulo": f"{MARKER} aula no slot liberado"},
    )
    b2 = slim(r2)
    out["slot_liberado_104"] = {
        "recreate": b2,
        "ok": b2.get("http") in (200, 201) and b2.get("code") != "CONFLITO_HORARIO",
    }

    r_bc = c.post(
        "/api/secretaria/eventos",
        json={
            "tipo_evento": "geral",
            "titulo": f"{MARKER} broadcast",
            "descricao": MARKER,
            "data_hora_inicio": start.replace(hour=15).isoformat(),
            "publico_alvo": "professores",
        },
    )
    bbc = slim(r_bc)
    r_bcc = c.patch(f"/api/secretaria/eventos/{bbc.get('id')}", json={"status": "cancelado"})
    out["regressao_broadcast_114"] = {
        "create": bbc,
        "cancel": slim(r_bcc),
        "ok": bbc.get("http") in (200, 201) and r_bcc.status_code == 200,
    }
    out["regressao_criar_aula_153"] = {"ok": b1.get("http") in (200, 201) and b1.get("status") == "enviado"}

    cleanup = {}
    with get_conn() as conn:
        with conn.cursor() as cur:
            for eid in (b1.get("id"), b2.get("id"), bbc.get("id")):
                if eid:
                    cur.execute("DELETE FROM public.school_eventos WHERE id = %s", (eid,))
                    cleanup[str(eid)] = cur.rowcount
            cur.execute(
                "DELETE FROM public.school_comunicacoes_eventos WHERE titulo LIKE %s",
                (MARKER + "%",),
            )
            cleanup["comunicados"] = cur.rowcount
            cur.execute(
                "DELETE FROM public.school_planejamento_escolar WHERE titulo LIKE %s",
                (MARKER + "%",),
            )
            cleanup["planejamento"] = cur.rowcount
    if b2.get("origem_plan"):
        from b2c_integration_service import cancel_planejamento_to_b2c

        cancel_planejamento_to_b2c(
            {"id_externo": b2["origem_plan"], "professor_b2c_id": prof_id}
        )
    out["cleanup"] = cleanup
    out["ok"] = bool(
        out["criar_aparece_b2c"]["ok"]
        and out["cancelar_some_b2c"]["ok"]
        and out["persistiu_reabrir"]["ok"]
        and out["slot_liberado_104"]["ok"]
        and out["regressao_broadcast_114"]["ok"]
        and out["regressao_criar_aula_153"]["ok"]
    )
    print(json.dumps(out, ensure_ascii=True, indent=2, default=str))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
