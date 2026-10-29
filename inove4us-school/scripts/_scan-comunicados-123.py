#!/usr/bin/env python3
"""Prompt 123 — 3 comunicados simultâneos (todos / turma / disciplina). Prefixo [TESTE VARREDURA 123].

Phases: create | late | cleanup
Roda no EC2 School. Sem senhas.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
OPER = "operacional@escolateste.edu.br"
MARKER = "[TESTE VARREDURA 123]"
TURMA_A = "537b057f-faf3-4d89-90f3-22f9f0d71764"  # 1ª Série A — homologador alocado
TZ = ZoneInfo("America/Sao_Paulo")
STATE = Path("/tmp/scan-123-state.json")


def j(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"ids": {}}


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2, default=j), encoding="utf-8")


def gestor_operacional():
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
                (INST, OPER),
            )
            row = cur.fetchone()
            if not row:
                raise SystemExit("gestor operacional não encontrado")
            return {
                "id": str(row["id"]),
                "instituicao_id": str(row["instituicao_id"]),
                "instituicao_nome": row.get("instituicao_nome"),
                "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
                "nome": row["nome"],
                "email": row["email"],
                "cargo": row["cargo"],
                "zonas": list(row["zonas"] or []),
            }


def client():
    from app import app

    user = gestor_operacional()
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = user
    return c, user


def post_com(c, payload):
    r = c.post("/api/secretaria/comunicacoes", json=payload)
    return r.status_code, r.get_json(silent=True) or {}


def patch_com(c, cid, payload):
    r = c.patch(f"/api/secretaria/comunicacoes/{cid}", json=payload)
    return r.status_code, r.get_json(silent=True) or {}


def slim_item(item: dict | None) -> dict | None:
    if not item:
        return None
    return {
        "id": item.get("id"),
        "titulo": item.get("titulo"),
        "tipo": item.get("tipo"),
        "publico_alvo": item.get("publico_alvo"),
        "status": item.get("status"),
        "data_hora_inicio": item.get("data_hora_inicio"),
        "data_hora_fim": item.get("data_hora_fim"),
        "turma_id": item.get("turma_id"),
        "disciplina_id": item.get("disciplina_id"),
        "replicado_b2c": item.get("replicado_b2c"),
    }


def slim_dispatch(d: dict | None) -> dict | None:
    if not d:
        return None
    return {
        "ok": d.get("ok"),
        "error": d.get("error"),
        "destinatarios": d.get("destinatarios"),
        "professor_b2c_ids": d.get("professor_b2c_ids"),
        "status_code": d.get("status_code"),
    }


def dt_local(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ).strftime("%Y-%m-%dT%H:%M:%S")


def disc_mine():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT d.id, d.nome
                FROM public.school_alocacoes_docentes a
                JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                WHERE a.instituicao_id = %s
                  AND lower(v.email_convite) = 'homologador@leaction.com.br'
                  AND a.ativo = TRUE
                ORDER BY d.nome
                LIMIT 1
                """,
                (INST,),
            )
            row = cur.fetchone()
    return {"id": str(row["id"]), "nome": row["nome"]} if row else None


