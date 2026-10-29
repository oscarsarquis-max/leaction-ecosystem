#!/usr/bin/env python3
"""122 — School: duas pendentes na mesma cadeia + retorno + índice 55."""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"
MARKER = "[TESTE VARREDURA 122]"
STATE = Path("/tmp/scan-122-state.json")


def gestor():
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
            row = cur.fetchone()
            if not row:
                raise SystemExit("homologador gestor não encontrado")
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

    user = gestor()
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = user
    return c, user


def is_122(it: dict) -> bool:
    return MARKER in json.dumps(it, ensure_ascii=False, default=str)


def slim(it: dict) -> dict:
    return {
        "id": it.get("id"),
        "metodologia_nome": it.get("metodologia_nome"),
        "professor_label": it.get("professor_label") or it.get("professor_nome"),
        "trecho": (it.get("trecho") or it.get("teacher_adaptation_text") or "")[:180],
        "turma_nome": it.get("turma_nome"),
    }


def main() -> int:
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    c, user = client()
    out: dict = {"prompt": 122, "gestor": user.get("email"), "suffix": st.get("suffix")}

    r = c.get("/api/pedagogico/curadoria-pendente")
    radar = r.get_json(silent=True) or {}
    itens = [slim(it) for it in (radar.get("itens") or []) if is_122(it)]
    textos = [it.get("trecho") or "" for it in itens]
    ids = [it.get("id") for it in itens if it.get("id")]
    has_c = any("proposta C" in t for t in textos)
    has_d = any("proposta D" in t for t in textos)
    has_b = any("proposta B" in t for t in textos)
    out["central"] = {
        "http": r.status_code,
        "n_122": len(itens),
        "ids": ids,
        "tem_c": has_c,
        "tem_d": has_d,
        "tem_b": has_b,
        "duas_na_cadeia": has_c and has_d and len(set(ids)) >= 2,
        "desafio_distinto": has_b,
        "itens": itens,
    }

    # 400 sem retorno
    alvo = ids[0] if ids else None
    if alvo:
        vazio = c.post(f"/api/pedagogico/curadoria/{alvo}/rejeitar", json={})
        bv = vazio.get_json(silent=True) or {}
        out["retorno_obrigatorio"] = {
            "http": vazio.status_code,
            "code": bv.get("code"),
            "ok": vazio.status_code == 400 and bv.get("code") == "RETORNO_DOCENTE_OBRIGATORIO",
        }
        avisos = []
        for i, cid in enumerate(ids):
            rr = c.post(
                f"/api/pedagogico/curadoria/{cid}/rejeitar",
                json={"retorno_docente": f"{MARKER} retorno {i + 1} ({st.get('suffix')})"},
            )
            body = rr.get_json(silent=True) or {}
            aviso = body.get("aviso") if isinstance(body.get("aviso"), dict) else {}
            avisos.append(
                {
                    "http": rr.status_code,
                    "id": cid,
                    "aviso_id": aviso.get("id"),
                    "tipo": aviso.get("tipo"),
                    "ok": rr.status_code in (200, 201),
                }
            )
        out["resolver"] = avisos
        r2 = c.get("/api/pedagogico/curadoria-pendente")
        radar2 = r2.get_json(silent=True) or {}
        rest = [slim(it) for it in (radar2.get("itens") or []) if is_122(it)]
        out["reabrir_central"] = {"http": r2.status_code, "n_122": len(rest), "itens": rest}
    else:
        out["retorno_obrigatorio"] = {"ok": False, "error": "sem pendentes 122"}

    fut_ini = date.today() + timedelta(days=80)
    fut_fim = date.today() + timedelta(days=90)
    rsum = c.get(
        f"/api/pedagogico/calendario-pedagogico/resumo?data_inicio={fut_ini.isoformat()}&data_fim={fut_fim.isoformat()}"
    )
    body_sum = rsum.get_json(silent=True) or {}
    contrib = body_sum.get("contribuicao") if isinstance(body_sum.get("contribuicao"), dict) else {}
    blob = json.dumps(contrib, ensure_ascii=False).lower()
    out["indice_55"] = {
        "http": rsum.status_code,
        "contribuicao": contrib,
        "identifica_individuo": "homologador@" in blob or "professor_email" in blob or "professor_b2c_id" in blob,
        "ok": rsum.status_code == 200 and "homologador@" not in blob,
    }

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text, tipo, professor_b2c_id, left(texto, 200) AS texto
                FROM public.school_avisos_mesa
                WHERE instituicao_id = %s AND texto ILIKE %s
                ORDER BY id DESC
                """,
                (INST, "%" + MARKER + "%"),
            )
            out["avisos_db"] = [dict(r) for r in cur.fetchall() or []]

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
