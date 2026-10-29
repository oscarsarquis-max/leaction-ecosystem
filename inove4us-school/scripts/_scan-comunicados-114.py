#!/usr/bin/env python3
"""Prompt 114 — CRUD comunicados Escola Teste. Prefixo [TESTE VARREDURA 114]. Sem senhas.

Phases: create | edit | edges | cancel | cleanup
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
MARKER = "[TESTE VARREDURA 114]"
TURMA_A = "537b057f-faf3-4d89-90f3-22f9f0d71764"  # 1ª Série A — homologador alocado
TURMA_B = "9eacd266-547a-4baf-8fe8-cdffb5bb1903"  # 1ª Série B — homologador NÃO
TZ = ZoneInfo("America/Sao_Paulo")
STATE = Path("/tmp/scan-114-state.json")


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
        "disciplina_id": item.get("disciplina_id"),
        "disciplina_nome": item.get("disciplina_nome"),
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
        "destinatarios": d.get("destinatarios"),
        "professor_b2c_ids": d.get("professor_b2c_ids"),
        "response_head": str(d.get("response") or "")[:240],
    }


def dt_local(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ).strftime("%Y-%m-%dT%H:%M:%S")


def disc_ids():
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
            mine = cur.fetchone()
            cur.execute(
                """
                SELECT d.id, d.nome
                FROM public.school_disciplinas d
                WHERE d.instituicao_id = %s
                  AND d.ativo IS NOT FALSE
                  AND (%s IS NULL OR d.id <> %s)
                ORDER BY d.nome
                LIMIT 1
                """,
                (INST, mine["id"] if mine else None, mine["id"] if mine else None),
            )
            other = cur.fetchone()
    return (
        {"id": str(mine["id"]), "nome": mine["nome"]} if mine else None,
        {"id": str(other["id"]), "nome": other["nome"]} if other else None,
    )


def phase_create():
    c, user = client()
    now = datetime.now(TZ).replace(microsecond=0)
    inicio = now + timedelta(hours=2)
    fim = inicio + timedelta(hours=1)
    disc_mine, disc_other = disc_ids()
    out = {
        "user": user["email"],
        "zonas": user["zonas"],
        "now_br": now.isoformat(),
        "disc_mine": disc_mine,
        "disc_other": disc_other,
        "creates": {},
    }

    payloads = {
        "agora": {
            "titulo": f"{MARKER} publicado agora fuso",
            "descricao": f"{MARKER} publicado neste instante — mural e agenda devem cair no mesmo dia BR.",
            "tipo": "evento_escolar",
            "publico_alvo": "professores",
            "data_hora_inicio": dt_local(now),
            "data_hora_fim": dt_local(now + timedelta(days=2)),
            "status": "publicado",
        },
        "futuro": {
            "titulo": f"{MARKER} vigencia futura",
            "descricao": f"{MARKER} data_hora_fim no futuro — deve aparecer.",
            "tipo": "evento_escolar",
            "publico_alvo": "professores",
            "data_hora_inicio": dt_local(inicio),
            "data_hora_fim": dt_local(fim),
            "status": "publicado",
        },
        "expirado": {
            "titulo": f"{MARKER} vigencia expirada",
            "descricao": f"{MARKER} data_hora_fim no passado — NÃO deve aparecer no mural nem na agenda.",
            "tipo": "evento_escolar",
            "publico_alvo": "professores",
            "data_hora_inicio": "2026-01-10T10:00:00",
            "data_hora_fim": "2026-01-10T11:00:00",
            "status": "publicado",
        },
        "turma_a": {
            "titulo": f"{MARKER} turma 1a Serie A",
            "descricao": f"{MARKER} só professores alocados à 1ª Série A.",
            "tipo": "reuniao_pedagogica",
            "publico_alvo": "turma",
            "turma_id": TURMA_A,
            "data_hora_inicio": dt_local(inicio + timedelta(minutes=10)),
            "data_hora_fim": dt_local(fim + timedelta(minutes=10)),
            "status": "publicado",
        },
        "turma_b": {
            "titulo": f"{MARKER} turma 1a Serie B",
            "descricao": f"{MARKER} só 1ª Série B — homologador NÃO está alocado.",
            "tipo": "evento_escolar",
            "publico_alvo": "turma",
            "turma_id": TURMA_B,
            "data_hora_inicio": dt_local(inicio + timedelta(minutes=20)),
            "data_hora_fim": dt_local(fim + timedelta(minutes=20)),
            "status": "publicado",
        },
    }
    if disc_mine:
        payloads["disciplina"] = {
            "titulo": f"{MARKER} disciplina {disc_mine['nome']}",
            "descricao": f"{MARKER} só professores alocados em {disc_mine['nome']}.",
            "tipo": "evento_escolar",
            "publico_alvo": "disciplina",
            "disciplina_id": disc_mine["id"],
            "data_hora_inicio": dt_local(inicio + timedelta(minutes=30)),
            "data_hora_fim": dt_local(fim + timedelta(minutes=30)),
            "status": "publicado",
        }
    if disc_other:
        payloads["disciplina_outra"] = {
            "titulo": f"{MARKER} disciplina {disc_other['nome']} (homologador nao)",
            "descricao": f"{MARKER} disciplina sem alocação do homologador.",
            "tipo": "evento_escolar",
            "publico_alvo": "disciplina",
            "disciplina_id": disc_other["id"],
            "data_hora_inicio": dt_local(inicio + timedelta(minutes=40)),
            "data_hora_fim": dt_local(fim + timedelta(minutes=40)),
            "status": "publicado",
        }

    st = load_state()
    st.setdefault("ids", {})
    for key, payload in payloads.items():
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
    cid = (st.get("ids") or {}).get("futuro")
    out = {"edit_id": cid}
    if not cid:
        out["error"] = "id futuro ausente"
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    http, body = patch_com(
        c,
        cid,
        {
            "titulo": f"{MARKER} vigencia futura EDITADO",
            "descricao": f"{MARKER} corpo editado — persistência PATCH.",
        },
    )
    out["http"] = http
    out["error"] = body.get("error")
    out["message"] = body.get("message")
    out["item"] = slim_item(body.get("item"))
    out["b2c_dispatch"] = slim_dispatch(body.get("b2c_dispatch"))
    code, listed = list_com(c)
    found = next((i for i in (listed.get("items") or []) if i.get("id") == cid), None)
    out["reload"] = {"http": code, "found": slim_item(found)}
    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_edges():
    c, _ = client()
    now = datetime.now(TZ).replace(microsecond=0)
    inicio = now + timedelta(hours=3)
    out = {}

    http, body = post_com(
        c,
        {
            "titulo": f"{MARKER} sem publico_alvo campo omitido",
            "descricao": f"{MARKER} omitido",
            "tipo": "evento_escolar",
            "data_hora_inicio": dt_local(inicio),
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
            "data_hora_inicio": dt_local(inicio),
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
            "titulo": f"{MARKER} disciplina sem id",
            "descricao": f"{MARKER}",
            "tipo": "evento_escolar",
            "publico_alvo": "disciplina",
            "data_hora_inicio": dt_local(inicio),
            "status": "publicado",
        },
    )
    out["disciplina_sem_id"] = {
        "http": http3,
        "error": (body3 or {}).get("error"),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_cancel():
    c, _ = client()
    st = load_state()
    cid = (st.get("ids") or {}).get("agora")
    out = {"cancel_id": cid}
    if not cid:
        out["error"] = "id agora ausente"
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
    ids = []
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
        cancelled.append({"id": cid, "http": http, "ok": (body.get("item") or {}).get("status")})
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