def phase_create():
    c, user = client()
    now = datetime.now(TZ).replace(microsecond=0)
    disc = disc_mine()
    out = {
        "user": user["email"],
        "now_br": now.isoformat(),
        "disc_mine": disc,
        "creates": {},
    }
    # Inícios distintos para conferir ordem DESC no mural (mais recente de vigência primeiro).
    payloads = {
        "disciplina": {
            "titulo": f"{MARKER} disciplina {disc['nome'] if disc else '?'}",
            "descricao": f"{MARKER} público disciplina — homologador alocado.",
            "tipo": "evento_escolar",
            "publico_alvo": "disciplina",
            "disciplina_id": disc["id"] if disc else None,
            "data_hora_inicio": dt_local(now + timedelta(hours=1)),
            "data_hora_fim": dt_local(now + timedelta(days=2)),
            "status": "publicado",
        },
        "turma": {
            "titulo": f"{MARKER} turma 1a Serie A",
            "descricao": f"{MARKER} público turma — 1ª Série A.",
            "tipo": "reuniao_pedagogica",
            "publico_alvo": "turma",
            "turma_id": TURMA_A,
            "data_hora_inicio": dt_local(now + timedelta(hours=2)),
            "data_hora_fim": dt_local(now + timedelta(days=2)),
            "status": "publicado",
        },
        "todos": {
            "titulo": f"{MARKER} todos os professores",
            "descricao": f"{MARKER} público professores (toda a instituição).",
            "tipo": "evento_escolar",
            "publico_alvo": "professores",
            "data_hora_inicio": dt_local(now + timedelta(hours=3)),
            "data_hora_fim": dt_local(now + timedelta(days=2)),
            "status": "publicado",
        },
    }
    if not disc:
        payloads.pop("disciplina")

    st = load_state()
    st.setdefault("ids", {})
    for key, payload in payloads.items():
        if key == "disciplina" and not payload.get("disciplina_id"):
            out["creates"][key] = {"error": "sem disciplina do homologador"}
            continue
        http, body = post_com(c, payload)
        item = body.get("item") or {}
        st["ids"][key] = item.get("id")
        out["creates"][key] = {
            "http": http,
            "error": body.get("error"),
            "message": body.get("message"),
            "item": slim_item(item),
            "b2c_dispatch": slim_dispatch(body.get("b2c_dispatch")),
        }

    save_state(st)
    out["ids"] = st["ids"]
    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_late():
    """4º comunicado — para o caso 'já estava com o mural aberto'."""
    c, _ = client()
    now = datetime.now(TZ).replace(microsecond=0)
    http, body = post_com(
        c,
        {
            "titulo": f"{MARKER} publicado com mural ja aberto",
            "descricao": f"{MARKER} não precisa aparecer em tempo real; deve aparecer no próximo reload.",
            "tipo": "evento_escolar",
            "publico_alvo": "professores",
            "data_hora_inicio": dt_local(now + timedelta(hours=4)),
            "data_hora_fim": dt_local(now + timedelta(days=2)),
            "status": "publicado",
        },
    )
    item = body.get("item") or {}
    st = load_state()
    st.setdefault("ids", {})["late"] = item.get("id")
    save_state(st)
    print(
        json.dumps(
            {
                "http": http,
                "error": body.get("error"),
                "message": body.get("message"),
                "item": slim_item(item),
                "b2c_dispatch": slim_dispatch(body.get("b2c_dispatch")),
                "id": item.get("id"),
            },
            ensure_ascii=False,
            indent=2,
            default=j,
        )
    )


def phase_cancel_todos():
    """Regressão 114: cancelar o de 'todos' e conferir desaparecimento no B2C."""
    c, _ = client()
    st = load_state()
    cid = (st.get("ids") or {}).get("todos")
    out = {"cancel_id": cid}
    if not cid:
        out["error"] = "id todos ausente"
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    http, body = patch_com(c, cid, {"status": "cancelado"})
    out["http"] = http
    out["message"] = body.get("message")
    out["item"] = slim_item(body.get("item"))
    out["b2c_dispatch"] = slim_dispatch(body.get("b2c_dispatch"))
    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_cleanup():
    c, _ = client()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id FROM public.school_comunicacoes_eventos
                WHERE instituicao_id = %s AND titulo LIKE %s
                """,
                (INST, f"%{MARKER}%"),
            )
            ids = [str(r["id"]) for r in cur.fetchall() or []]
    cancelled = []
    for cid in ids:
        http, body = patch_com(c, cid, {"status": "cancelado"})
        cancelled.append({"id": cid, "http": http, "status": (body.get("item") or {}).get("status")})
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                DELETE FROM public.school_comunicacoes_eventos
                WHERE instituicao_id = %s AND titulo LIKE %s
                RETURNING id, titulo, status
                """,
                (INST, f"%{MARKER}%"),
            )
            deleted = [dict(r) for r in cur.fetchall() or []]
    if STATE.exists():
        STATE.unlink()
    print(
        json.dumps(
            {
                "cancelled": cancelled,
                "deleted": [
                    {"id": str(r["id"]), "titulo": r["titulo"], "status": r["status"]} for r in deleted
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main():
    phase = (sys.argv[1] if len(sys.argv) > 1 else "create").strip()
    fn = {
        "create": phase_create,
        "late": phase_late,
        "cancel_todos": phase_cancel_todos,
        "cleanup": phase_cleanup,
    }.get(phase)
    if not fn:
        raise SystemExit(f"phase inválida: {phase}")
    fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
