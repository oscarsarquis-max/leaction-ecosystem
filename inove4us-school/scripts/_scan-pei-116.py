#!/usr/bin/env python3
"""116 — testes PEI TEA + amostra + 409 + limpeza. Prefixo [TESTE VARREDURA 116]."""
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
MARKER = "[TESTE VARREDURA 116]"
TURMA_A = "537b057f-faf3-4d89-90f3-22f9f0d71764"
PERIOD = "68a38cc9-b975-4411-815e-b1fcef171c3d"
LUCAS_PEI = "88da0eae-5446-4ec7-9c96-f88f63d37c33"
STATE = Path("/tmp/scan-116-state.json")


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

    user = gestor()
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = user
    return c


def slim_pei(p):
    if not isinstance(p, dict) or not p.get("id"):
        return p
    return {
        "id": p.get("id"),
        "nome": p.get("nome_completo"),
        "condicao": p.get("condicao_categoria"),
        "status": p.get("status"),
        "status_assinatura": p.get("status_assinatura"),
        "status_assinatura_label": p.get("status_assinatura_label"),
        "valido": p.get("valido"),
        "coord": p.get("assinado_coordenador"),
        "psico": p.get("assinado_psicopedagogo"),
        "aee_matriz_id": p.get("aee_matriz_id"),
        "aee_versao": p.get("aee_versao"),
        "periodo_letivo_id": p.get("periodo_letivo_id"),
    }


def heranca_81(c, pei: dict) -> dict:
    aid = pei.get("aee_matriz_id")
    cond = pei.get("condicao_categoria") or pei.get("condicao")
    r = c.get(f"/api/aee/{aid}/metodologias")
    body = r.get_json(silent=True) or {}
    items = body.get("items") or []
    origens = sorted({str(i.get("origem_texto")) for i in items})
    n_adapt = sum(1 for i in items if i.get("origem_texto") == "adaptacao_canonica")
    n_cat = sum(1 for i in items if i.get("origem_texto") == "catalogo")
    hit = next((i for i in items if i.get("is_customizado")), None) or (items[0] if items else {})
    servido = (hit.get("versao_escola") or "") if hit else ""
    canon_met = (hit.get("texto_canonico") or "") if hit else ""
    return {
        "http": r.status_code,
        "n": len(items),
        "origens": origens,
        "n_adaptacao_canonica": n_adapt,
        "n_catalogo": n_cat,
        "herda_81": n_adapt >= 30 and n_cat == 0,
        "amostra_metodo": hit.get("nome") if hit else None,
        "servido_diferente_catalogo": bool(servido) and servido != canon_met,
        "preview": servido[:160],
        "condicao": cond,
    }


