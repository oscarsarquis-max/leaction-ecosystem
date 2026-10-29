#!/usr/bin/env python3
"""115 — varredura PEI assinatura dupla. Prefixo [TESTE VARREDURA 115]. Sem senhas. Sem correção.

Usa condição AEE 'Deficiência Visual' (só rascunho hoje) + aluno isolado.
Não assina o PEI de Lucas Mendes. Restaura AEE Visual ao estado pré-teste no cleanup.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"
MARKER = "[TESTE VARREDURA 115]"
COND = "Deficiência Visual"
TURMA_A = "537b057f-faf3-4d89-90f3-22f9f0d71764"
LUCAS_PEI = "88da0eae-5446-4ec7-9c96-f88f63d37c33"
PERIOD = "68a38cc9-b975-4411-815e-b1fcef171c3d"
STATE = Path("/tmp/scan-115-state.json")


def j(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2, default=j), encoding="utf-8")


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
    return c, user


def slim_pei(p):
    if not p:
        return None
    return {
        "id": p.get("id"),
        "nome": p.get("nome_completo"),
        "status": p.get("status"),
        "versao": p.get("versao"),
        "valido": p.get("valido"),
        "coord": p.get("assinado_coordenador"),
        "psico": p.get("assinado_psicopedagogo"),
        "aee_matriz_id": p.get("aee_matriz_id"),
        "aee_versao": p.get("aee_versao"),
        "condicao": p.get("condicao_categoria"),
        "periodo_letivo_id": p.get("periodo_letivo_id"),
        "periodo_rotulo": p.get("periodo_rotulo"),
        "data_coord": p.get("data_assinatura_coordenador"),
        "data_psico": p.get("data_assinatura_psicopedagogo"),
        "data_assinatura": p.get("data_assinatura"),
        "metas": (p.get("metas_desenvolvimento") or "")[:80],
    }


def slim_aee(m):
    if not m:
        return None
    return {
        "id": m.get("id"),
        "versao": m.get("versao"),
        "status": m.get("status"),
        "coord": m.get("assinado_coordenador"),
        "psico": m.get("assinado_psicopedagogo"),
        "texto": (m.get("texto_escola") or "")[:100],
        "canon_head": (m.get("texto_canonico") or "")[:80],
        "same_as_canon": (m.get("texto_escola") or "").strip()
        == (m.get("texto_canonico") or "").strip(),
    }


def snapshot_aee(cond):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, versao, status, texto_escola, campos_experiencia_metodologica,
                       assinado_coordenador, assinado_psicopedagogo
                FROM public.school_aee_matrizes
                WHERE instituicao_id = %s AND condicao_categoria = %s
                ORDER BY versao
                """,
                (INST, cond),
            )
            return [
                {
                    "id": str(r["id"]),
                    "versao": r["versao"],
                    "status": str(r["status"]),
                    "texto": r["texto_escola"],
                    "campos": r["campos_experiencia_metodologica"],
                    "coord": bool(r["assinado_coordenador"]),
                    "psico": bool(r["assinado_psicopedagogo"]),
                }
                for r in cur.fetchall() or []
            ]


