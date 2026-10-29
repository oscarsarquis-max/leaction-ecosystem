#!/usr/bin/env python3
"""118 — backfill TEACHER_ALLOCATED + teste alocação nova + regressão 117."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"
MISSING = "391f21a4-e97d-49f1-b6aa-0b8181b578c8"


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

    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = gestor()
    return c


def audit():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT a.id, a.notificado_b2c, a.ativo, a.created_at,
                       v.email_convite, t.nome AS turma, d.nome AS disciplina
                FROM public.school_alocacoes_docentes a
                JOIN public.school_professores_vinculo v ON v.id = a.professor_vinculo_id
                JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                WHERE a.instituicao_id = %s
                ORDER BY a.created_at
                """,
                (INST,),
            )
            rows = [dict(r) for r in cur.fetchall() or []]
    pending = [
        {
            "id": str(r["id"]),
            "email": r.get("email_convite"),
            "turma": r.get("turma"),
            "disciplina": r.get("disciplina"),
            "created_at": str(r.get("created_at")),
        }
        for r in rows
        if r.get("ativo") and not r.get("notificado_b2c")
    ]
    return {
        "n": len(rows),
        "ativas": sum(1 for r in rows if r.get("ativo")),
        "pendentes_notify": pending,
        "homolog": [
            {
                "id": str(r["id"]),
                "turma": r.get("turma"),
                "notificado_b2c": bool(r.get("notificado_b2c")),
                "created_at": str(r.get("created_at")),
            }
            for r in rows
            if (r.get("email_convite") or "").lower() == HOMOLOG and r.get("ativo")
        ],
    }


def main():
    phase = (sys.argv[1] if len(sys.argv) > 1 else "audit").strip()
    c = client()
    out: dict = {"phase": phase, "audit_antes": audit()}
    if phase == "audit":
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0

    if phase == "backfill":
        r1 = c.post("/api/secretaria/alocacoes/sincronizar-b2c", json={})
        b1 = r1.get_json(silent=True) or {}
        r2 = c.post(
            "/api/secretaria/alocacoes/sincronizar-b2c",
            json={"force": True, "alocacao_id": MISSING},
        )
        b2 = r2.get_json(silent=True) or {}
        out["backfill_1"] = {
            "http": r1.status_code,
            "n": b1.get("n"),
            "ok": b1.get("ok"),
            "failed": b1.get("failed"),
            "items": b1.get("items"),
        }
        out["backfill_2_force"] = {
            "http": r2.status_code,
            "n": b2.get("n"),
            "ok": b2.get("ok"),
            "failed": b2.get("failed"),
            "items": b2.get("items"),
        }
        out["audit_depois"] = audit()
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0 if out["audit_depois"]["pendentes_notify"] == [] else 1

    if phase == "create":
        alocs = c.get("/api/secretaria/alocacoes").get_json(silent=True) or {}
        items = alocs.get("items") or []
        hom = next(
            (x for x in items if (x.get("professor_email") or "").lower() == HOMOLOG),
            None,
        )
        turmas = (c.get("/api/secretaria/turmas").get_json(silent=True) or {}).get(
            "items"
        ) or []
        discs = (c.get("/api/secretaria/disciplinas").get_json(silent=True) or {}).get(
            "items"
        ) or []
        used = {
            (x.get("turma_id"), x.get("disciplina_id"), x.get("professor_id"))
            for x in items
            if x.get("ativo")
        }
        target = None
        disc_id = (hom or {}).get("disciplina_id")
        disc_nome = (hom or {}).get("disciplina_nome")
        attempts = []
        created = None
        cb = {}
        target = None
        for t in turmas:
            nome_t = t.get("nome") or ""
            if "varredura" in nome_t.lower() or nome_t.startswith("109"):
                continue
            if not t.get("ativa", True):
                continue
            key = (t.get("id"), disc_id, (hom or {}).get("professor_id"))
            if not (hom and disc_id) or key in used:
                continue
            cand = {
                "unidade_id": hom["unidade_id"],
                "periodo_id": hom["periodo_id"],
                "disciplina_id": disc_id,
                "professor_id": hom["professor_id"],
                "turma_id": t["id"],
            }
            created = c.post("/api/secretaria/alocacoes", json=cand)
            cb = created.get_json(silent=True) or {}
            attempts.append(
                {
                    "turma": nome_t,
                    "http": created.status_code,
                    "error": cb.get("error"),
                }
            )
            if created.status_code == 201:
                target = {**cand, "turma_nome": nome_t, "disc_nome": disc_nome}
                break
        out["create_attempts"] = attempts
        out["create_plan"] = target
        if not target:
            print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
            return 2
        item = cb.get("item") or {}
        out["create"] = {
            "http": created.status_code,
            "notificado_b2c": item.get("notificado_b2c"),
            "id": item.get("id"),
            "message": cb.get("message"),
            "dispatch_ok": (cb.get("b2c_dispatch") or {}).get("ok"),
        }
        new_id = item.get("id")
        if new_id:
            off = c.put(
                f"/api/secretaria/alocacoes/{new_id}",
                json={"ativo": False},
            )
            out["deactivate"] = {
                "http": off.status_code,
                "ativo": ((off.get_json(silent=True) or {}).get("item") or {}).get("ativo"),
            }
        out["audit_depois"] = audit()
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0

    if phase == "regressao":
        dup = c.post("/api/equipe/convites", json={"email": HOMOLOG})
        db = dup.get_json(silent=True) or {}
        out["convite_409"] = {"http": dup.status_code, "error": db.get("error")}
        # aceite tardio de revogado: reusa 117 se ainda revogado — cria, revoga, webhook
        from webhook_b2c_routes import _handle_teacher_invite_accepted

        conv = c.post("/api/equipe/convites", json={"email": "varredura118@leaction.com.br"})
        cb = conv.get_json(silent=True) or {}
        vid = (cb.get("membro") or {}).get("id")
        if vid:
            c.post(f"/api/equipe/{vid}/revogar")
            acc = _handle_teacher_invite_accepted(
                {
                    "professor_b2c_id": 21,
                    "email": "varredura118@leaction.com.br",
                    "instituicao_id": INST,
                    "vinculo_id": vid,
                }
            )
            out["aceite_revogado"] = acc
        out["audit"] = audit()
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0

    print(json.dumps({"error": "phase"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
