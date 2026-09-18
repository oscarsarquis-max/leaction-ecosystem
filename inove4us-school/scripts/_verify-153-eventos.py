#!/usr/bin/env python3
"""153 — confirma eventos unificados em produção. Homologador. Limpa o que criar."""
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
MARKER = "[TRIAGEM 153]"
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
        "publico": item.get("publico_alvo"),
    }


def main():
    from app import app

    u = user()
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = u

    out = {"git": None, "migracao": {}, "tipos": {}, "admin": {}, "aula_conflito": {}, "edicao": {}}
    h = c.get("/api/health")
    out["git"] = (h.get_json(silent=True) or {}).get("git_sha")

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*)::int AS n FROM public.school_eventos")
            total = cur.fetchone()["n"]
            cur.execute(
                """
                SELECT tipo_evento, COUNT(*)::int AS n
                  FROM public.school_eventos
                 GROUP BY 1 ORDER BY 1
                """
            )
            by_tipo = {r["tipo_evento"]: r["n"] for r in cur.fetchall()}
            cur.execute("SELECT COUNT(*)::int AS n FROM public.school_comunicacoes_eventos")
            n_com = cur.fetchone()["n"]
            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                  FROM public.school_comunicacoes_eventos c
                  JOIN public.school_eventos e ON e.origem_comunicado_id = c.id
                """
            )
            n_com_mig = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*)::int AS n FROM public.school_planejamento_escolar")
            n_plan = cur.fetchone()["n"]
            cur.execute(
                """
                SELECT COUNT(*)::int AS n
                  FROM public.school_planejamento_escolar p
                  JOIN public.school_eventos e ON e.origem_planejamento_id = p.id
                """
            )
            n_plan_mig = cur.fetchone()["n"]
    out["migracao"] = {
        "eventos": total,
        "por_tipo": by_tipo,
        "comunicados": n_com,
        "comunicados_migrados": n_com_mig,
        "planejamento": n_plan,
        "planejamento_migrado": n_plan_mig,
        "ok": n_com_mig == n_com and n_plan_mig == n_plan,
    }

    listed = c.get("/api/secretaria/eventos")
    items = (listed.get_json(silent=True) or {}).get("items") or []
    out["lista"] = {"http": listed.status_code, "n": len(items)}

    day = date.today() + timedelta(days=47)
    created = []
    for tipo in ("planejamento", "treinamento", "civico", "geral"):
        start = datetime(day.year, day.month, day.day, 10, 0, tzinfo=TZ)
        r = c.post(
            "/api/secretaria/eventos",
            json={
                "tipo_evento": tipo,
                "titulo": f"{MARKER} {tipo}",
                "descricao": MARKER,
                "data_hora_inicio": start.isoformat(),
                "data_hora_fim": start.replace(hour=11).isoformat(),
                "publico_alvo": "professores",
            },
        )
        s = slim(r)
        out["tipos"][tipo] = s
        if s.get("id"):
            created.append(s["id"])

    r_adm = c.post(
        "/api/secretaria/eventos",
        json={
            "tipo_evento": "geral",
            "titulo": f"{MARKER} admin",
            "descricao": MARKER,
            "data_hora_inicio": datetime(day.year, day.month, day.day, 15, 0, tzinfo=TZ).isoformat(),
            "publico_alvo": "administradores",
        },
    )
    s_adm = slim(r_adm)
    out["admin"]["create"] = s_adm
    if s_adm.get("id"):
        created.append(s_adm["id"])
        listed_admin = c.get("/api/secretaria/eventos")
        ids = [(x.get("id"), x.get("publico_alvo")) for x in (listed_admin.get_json(silent=True) or {}).get("items") or []]
        out["admin"]["visivel_admin"] = any(i == s_adm["id"] for i, _ in ids)
        u2 = dict(u)
        u2["zonas"] = [z for z in u2.get("zonas") or [] if z != "administrativo"] or ["operacional"]
        with c.session_transaction() as sess:
            sess["school_gestor"] = u2
        listed_op = c.get("/api/secretaria/eventos")
        ids_op = [x.get("id") for x in (listed_op.get_json(silent=True) or {}).get("items") or []]
        out["admin"]["oculto_operacional"] = s_adm["id"] not in ids_op
        with c.session_transaction() as sess:
            sess["school_gestor"] = u

    alocs = (c.get("/api/secretaria/alocacoes").get_json(silent=True) or {}).get("items") or []
    picked = next((x for x in alocs if x.get("turma_id") and x.get("ativo")), None)
    if not picked:
        out["aula_conflito"] = {"status": "nao_deu_pra_testar"}
    else:
        start = datetime(day.year, day.month, day.day, 8, 0, tzinfo=TZ)
        payload = {
            "tipo_evento": "aula",
            "titulo": f"{MARKER} aula base",
            "descricao": MARKER,
            "data_hora_inicio": start.isoformat(),
            "data_hora_fim": start.replace(minute=50).isoformat(),
            "turma_id": picked["turma_id"],
            "disciplina_id": picked["disciplina_id"],
        }
        r1 = c.post("/api/secretaria/eventos", json=payload)
        b1 = slim(r1)
        r2 = c.post(
            "/api/secretaria/eventos",
            json={**payload, "titulo": f"{MARKER} aula conflito"},
        )
        b2 = slim(r2)
        ok = r1.status_code in (200, 201) and r2.status_code == 409 and b2.get("code") == "CONFLITO_HORARIO"
        if b1.get("id"):
            created.append(b1["id"])
        if b2.get("id"):
            created.append(b2["id"])
        out["aula_conflito"] = {"status": "funcionando" if ok else "quebrado", "base": b1, "conflito": b2}

        if b1.get("id"):
            r_edit = c.patch(
                f"/api/secretaria/eventos/{b1['id']}",
                json={"titulo": f"{MARKER} aula editada"},
            )
            out["edicao"] = slim(r_edit)

    if created and created[0]:
        r_can = c.patch(
            f"/api/secretaria/eventos/{created[0]}",
            json={"status": "cancelado"},
        )
        out["cancelamento"] = slim(r_can)

    cleanup = {}
    with get_conn() as conn:
        with conn.cursor() as cur:
            for eid in created:
                if not eid:
                    continue
                cur.execute(
                    "DELETE FROM public.school_eventos WHERE id = %s AND titulo LIKE %s",
                    (eid, MARKER + "%"),
                )
                cleanup[eid] = cur.rowcount
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
    out["cleanup"] = cleanup

    tipos_ok = all(
        out["tipos"].get(t, {}).get("http") in (200, 201) for t in ("planejamento", "treinamento", "civico", "geral")
    )
    out["ok"] = bool(
        out["migracao"].get("ok")
        and tipos_ok
        and out["admin"].get("create", {}).get("http") in (200, 201)
        and out["admin"].get("visivel_admin")
        and out["admin"].get("oculto_operacional")
        and out["aula_conflito"].get("status") in ("funcionando", "nao_deu_pra_testar")
    )
    print(json.dumps(out, ensure_ascii=True, indent=2, default=str))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
