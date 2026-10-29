#!/usr/bin/env python3
"""Varredura 113 — CRUD comunicados Escola Teste. Sem senhas. Sem correção.

Phases: create | edit | edges | cancel | cleanup
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
OPER = "operacional@escolateste.edu.br"
MARKER = "[TESTE VARREDURA 113]"
TURMA_A = "537b057f-faf3-4d89-90f3-22f9f0d71764"  # 1ª Série A — homologador alocado
TURMA_B = "9eacd266-547a-4baf-8fe8-cdffb5bb1903"  # 1ª Série B — homologador NÃO
STATE = Path("/tmp/scan-113-state.json")


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


def list_com(c):
    r = c.get("/api/secretaria/comunicacoes")
    body = r.get_json(silent=True) or {}
    return r.status_code, body


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
        "descricao": (item.get("descricao") or "")[:120],
        "tipo": item.get("tipo"),
        "publico_alvo": item.get("publico_alvo"),
        "status": item.get("status"),
        "data_hora_inicio": item.get("data_hora_inicio"),
        "data_hora_fim": item.get("data_hora_fim"),
        "turma_id": item.get("turma_id"),
        "turma_nome": item.get("turma_nome"),
        "replicado_b2c": item.get("replicado_b2c"),
    }


def slim_dispatch(d: dict | None) -> dict | None:
    if not d:
        return None
    return {
        "ok": d.get("ok"),
        "error": d.get("error"),
        "skipped": d.get("skipped"),
        "status_code": d.get("status_code"),
        "destinatarios": (d.get("response") and None) or d.get("destinatarios"),
        "professor_b2c_ids": d.get("professor_b2c_ids"),
        "response_head": str(d.get("response") or "")[:240],
    }


def dt_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def phase_create():
    c, user = client()
    now = datetime.now().replace(microsecond=0)
    inicio = now + timedelta(hours=2)
    fim = inicio + timedelta(hours=1)
    out = {"user": user["email"], "zonas": user["zonas"], "list_before": None, "creates": {}}

    code, listed = list_com(c)
    items = listed.get("items") or []
    out["list_before"] = {
        "http": code,
        "n": len(items),
        "titulos": [i.get("titulo") for i in items],
    }

    payloads = {
        "todos": {
            "titulo": f"{MARKER} todos os professores",
            "descricao": f"{MARKER} corpo — público professores (toda a equipe com conta B2C).",
            "tipo": "evento_escolar",
            "publico_alvo": "professores",
            "data_hora_inicio": dt_iso(inicio),
            "data_hora_fim": dt_iso(fim),
            "status": "publicado",
        },
        "turma_a": {
            "titulo": f"{MARKER} turma 1a Serie A",
            "descricao": f"{MARKER} só professores alocados à 1ª Série A.",
            "tipo": "reuniao_pedagogica",
            "publico_alvo": "turma",
            "turma_id": TURMA_A,
            "data_hora_inicio": dt_iso(inicio + timedelta(minutes=10)),
            "data_hora_fim": dt_iso(fim + timedelta(minutes=10)),
            "status": "publicado",
        },
        "turma_b": {
            "titulo": f"{MARKER} turma 1a Serie B",
            "descricao": f"{MARKER} só 1ª Série B — homologador NÃO está alocado.",
            "tipo": "evento_escolar",
            "publico_alvo": "turma",
            "turma_id": TURMA_B,
            "data_hora_inicio": dt_iso(inicio + timedelta(minutes=20)),
            "data_hora_fim": dt_iso(fim + timedelta(minutes=20)),
            "status": "publicado",
        },
        "expirado": {
            "titulo": f"{MARKER} expirado",
            "descricao": f"{MARKER} vigência no passado — deve sumir do mural se houver filtro.",
            "tipo": "evento_escolar",
            "publico_alvo": "professores",
            "data_hora_inicio": "2026-01-10T10:00:00",
            "data_hora_fim": "2026-01-10T11:00:00",
            "status": "publicado",
        },
    }

    st = load_state()
    st.setdefault("ids", {})
    for key, payload in payloads.items():
        http, body = post_com(c, payload)
        item = body.get("item") or {}
        st["ids"][key] = item.get("id")
        out["creates"][key] = {
            "http": http,
            "message": body.get("message"),
            "item": slim_item(item),
            "b2c_dispatch": slim_dispatch(body.get("b2c_dispatch")),
        }

    code2, listed2 = list_com(c)
    marker_items = [i for i in (listed2.get("items") or []) if MARKER in (i.get("titulo") or "")]
    out["list_after_create"] = {
        "http": code2,
        "n_total": len(listed2.get("items") or []),
        "n_marker": len(marker_items),
        "titulos_marker": [i.get("titulo") for i in marker_items],
        "status_marker": [i.get("status") for i in marker_items],
    }
    save_state(st)
    out["ids"] = st["ids"]
    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_edit():
    c, _ = client()
    st = load_state()
    cid = (st.get("ids") or {}).get("todos")
    out = {"edit_id": cid}
    if not cid:
        out["error"] = "id todos ausente"
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    http, body = patch_com(
        c,
        cid,
        {
            "titulo": f"{MARKER} todos os professores EDITADO",
            "descricao": f"{MARKER} corpo editado — persistência PATCH.",
            "publico_alvo": "toda_instituicao",
        },
    )
    out["http"] = http
    out["message"] = body.get("message")
    out["item"] = slim_item(body.get("item"))
    out["b2c_dispatch"] = slim_dispatch(body.get("b2c_dispatch"))
    code, listed = list_com(c)
    found = next((i for i in (listed.get("items") or []) if i.get("id") == cid), None)
    out["reload"] = {"http": code, "found": slim_item(found)}
    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_edges():
    c, _ = client()
    now = datetime.now().replace(microsecond=0)
    inicio = now + timedelta(hours=3)
    out = {}

    http, body = post_com(
        c,
        {
            "titulo": f"{MARKER} sem publico_alvo campo omitido",
            "descricao": f"{MARKER} omitido",
            "tipo": "evento_escolar",
            "data_hora_inicio": dt_iso(inicio),
            "status": "publicado",
        },
    )
    out["omit_publico"] = {
        "http": http,
        "error": (body or {}).get("error"),
        "item": slim_item((body or {}).get("item")),
        "publico_alvo": ((body or {}).get("item") or {}).get("publico_alvo"),
        "message": (body or {}).get("message"),
        "b2c_dispatch": slim_dispatch((body or {}).get("b2c_dispatch")),
    }
    if ((body or {}).get("item") or {}).get("id"):
        st = load_state()
        st.setdefault("ids", {})["omit_publico"] = body["item"]["id"]
        save_state(st)

    http2, body2 = post_com(
        c,
        {
            "titulo": f"{MARKER} publico vazio",
            "descricao": f"{MARKER} string vazia",
            "tipo": "evento_escolar",
            "publico_alvo": "",
            "data_hora_inicio": dt_iso(inicio),
            "status": "publicado",
        },
    )
    out["publico_vazio"] = {
        "http": http2,
        "error": (body2 or {}).get("error"),
        "item": slim_item((body2 or {}).get("item")),
    }

    http3, body3 = post_com(
        c,
        {
            "titulo": f"{MARKER} disciplina inexistente",
            "descricao": f"{MARKER}",
            "tipo": "evento_escolar",
            "publico_alvo": "disciplina",
            "data_hora_inicio": dt_iso(inicio),
            "status": "publicado",
        },
    )
    out["publico_disciplina"] = {
        "http": http3,
        "error": (body3 or {}).get("error"),
    }

    http4, body4 = post_com(
        c,
        {
            "titulo": f"{MARKER} sem data_hora_inicio",
            "descricao": f"{MARKER}",
            "tipo": "evento_escolar",
            "publico_alvo": "professores",
            "status": "publicado",
        },
    )
    out["sem_inicio"] = {
        "http": http4,
        "error": (body4 or {}).get("error"),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_cancel():
    c, _ = client()
    st = load_state()
    ids = [v for v in (st.get("ids") or {}).values() if v]
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, titulo, status FROM public.school_comunicacoes_eventos
                WHERE instituicao_id = %s AND titulo LIKE %s
                """,
                (INST, f"%{MARKER}%"),
            )
            extra = [str(r["id"]) for r in cur.fetchall() or []]
    for cid in extra:
        if cid not in ids:
            ids.append(cid)

    out = {"cancelled": []}
    for cid in ids:
        http, body = patch_com(c, cid, {"status": "cancelado"})
        out["cancelled"].append(
            {
                "id": cid,
                "http": http,
                "message": body.get("message"),
                "item": slim_item(body.get("item")),
                "b2c_dispatch": slim_dispatch(body.get("b2c_dispatch")),
            }
        )
    code, listed = list_com(c)
    marker = [i for i in (listed.get("items") or []) if MARKER in (i.get("titulo") or "")]
    out["reload"] = {
        "http": code,
        "n_marker": len(marker),
        "status": [i.get("status") for i in marker],
        "titulos": [i.get("titulo") for i in marker],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_cleanup():
    """Remove linhas de teste do School (higiene). Produto não tem DELETE."""
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
    print(json.dumps({"deleted": [{"id": str(r["id"]), "titulo": r["titulo"], "status": r["status"]} for r in deleted]}, ensure_ascii=False, indent=2))


def main():
    phase = (sys.argv[1] if len(sys.argv) > 1 else "create").strip()
    fn = {
        "create": phase_create,
        "edit": phase_edit,
        "edges": phase_edges,
        "cancel": phase_cancel,
        "cleanup": phase_cleanup,
    }.get(phase)
    if not fn:
        raise SystemExit(f"phase inválida: {phase}")
    fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