def phase_create():
    c, user = client()
    st = load_state()
    out = {"user": user["email"], "zonas": user["zonas"]}

    tdah = c.get("/api/aee/matriz", query_string={"condicao": "TDAH"}).get_json(silent=True) or {}
    out["tdah"] = {
        "ativa": slim_aee(tdah.get("ativa")),
        "aguardando": slim_aee(tdah.get("aguardando")),
        "editavel": slim_aee(tdah.get("editavel")),
        "canon_head": ((tdah.get("canonico") or {}).get("descricao_base_canonica") or "")[:80],
        "ativa_igual_canon": (
            ((tdah.get("ativa") or {}).get("texto_escola") or "").strip()
            == ((tdah.get("canonico") or {}).get("descricao_base_canonica") or "").strip()
        ),
    }

    tea = c.get("/api/aee/matriz", query_string={"condicao": "TEA"}).get_json(silent=True) or {}
    out["tea"] = {
        "ativa": slim_aee(tea.get("ativa")),
        "aguardando": slim_aee(tea.get("aguardando")),
        "editavel": slim_aee(tea.get("editavel")),
    }

    st["aee_visual_antes"] = snapshot_aee(COND)
    save_state(st)

    vis = c.get("/api/aee/matriz", query_string={"condicao": COND}).get_json(silent=True) or {}
    edit = vis.get("editavel") or vis.get("atual")
    out["visual_antes"] = {
        "ativa": slim_aee(vis.get("ativa")),
        "aguardando": slim_aee(vis.get("aguardando")),
        "editavel": slim_aee(edit),
        "n_timeline": len(vis.get("timeline") or []),
    }

    texto_v1 = f"{MARKER} versão da escola Deficiência Visual — não canônico puro.\n" + (
        (edit or {}).get("texto_escola") or "diretriz escola"
    )
    http_put = c.put(
        f"/api/aee/matriz/{edit['id']}",
        json={"texto_escola": texto_v1, "campos_experiencia_metodologica": (edit or {}).get("campos_experiencia_metodologica") or ""},
    )
    put_body = http_put.get_json(silent=True) or {}
    out["aee_put_rascunho"] = {"http": http_put.status_code, "item": slim_aee(put_body)}

    http_env = c.post(
        f"/api/aee/matriz/{edit['id']}/enviar-aprovacao",
        json={"texto_escola": texto_v1},
    )
    env = http_env.get_json(silent=True) or {}
    out["aee_enviar"] = {
        "http": http_env.status_code,
        "message": env.get("message"),
        "error": env.get("error"),
        "matriz": slim_aee(env.get("matriz")),
    }
    aguardando_id = (env.get("matriz") or {}).get("id")
    st["aee_aguardando_id"] = aguardando_id
    save_state(st)

    vis2 = c.get("/api/aee/matriz", query_string={"condicao": COND}).get_json(silent=True) or {}
    out["visual_apos_enviar"] = {
        "ativa": slim_aee(vis2.get("ativa")),
        "aguardando": slim_aee(vis2.get("aguardando")),
        "editavel": slim_aee(vis2.get("editavel")),
        "statuses": [(t.get("versao"), t.get("status"), t.get("assinado_coordenador"), t.get("assinado_psicopedagogo")) for t in (vis2.get("timeline") or [])],
    }

    # aluno isolado
    http_al = c.post(
        "/api/secretaria/alunos",
        json={
            "nome": f"{MARKER} Aluno PEI",
            "matricula": "115PEI001",
            "turma_id": TURMA_A,
        },
    )
    al = http_al.get_json(silent=True) or {}
    aluno_id = (al.get("item") or {}).get("id")
    out["aluno"] = {"http": http_al.status_code, "item": al.get("item"), "error": al.get("error")}
    st["aluno_id"] = aluno_id
    save_state(st)

    # PEI antes da AEE ativa — deve 409
    http_pre = c.post(
        "/api/pei/alunos",
        json={
            "aluno_id": aluno_id,
            "condicao_categoria": COND,
            "periodo_letivo_id": PERIOD,
            "metas_desenvolvimento": f"{MARKER} metas",
        },
    )
    pre = http_pre.get_json(silent=True) or {}
    out["pei_antes_aee_ativa"] = {"http": http_pre.status_code, "error": pre.get("error")}

    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_aee_sign():
    c, _ = client()
    st = load_state()
    mid = st.get("aee_aguardando_id")
    out = {"matriz_id": mid}

    r1 = c.post("/api/aee/matriz/assinar/coordenador", json={"matriz_id": mid, "condicao_categoria": COND})
    b1 = r1.get_json(silent=True) or {}
    m1 = b1.get("matriz") or {}
    out["coord"] = {
        "http": r1.status_code,
        "message": b1.get("message"),
        "matriz": slim_aee(m1),
        "status_ainda_aguardando": m1.get("status") == "aguardando_assinaturas",
        "completo_cedo": bool(m1.get("assinado_coordenador") and m1.get("assinado_psicopedagogo")),
        "ativo_cedo": m1.get("status") == "ativo",
    }

    r1b = c.get("/api/aee/matriz", query_string={"condicao": COND})
    vis = r1b.get_json(silent=True) or {}
    out["reload_pos_coord"] = {
        "http": r1b.status_code,
        "aguardando": slim_aee(vis.get("aguardando")),
        "ativa": slim_aee(vis.get("ativa")),
    }

    # duplicar coord
    ts1 = (m1.get("data_assinatura_coordenador"))
    r2 = c.post("/api/aee/matriz/assinar/coordenador", json={"matriz_id": mid, "condicao_categoria": COND})
    b2 = r2.get_json(silent=True) or {}
    m2 = b2.get("matriz") or {}
    out["coord_de_novo"] = {
        "http": r2.status_code,
        "error": b2.get("error"),
        "message": b2.get("message"),
        "matriz": slim_aee(m2),
        "bloqueou": r2.status_code >= 400,
        "timestamp_mudou": m2.get("data_assinatura_coordenador") != ts1,
    }

    # editar aguardando
    r_edit = c.put(f"/api/aee/matriz/{mid}", json={"texto_escola": f"{MARKER} edit após 1 assinatura"})
    e_edit = r_edit.get_json(silent=True) or {}
    out["edit_aguardando"] = {"http": r_edit.status_code, "error": e_edit.get("error")}

    r3 = c.post("/api/aee/matriz/assinar/psicopedagogo", json={"matriz_id": mid, "condicao_categoria": COND})
    b3 = r3.get_json(silent=True) or {}
    m3 = b3.get("matriz") or {}
    out["psico"] = {
        "http": r3.status_code,
        "message": b3.get("message"),
        "matriz": slim_aee(m3),
        "status_ativo": m3.get("status") == "ativo",
        "ambas": bool(m3.get("assinado_coordenador") and m3.get("assinado_psicopedagogo")),
    }
    st["aee_ativa_id"] = m3.get("id")
    st["aee_ativa_versao"] = m3.get("versao")
    save_state(st)

    vis3 = c.get("/api/aee/matriz", query_string={"condicao": COND}).get_json(silent=True) or {}
    out["reload_pos_psico"] = {
        "ativa": slim_aee(vis3.get("ativa")),
        "aguardando": slim_aee(vis3.get("aguardando")),
        "statuses": [(t.get("versao"), t.get("status")) for t in (vis3.get("timeline") or [])],
        "ativa_tem_marker": MARKER in ((vis3.get("ativa") or {}).get("texto_escola") or ""),
        "ativa_igual_canon": ((vis3.get("ativa") or {}).get("texto_escola") or "").strip()
        == ((vis3.get("canonico") or {}).get("descricao_base_canonica") or "").strip(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_pei():
    c, _ = client()
    st = load_state()
    aluno_id = st.get("aluno_id")
    out = {}

    http = c.post(
        "/api/pei/alunos",
        json={
            "aluno_id": aluno_id,
            "condicao_categoria": COND,
            "periodo_letivo_id": PERIOD,
            "nome_responsavel": f"{MARKER} responsável",
            "perfil_atual_habilidades": f"{MARKER} perfil",
            "barreiras_identificadas": f"{MARKER} barreiras",
            "metas_desenvolvimento": f"{MARKER} metas v1",
        },
    )
    body = http.get_json(silent=True) or {}
    out["criar"] = {
        "http": http.status_code,
        "error": body.get("error"),
        "pei": slim_pei(body),
        "herda_aee_id": body.get("aee_matriz_id") == st.get("aee_ativa_id"),
        "herda_aee_versao": body.get("aee_versao") == st.get("aee_ativa_versao"),
        "status_rascunho": body.get("status") == "rascunho",
        "valido": body.get("valido"),
    }
    pei_id = body.get("id")
    st["pei_id"] = pei_id
    save_state(st)

    r_get = c.get(f"/api/pei/alunos/{pei_id}")
    out["reload_criar"] = {"http": r_get.status_code, "pei": slim_pei(r_get.get_json(silent=True))}

    r_c = c.post(f"/api/pei/alunos/{pei_id}/assinar/coordenador")
    bc = r_c.get_json(silent=True) or {}
    out["coord"] = {
        "http": r_c.status_code,
        "pei": slim_pei(bc),
        "status": bc.get("status"),
        "valido": bc.get("valido"),
        "completo_cedo": bool(bc.get("valido")),
        "status_intermediario": bc.get("status"),
        "label_ui_equiv": "Aguardando assinaturas" if not bc.get("valido") else "Válido",
    }

    r_c2 = c.post(f"/api/pei/alunos/{pei_id}/assinar/coordenador")
    b2 = r_c2.get_json(silent=True) or {}
    out["coord_de_novo"] = {
        "http": r_c2.status_code,
        "error": b2.get("error"),
        "pei": slim_pei(b2),
        "bloqueou": r_c2.status_code >= 400,
        "timestamp_mudou": b2.get("data_assinatura_coordenador") != bc.get("data_assinatura_coordenador"),
    }

    r_edit = c.put(
        f"/api/pei/alunos/{pei_id}",
        json={"metas_desenvolvimento": f"{MARKER} metas editadas após 1 assinatura"},
    )
    be = r_edit.get_json(silent=True) or {}
    out["edit_apos_1_assinatura"] = {
        "http": r_edit.status_code,
        "error": be.get("error"),
        "pei": slim_pei(be),
        "invalidou_coord": be.get("assinado_coordenador") is False,
        "status": be.get("status"),
    }

    # re-assinar as duas
    r_c3 = c.post(f"/api/pei/alunos/{pei_id}/assinar/coordenador")
    r_p = c.post(f"/api/pei/alunos/{pei_id}/assinar/psicopedagogo")
    bp = r_p.get_json(silent=True) or {}
    out["psico"] = {
        "http": r_p.status_code,
        "pei": slim_pei(bp),
        "valido": bp.get("valido"),
        "status_ativo": bp.get("status") == "ativo",
        "ambas": bool(bp.get("assinado_coordenador") and bp.get("assinado_psicopedagogo")),
        "coord_apos_edit_reassinado": (r_c3.get_json(silent=True) or {}).get("assinado_coordenador"),
    }

    r_get2 = c.get(f"/api/pei/alunos/{pei_id}")
    out["reload_assinado"] = {"http": r_get2.status_code, "pei": slim_pei(r_get2.get_json(silent=True))}

    lista = c.get("/api/pei/alunos").get_json(silent=True) or []
    marker = [p for p in lista if MARKER in (p.get("nome_completo") or "")]
    lucas = next((p for p in lista if p.get("id") == LUCAS_PEI), None)
    out["listagem"] = {
        "http": c.get("/api/pei/alunos").status_code,
        "n_marker": len(marker),
        "lucas": slim_pei(lucas),
        "test": slim_pei(marker[0] if marker else None),
    }

    pdf = c.get(f"/api/pei/alunos/{pei_id}/relatorio-execucao")
    head = (pdf.data or b"")[:8]
    out["pdf"] = {
        "http": pdf.status_code,
        "content_type": pdf.headers.get("Content-Type"),
        "bytes": len(pdf.data or b""),
        "is_pdf": (pdf.data or b"").startswith(b"%PDF"),
        "error": None if pdf.status_code == 200 else (pdf.get_json(silent=True) or {}).get("error"),
        "assinatura_no_binario": b"Coordenador" in (pdf.data or b"") or b"assinat" in (pdf.data or b"").lower(),
        "magic": head.decode("latin-1", errors="replace"),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_72_and_borda3():
    c, _ = client()
    st = load_state()
    pei_id = st.get("pei_id")
    aee_id_orig = st.get("aee_ativa_id")
    out = {}

    before = c.get(f"/api/pei/alunos/{pei_id}").get_json(silent=True) or {}
    r_put = c.put(f"/api/pei/alunos/{pei_id}", json={"periodo_letivo_id": PERIOD})
    after = r_put.get_json(silent=True) or {}
    out["72_teste"] = {
        "http": r_put.status_code,
        "error": after.get("error"),
        "periodo": after.get("periodo_letivo_id"),
        "valido": after.get("valido"),
        "coord": after.get("assinado_coordenador"),
        "psico": after.get("assinado_psicopedagogo"),
        "status": after.get("status"),
        "assinatura_intacta": bool(after.get("valido")) and after.get("status") == "ativo",
    }

    r_cont = c.put(
        f"/api/pei/alunos/{pei_id}",
        json={"metas_desenvolvimento": f"{MARKER} tentou editar conteúdo já assinado"},
    )
    out["put_conteudo_assinado"] = {
        "http": r_cont.status_code,
        "error": (r_cont.get_json(silent=True) or {}).get("error"),
    }

    # 72 no PEI real do Lucas (já assinado) — só período, depois GET confirma
    lucas_antes = c.get(f"/api/pei/alunos/{LUCAS_PEI}").get_json(silent=True) or {}
    r_lu = c.put(f"/api/pei/alunos/{LUCAS_PEI}", json={"periodo_letivo_id": PERIOD})
    lu = r_lu.get_json(silent=True) or {}
    out["72_lucas"] = {
        "http": r_lu.status_code,
        "error": lu.get("error"),
        "periodo": lu.get("periodo_letivo_id"),
        "valido": lu.get("valido"),
        "coord": lu.get("assinado_coordenador"),
        "psico": lu.get("assinado_psicopedagogo"),
        "status": lu.get("status"),
        "antes_valido": lucas_antes.get("valido"),
    }

    # borda 3: nova versão da escola depois do PEI assinado
    vis = c.get("/api/aee/matriz", query_string={"condicao": COND}).get_json(silent=True) or {}
    edit = vis.get("editavel")
    texto2 = f"{MARKER} v2 escola ALTERADA depois do PEI individual assinado"
    c.put(f"/api/aee/matriz/{edit['id']}", json={"texto_escola": texto2})
    env = c.post(
        f"/api/aee/matriz/{edit['id']}/enviar-aprovacao",
        json={"texto_escola": texto2},
    ).get_json(silent=True) or {}
    mid2 = (env.get("matriz") or {}).get("id")
    c.post("/api/aee/matriz/assinar/coordenador", json={"matriz_id": mid2})
    r_ps = c.post("/api/aee/matriz/assinar/psicopedagogo", json={"matriz_id": mid2})
    nova = (r_ps.get_json(silent=True) or {}).get("matriz") or {}
    pei_depois = c.get(f"/api/pei/alunos/{pei_id}").get_json(silent=True) or {}
    vis_f = c.get("/api/aee/matriz", query_string={"condicao": COND}).get_json(silent=True) or {}
    out["borda3"] = {
        "nova_aee": slim_aee(nova),
        "pei": slim_pei(pei_depois),
        "pei_aee_id_antes": aee_id_orig,
        "pei_aee_id_depois": pei_depois.get("aee_matriz_id"),
        "fixo_na_versao_assinada": pei_depois.get("aee_matriz_id") == aee_id_orig,
        "nao_seguiu_nova_ativa": pei_depois.get("aee_matriz_id") != (vis_f.get("ativa") or {}).get("id"),
        "ativa_agora": slim_aee(vis_f.get("ativa")),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def phase_cleanup():
    c, _ = client()
    st = load_state()
    out = {"deleted_pei": [], "aluno": None, "aee_restored": None}

    pei_id = st.get("pei_id")
    aluno_id = st.get("aluno_id")
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                DELETE FROM public.school_pei_alunos
                WHERE instituicao_id = %s
                  AND (nome_completo LIKE %s OR aluno_id = %s)
                RETURNING id, nome_completo, status
                """,
                (INST, f"%{MARKER}%", aluno_id),
            )
            out["deleted_pei"] = [
                {"id": str(r["id"]), "nome": r["nome_completo"], "status": r["status"]}
                for r in cur.fetchall() or []
            ]
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

            # remove versões de teste da Visual; restaura snapshot
            antes = st.get("aee_visual_antes") or []
            keep_ids = {x["id"] for x in antes}
            cur.execute(
                """
                SELECT id FROM public.school_aee_matrizes
                WHERE instituicao_id = %s AND condicao_categoria = %s
                """,
                (INST, COND),
            )
            now_ids = [str(r["id"]) for r in cur.fetchall() or []]
            extra = [i for i in now_ids if i not in keep_ids]
            if extra:
                cur.execute(
                    "DELETE FROM public.school_aee_metodologias_org WHERE aee_matriz_id = ANY(%s::uuid[])",
                    (extra,),
                )
                cur.execute(
                    """
                    DELETE FROM public.school_aee_matrizes
                    WHERE id = ANY(%s::uuid[])
                    RETURNING id, versao, status
                    """,
                    (extra,),
                )
                out["aee_deleted"] = [
                    {"id": str(r["id"]), "versao": r["versao"], "status": str(r["status"])}
                    for r in cur.fetchall() or []
                ]
            for snap in antes:
                cur.execute(
                    """
                    UPDATE public.school_aee_matrizes
                    SET status = %s,
                        texto_escola = %s,
                        campos_experiencia_metodologica = %s,
                        assinado_coordenador = %s,
                        assinado_psicopedagogo = %s,
                        data_assinatura_coordenador = NULL,
                        data_assinatura_psicopedagogo = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        snap["status"],
                        snap["texto"],
                        snap["campos"],
                        snap["coord"],
                        snap["psico"],
                        snap["id"],
                    ),
                )
            out["aee_apos"] = snapshot_aee(COND)

    leftover = c.get("/api/pei/alunos").get_json(silent=True) or []
    out["pei_list_marker"] = [p.get("nome_completo") for p in leftover if MARKER in (p.get("nome_completo") or "")]
    vis = c.get("/api/aee/matriz", query_string={"condicao": COND}).get_json(silent=True) or {}
    out["visual_final"] = {
        "ativa": slim_aee(vis.get("ativa")),
        "aguardando": slim_aee(vis.get("aguardando")),
        "editavel": slim_aee(vis.get("editavel")),
        "n": len(vis.get("timeline") or []),
        "tem_marker": any(MARKER in (t.get("texto_escola") or "") for t in (vis.get("timeline") or [])),
    }
    if STATE.exists():
        STATE.unlink()
    print(json.dumps(out, ensure_ascii=False, indent=2, default=j))


def main():
    phase = (sys.argv[1] if len(sys.argv) > 1 else "create").strip()
    fn = {
        "create": phase_create,
        "aee": phase_aee_sign,
        "pei": phase_pei,
        "72": phase_72_and_borda3,
        "cleanup": phase_cleanup,
    }.get(phase)
    if not fn:
        raise SystemExit(f"phase inválida: {phase}")
    fn()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
