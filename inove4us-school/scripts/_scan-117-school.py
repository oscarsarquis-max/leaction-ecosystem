#!/usr/bin/env python3
"""117 — School: convite / disparo / revogar / aceite webhook. Prefixo varredura117."""
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
TEST_EMAIL = "varredura117@leaction.com.br"
STATE = Path("/tmp/scan-117-state.json")


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
                raise SystemExit("homologador não encontrado")
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
    return c


def slim_m(m):
    if not isinstance(m, dict):
        return m
    return {
        "id": m.get("id"),
        "email": m.get("email"),
        "status": m.get("status"),
        "status_vinculo": m.get("status_vinculo"),
        "professor_b2c_id": m.get("professor_b2c_id"),
    }


def list_equipe(c):
    r = c.get("/api/equipe")
    body = r.get_json(silent=True) or {}
    membros = body.get("membros") or []
    return {
        "http": r.status_code,
        "n": len(membros),
        "membros": [slim_m(m) for m in membros],
        "licencas": body.get("licencas"),
    }


def alocacoes_secret(c, email: str):
    r = c.get("/api/secretaria/alocacoes")
    body = r.get_json(silent=True) or {}
    items = body.get("items") or []
    if not isinstance(items, list):
        items = []
    hit = [
        x
        for x in items
        if email in str(x.get("professor_email") or "").lower()
        or str(x.get("professor_b2c_id") or "") == "21"
    ]
    def slim_a(x):
        return {
            "id": x.get("id"),
            "professor_email": x.get("professor_email"),
            "professor_b2c_id": x.get("professor_b2c_id"),
            "turma_nome": x.get("turma_nome"),
            "disciplina_nome": x.get("disciplina_nome"),
            "periodo_nome": x.get("periodo_nome"),
            "ativo": x.get("ativo"),
        }
    return {
        "http": r.status_code,
        "n_total": len(items),
        "n_hit": len(hit),
        "amostra": [slim_a(x) for x in hit[:8]],
    }


