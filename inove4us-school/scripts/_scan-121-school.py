#!/usr/bin/env python3
"""Prompt 121 — School: Central de Ações + retorno obrigatório + índice 55. Não corrige."""
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
MARKER = "[TESTE VARREDURA 121]"
STATE = Path("/tmp/scan-121-state.json")
OUT = Path("/tmp/scan-121-school.json")


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


def slim_item(it: dict) -> dict:
    return {
        "id": it.get("id"),
        "tipo": it.get("tipo"),
        "metodologia_nome": it.get("metodologia_nome"),
        "turma_nome": it.get("turma_nome"),
        "professor_label": it.get("professor_label"),
        "professor_nome": it.get("professor_nome"),
        "aula_contexto": it.get("aula_contexto"),
        "trecho": (it.get("trecho") or it.get("teacher_adaptation_text") or "")[:180],
        "data": it.get("data") or it.get("created_at"),
        "plano_id": it.get("plano_id") or it.get("plano_espelhado_id"),
    }


def is_121(it: dict) -> bool:
    blob = json.dumps(it, ensure_ascii=False, default=str)
    return MARKER in blob


def keys_identificam_individuo(obj: dict) -> list[str]:
    hits = []
    blob = json.dumps(obj, ensure_ascii=False, default=str).lower()
    for needle, label in (
        ("homologador@leaction.com.br", "email_homologador"),
        ("professor_email", "campo_professor_email"),
        ("professor_b2c_id", "campo_professor_b2c_id"),
        ("professor_vinculo_id", "campo_professor_vinculo_id"),
        ("professor_nome", "campo_professor_nome"),
        ("professor_label", "campo_professor_label"),
    ):
        if needle in blob:
            hits.append(label)
    return hits