def phase_test():
    c = client()
    out = {}
    conds = c.get("/api/aee/condicoes").get_json(silent=True) or []
    nomes = [x.get("condicao_categoria") for x in conds] if isinstance(conds, list) else []
    estados = []
    for nome in nomes:
        b = c.get("/api/aee/matriz", query_string={"condicao": nome}).get_json(silent=True) or {}
        a = b.get("ativa") or {}
        estados.append({"condicao": nome, "ativa": a.get("status"), "versao": a.get("versao"), "id": a.get("id")})
    out["oito"] = estados
    out["todas_ativas"] = all(e.get("ativa") == "ativo" for e in estados) and len(estados) == 8

    tdah = c.get("/api/aee/matriz", query_string={"condicao": "TDAH"}).get_json(silent=True) or {}
    out["reg_tdah"] = {
        "ativa": (tdah.get("ativa") or {}).get("status"),
        "aguardando": (tdah.get("aguardando") or {}).get("status") if tdah.get("aguardando") else None,
        "coord": (tdah.get("ativa") or {}).get("assinado_coordenador"),
        "psico": (tdah.get("ativa") or {}).get("assinado_psicopedagogo"),
    }

    al = c.post(
        "/api/secretaria/alunos",
        json={"nome": f"{MARKER} Aluno PEI", "matricula": "116PEI001", "turma_id": TURMA_A},
    )
    aluno = (al.get_json(silent=True) or {}).get("item") or {}
    aluno_id = aluno.get("id")
    out["aluno"] = {"http": al.status_code, "id": aluno_id, "error": (al.get_json(silent=True) or {}).get("error")}
    STATE.write_text(json.dumps({"aluno_id": aluno_id}, ensure_ascii=False), encoding="utf-8")

    amostras = {}
    pei_ids = []
    for cond in ("TEA", "Altas Habilidades", "Deficiência Visual"):
        r = c.post(
            "/api/pei/alunos",
            json={
                "aluno_id": aluno_id,
                "condicao_categoria": cond,
                "periodo_letivo_id": PERIOD,
                "metas_desenvolvimento": f"{MARKER} {cond}",
            },
        )
        body = r.get_json(silent=True) or {}
        amostras[cond] = {
            "criar_http": r.status_code,
            "error": body.get("error"),
            "pei": slim_pei(body),
            "heranca": heranca_81(c, body) if r.status_code == 201 else None,
        }
        if body.get("id"):
            pei_ids.append(body["id"])
    out["amostras"] = amostras
    st = json.loads(STATE.read_text(encoding="utf-8"))
    st["pei_ids"] = pei_ids
    tea_id = (amostras.get("TEA") or {}).get("pei") or {}
    tea_id = tea_id.get("id")
    st["tea_pei"] = tea_id
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")

    if tea_id:
        s1 = c.post(f"/api/pei/alunos/{tea_id}/assinar/coordenador")
        b1 = s1.get_json(silent=True) or {}
        reload1 = c.get(f"/api/pei/alunos/{tea_id}").get_json(silent=True) or {}
        s1b = c.post(f"/api/pei/alunos/{tea_id}/assinar/coordenador")
        b1b = s1b.get_json(silent=True) or {}
        edit_mid = c.put(
            f"/api/pei/alunos/{tea_id}",
            json={"metas_desenvolvimento": f"{MARKER} edit entre assinaturas"},
        )
        be = edit_mid.get_json(silent=True) or {}
        s1c = c.post(f"/api/pei/alunos/{tea_id}/assinar/coordenador")
        s2 = c.post(f"/api/pei/alunos/{tea_id}/assinar/psicopedagogo")
        b2 = s2.get_json(silent=True) or {}
        s2b = c.post(f"/api/pei/alunos/{tea_id}/assinar/psicopedagogo")
        put72 = c.put(f"/api/pei/alunos/{tea_id}", json={"periodo_letivo_id": PERIOD})
        p72 = put72.get_json(silent=True) or {}
        lucas = c.put(f"/api/pei/alunos/{LUCAS_PEI}", json={"periodo_letivo_id": PERIOD})
        lu = lucas.get_json(silent=True) or {}
        reload2 = c.get(f"/api/pei/alunos/{tea_id}").get_json(silent=True) or {}
        out["ciclo_tea"] = {
            "coord": {"http": s1.status_code, "pei": slim_pei(b1)},
            "reload_pos_coord": slim_pei(reload1),
            "coord_de_novo": {"http": s1b.status_code, "error": b1b.get("error")},
            "edit_entre": {
                "http": edit_mid.status_code,
                "invalidou": be.get("assinado_coordenador") is False,
                "status": be.get("status"),
                "label": be.get("status_assinatura_label"),
            },
            "psico": {"http": s2.status_code, "pei": slim_pei(b2)},
            "psico_de_novo": {"http": s2b.status_code, "error": (s2b.get_json(silent=True) or {}).get("error")},
            "72_teste": {
                "http": put72.status_code,
                "valido": p72.get("valido"),
                "status": p72.get("status"),
                "coord": p72.get("assinado_coordenador"),
                "psico": p72.get("assinado_psicopedagogo"),
            },
            "72_lucas": {
                "http": lucas.status_code,
                "valido": lu.get("valido"),
                "status": lu.get("status"),
            },
            "reload_final": slim_pei(reload2),
            "coord_apos_edit": (s1c.get_json(silent=True) or {}).get("status_assinatura_label"),
        }

    print(json.dumps(out, ensure_ascii=False, indent=2))


def phase_cleanup():
    c = client()
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    aluno_id = st.get("aluno_id")
    out = {}
    peis = []
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                DELETE FROM public.school_pei_alunos
                WHERE instituicao_id = %s AND (nome_completo LIKE %s OR aluno_id = %s)
                RETURNING id, nome_completo, status
                """,
                (INST, f"%{MARKER}%", aluno_id),
            )
            peis = [dict(r) for r in cur.fetchall() or []]
            if aluno_id:
                cur.execute(
                    """
                    DELETE FROM public.school_alunos
                    WHERE id = %s AND instituicao_id = %s AND nome LIKE %s
                    RETURNING id, nome
                    """,
                    (aluno_id, INST, f"%{MARKER}%"),
                )
                row = cur.fetchone()
                out["aluno"] = {"id": str(row["id"]), "nome": row["nome"]} if row else None
    out["peis"] = [{"id": str(r["id"]), "nome": r["nome_completo"]} for r in peis]
    leftover = c.get("/api/pei/alunos").get_json(silent=True) or []
    out["list_marker"] = [p.get("nome_completo") for p in leftover if MARKER in (p.get("nome_completo") or "")]
    if STATE.exists():
        STATE.unlink()
    tea_aluno = "00000000-0000-0000-0000-000000000000"
    if aluno_id:
        from b2c_integration_service import dispatch_pei_override_updated

        out["b2c_indiv"] = dispatch_pei_override_updated(
            {
                "nivel": "individual",
                "instituicao_id": INST,
                "aluno_id": aluno_id,
                "aluno_nome": f"{MARKER} Aluno PEI",
                "condicao": "TEA",
                "particularidades": "",
                "versao": 99,
                "is_active": False,
            }
        )
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