def phase_test():
    c = client()
    out = {"equipe_antes": list_equipe(c)}
    out["alocacoes_homolog"] = alocacoes_secret(c, HOMOLOG)

    ja = next(
        (
            m
            for m in (out["equipe_antes"].get("membros") or [])
            if (m.get("email") or "").lower() == TEST_EMAIL
        ),
        None,
    )
    if ja and ja.get("status_vinculo") not in ("revogado", None) and ja.get("status") != "Revogado":
        out["convite"] = {"skipped": "ja_na_lista", "membro": ja}
        vid = ja.get("id")
    else:
        conv = c.post("/api/equipe/convites", json={"email": TEST_EMAIL})
        cb = conv.get_json(silent=True) or {}
        out["convite"] = {
            "http": conv.status_code,
            "error": cb.get("error"),
            "membro": slim_m(cb.get("membro") or {}),
        }
        vid = (cb.get("membro") or {}).get("id")

    out["convite_homolog_ja_vinculado"] = None
    dup = c.post("/api/equipe/convites", json={"email": HOMOLOG})
    db = dup.get_json(silent=True) or {}
    out["convite_homolog_ja_vinculado"] = {
        "http": dup.status_code,
        "error": db.get("error"),
        "membro": slim_m(db.get("membro") or {}) if db.get("membro") else None,
    }

    if vid:
        disp = c.post(f"/api/equipe/{vid}/disparar-convite")
        dbody = disp.get_json(silent=True) or {}
        push = dbody.get("b2c_push") or {}
        out["disparo"] = {
            "http": disp.status_code,
            "ok": dbody.get("ok"),
            "email": dbody.get("email"),
            "invite_url": dbody.get("invite_url"),
            "status_vinculo": dbody.get("status_vinculo"),
            "mensagem": dbody.get("mensagem"),
            "b2c_push_ok": push.get("ok"),
            "b2c_push_status": push.get("status_code") or push.get("http") or push.get("status"),
            "b2c_push_event": (push.get("response") or push).get("event_type")
            if isinstance(push.get("response"), dict)
            else push.get("event_type"),
            "b2c_push": {
                k: push.get(k)
                for k in ("ok", "status_code", "event_type", "error", "handled")
                if k in push or True
            },
        }
        # trim push
        raw = dict(push)
        if "response" in raw and isinstance(raw["response"], str):
            raw["response"] = raw["response"][:500]
        out["disparo"]["b2c_push"] = raw

    out["equipe_pos_convite"] = list_equipe(c)
    test_row = next(
        (
            m
            for m in (out["equipe_pos_convite"].get("membros") or [])
            if (m.get("email") or "").lower() == TEST_EMAIL
        ),
        None,
    )
    out["teste_status"] = test_row
    STATE.write_text(
        json.dumps({"vinculo_id": vid, "email": TEST_EMAIL}, ensure_ascii=False),
        encoding="utf-8",
    )

    # Borda: aceite de convite revogado (handler School, mesmo caminho do webhook)
    if vid:
        rev = c.post(f"/api/equipe/{vid}/revogar")
        rb = rev.get_json(silent=True) or {}
        out["revogar_para_borda"] = {"http": rev.status_code, "ok": rb.get("ok"), "error": rb.get("error")}
        from webhook_b2c_routes import _handle_teacher_invite_accepted

        acc_rev = _handle_teacher_invite_accepted(
            {
                "professor_b2c_id": 21,
                "email": TEST_EMAIL,
                "professor_email": TEST_EMAIL,
                "instituicao_id": INST,
                "vinculo_id": vid,
            }
        )
        out["aceite_apos_revogar"] = acc_rev

        # reconvida para o ciclo de aceite real (B2C) — pendente de novo
        recon = c.post("/api/equipe/convites", json={"email": TEST_EMAIL})
        rcb = recon.get_json(silent=True) or {}
        out["reconvite"] = {
            "http": recon.status_code,
            "error": rcb.get("error"),
            "membro": slim_m(rcb.get("membro") or {}),
        }
        vid2 = (rcb.get("membro") or {}).get("id") or vid
        if vid2:
            disp2 = c.post(f"/api/equipe/{vid2}/disparar-convite")
            d2 = disp2.get_json(silent=True) or {}
            out["redisparo"] = {
                "http": disp2.status_code,
                "ok": d2.get("ok"),
                "b2c_push_ok": (d2.get("b2c_push") or {}).get("ok"),
                "invite_url": d2.get("invite_url"),
            }
            STATE.write_text(
                json.dumps({"vinculo_id": vid2, "email": TEST_EMAIL}, ensure_ascii=False),
                encoding="utf-8",
            )

    # Expirado: não existe status no domínio
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='school_professores_vinculo'
                ORDER BY ordinal_position
                """
            )
            cols = [r[0] for r in cur.fetchall()]
    out["vinculo_colunas"] = cols
    out["tem_campo_expiracao"] = any("expir" in x for x in cols)

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


def phase_cleanup():
    c = client()
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    vid = st.get("vinculo_id")
    out = {"state": st}
    eq = list_equipe(c)
    hits = [
        m
        for m in (eq.get("membros") or [])
        if (m.get("email") or "").lower() == TEST_EMAIL
    ]
    out["hits_antes"] = hits
    revoked = []
    for m in hits:
        if m.get("status_vinculo") == "revogado" or m.get("status") == "Revogado":
            continue
        r = c.post(f"/api/equipe/{m['id']}/revogar")
        revoked.append({"id": m["id"], "http": r.status_code, "body": r.get_json(silent=True)})
    if vid and not hits:
        r = c.post(f"/api/equipe/{vid}/revogar")
        revoked.append({"id": vid, "http": r.status_code, "body": r.get_json(silent=True)})
    out["revogados"] = revoked
    out["equipe_depois"] = [
        slim_m(m)
        for m in (list_equipe(c).get("membros") or [])
        if (m.get("email") or "").lower() == TEST_EMAIL
    ]
    if STATE.exists():
        STATE.unlink()
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


def main():
    phase = (sys.argv[1] if len(sys.argv) > 1 else "test").strip()
    if phase == "cleanup":
        phase_cleanup()
    else:
        phase_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