def main() -> int:
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    c, user = client()
    out: dict = {
        "prompt": 121,
        "gestor": {"email": user.get("email"), "zonas": user.get("zonas"), "cargo": user.get("cargo")},
        "state": {k: st.get(k) for k in ("suffix", "d1", "d2", "d3")},
    }

    r_radar = c.get("/api/pedagogico/curadoria-pendente")
    radar = r_radar.get_json(silent=True) or {}
    itens = radar.get("itens") or []
    itens_121 = [slim_item(it) for it in itens if is_121(it)]
    out["item1"] = {
        "radar_http": r_radar.status_code,
        "radar_total": radar.get("total"),
        "radar_metodologia": radar.get("metodologia"),
        "radar_pei": radar.get("pei"),
        "itens_121": itens_121,
        "n_121": len(itens_121),
        "contexto_ok": all(
            (it.get("metodologia_nome") and it.get("metodologia_nome") != "—")
            and (it.get("professor_label") or it.get("professor_nome"))
            and it.get("trecho")
            for it in itens_121
        )
        if itens_121
        else False,
        "tem_desafio_no_item": any(
            (st.get("d1") and st.get("d1") in json.dumps(it))
            or "desafio" in json.dumps(it, ensure_ascii=False).lower()
            for it in itens_121
        ),
    }

    r_ed = c.get("/api/pedagogico/curadoria/pendentes")
    ed = r_ed.get_json(silent=True) or {}
    ed_items = ed.get("items") or []
    ed_121 = [slim_item(it) for it in ed_items if is_121(it)]
    ids = [it["id"] for it in ed_121 if it.get("id")]
    textos = [it.get("trecho") or "" for it in ed_121]
    out["item1"]["editor_http"] = r_ed.status_code
    out["item1"]["editor_n_121"] = len(ed_121)
    out["item1"]["editor_ids"] = ids
    out["item1"]["textos"] = textos

    # 2.3: A e B em desafios distintos devem aparecer separados
    has_a = any("proposta A" in (t or "") for t in textos)
    has_b = any("proposta B" in (t or "") for t in textos)
    has_c = any("proposta C" in (t or "") for t in textos)
    has_d = any("proposta D" in (t or "") for t in textos)
    out["item2"] = {
        "duas_pendentes_desafios_distintos": {
            "n_ids": len(ids),
            "ids_unicos": len(set(ids)),
            "tem_a": has_a,
            "tem_b": has_b,
            "ok": has_a and has_b and len(set(ids)) >= 2,
        },
        "mesma_cadeia_c_e_d": {
            "tem_c": has_c,
            "tem_d": has_d,
            "ambas": has_c and has_d,
            "nota": "se só D restar, o webhook fez UPDATE na pendente do mesmo plano",
        },
    }

    alvo = ids[0] if ids else None
    vazio = {}
    if alvo:
        r_inc = c.post(f"/api/pedagogico/curadoria/{alvo}/incorporar", json={})
        r_adp = c.post(f"/api/pedagogico/curadoria/{alvo}/adaptar", json={"retorno_docente": "   "})
        r_rej_vazio = c.post(f"/api/pedagogico/curadoria/{alvo}/rejeitar", json={})
        b_inc = r_inc.get_json(silent=True) or {}
        b_adp = r_adp.get_json(silent=True) or {}
        b_rej = r_rej_vazio.get_json(silent=True) or {}
        out["item2"]["retorno_obrigatorio"] = {
            "alvo": alvo,
            "incorporar_vazio": {
                "http": r_inc.status_code,
                "code": b_inc.get("code"),
                "error": b_inc.get("error"),
            },
            "adaptar_branco": {
                "http": r_adp.status_code,
                "code": b_adp.get("code"),
                "error": b_adp.get("error"),
            },
            "rejeitar_vazio": {
                "http": r_rej_vazio.status_code,
                "code": b_rej.get("code"),
                "error": b_rej.get("error"),
            },
            "ok": r_inc.status_code == 400
            and b_inc.get("code") == "RETORNO_DOCENTE_OBRIGATORIO"
            and r_adp.status_code == 400
            and r_rej_vazio.status_code == 400,
        }

        retorno = f"{MARKER} retorno ao docente — não incorporar agora ({st.get('suffix')})"
        r_ok = c.post(
            f"/api/pedagogico/curadoria/{alvo}/rejeitar",
            json={"retorno_docente": retorno},
        )
        bok = r_ok.get_json(silent=True) or {}
        aviso = bok.get("aviso") if isinstance(bok.get("aviso"), dict) else {}
        out["item1"]["rejeitar_com_retorno"] = {
            "http": r_ok.status_code,
            "error": bok.get("error"),
            "code": bok.get("code"),
            "aviso_tipo": aviso.get("tipo") or (bok.get("item") or {}).get("resultado_analise"),
            "aviso_id": aviso.get("id") or (bok.get("aviso") or {}).get("id") if isinstance(bok.get("aviso"), dict) else None,
            "b2c_dispatch": bok.get("b2c_dispatch") or bok.get("aviso_push"),
            "item_status": (bok.get("item") or {}).get("status_analise"),
            "resultado": (bok.get("item") or {}).get("resultado_analise"),
            "ok": r_ok.status_code in (200, 201),
        }
        # segundo item: adaptar com retorno (não incorpora catálogo? adaptar SIM incorpora)
        # só rejeitar o segundo também para não mutar catálogo
        ids2 = [i for i in ids if i != alvo]
        if ids2:
            r2 = c.post(
                f"/api/pedagogico/curadoria/{ids2[0]}/rejeitar",
                json={"retorno_docente": f"{MARKER} segundo retorno ({st.get('suffix')})"},
            )
            b2 = r2.get_json(silent=True) or {}
            out["item1"]["rejeitar_segundo"] = {
                "http": r2.status_code,
                "error": b2.get("error"),
                "ok": r2.status_code in (200, 201),
            }
        # reabrir radar
        r_radar2 = c.get("/api/pedagogico/curadoria-pendente")
        radar2 = r_radar2.get_json(silent=True) or {}
        itens2 = [slim_item(it) for it in (radar2.get("itens") or []) if is_121(it)]
        out["item1"]["reabrir_radar"] = {
            "http": r_radar2.status_code,
            "n_121_restantes": len(itens2),
            "itens": itens2,
        }
    else:
        out["item2"]["retorno_obrigatorio"] = {"ok": False, "error": "nenhuma pendente 121"}
        out["item1"]["rejeitar_com_retorno"] = {"ok": False, "error": "nenhuma pendente 121"}

    # Índice 55
    today = date.today()
    ini = today - timedelta(days=(today.weekday()))
    fim = ini + timedelta(days=6)
    # aulas de teste estão em datas futuras (semana_referencia = data da aula)
    fut_ini = date.today() + timedelta(days=70)
    fut_fim = date.today() + timedelta(days=80)
    r_sum = c.get(
        f"/api/pedagogico/calendario-pedagogico/resumo?data_inicio={fut_ini.isoformat()}&data_fim={fut_fim.isoformat()}"
    )
    body_sum = r_sum.get_json(silent=True) or {}
    contrib = body_sum.get("contribuicao") if isinstance(body_sum.get("contribuicao"), dict) else None
    hits = keys_identificam_individuo(contrib or {})
    # o resumo completo pode ter professores_ativos (contagem) — ok; não pode listar emails no bloco
    out["item3"] = {
        "resumo_http": r_sum.status_code,
        "contribuicao": contrib,
        "chaves_contribuicao": sorted(contrib.keys()) if contrib else None,
        "identifica_individuo_no_bloco": hits,
        "ok_agregado": contrib is not None and not hits,
        "copy_esperado": "agregado da escola / sem identificação de professores",
        "semana_usada": {"inicio": fut_ini.isoformat(), "fim": fut_fim.isoformat()},
        "semana_corrente_nao_usada": {"inicio": ini.isoformat(), "fim": fim.isoformat()},
    }

    # DB: avisos gerados
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text, tipo, professor_b2c_id, left(texto, 180) AS texto, ativo
                FROM public.school_avisos_mesa
                WHERE instituicao_id = %s
                  AND (
                    texto ILIKE %s
                    OR tipo = 'resposta_proposta_metodologica'
                  )
                ORDER BY id DESC
                LIMIT 20
                """,
                (INST, "%" + MARKER + "%"),
            )
            avisos = [dict(r) for r in cur.fetchall() or []]
            cur.execute(
                """
                SELECT c.id::text, c.status_analise, c.resultado_analise,
                       c.metodologia_nome, left(c.sugestao_professor_json::text, 200) AS trecho
                FROM public.school_curadoria_metodologias c
                WHERE c.instituicao_id = %s
                  AND c.sugestao_professor_json::text ILIKE %s
                ORDER BY c.created_at DESC
                """,
                (INST, "%" + MARKER + "%"),
            )
            curads = [dict(r) for r in cur.fetchall() or []]
    out["db"] = {
        "avisos_121": avisos,
        "curadoria_121": curads,
        "aviso_tipo_resposta": all(
            a.get("tipo") == "resposta_proposta_metodologica" for a in avisos if MARKER in (a.get("texto") or "")
        )
        if avisos
        else False,
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
