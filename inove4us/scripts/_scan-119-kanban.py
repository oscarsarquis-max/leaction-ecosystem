#!/usr/bin/env python3
"""Prompt 119 — varredura Diário de Bordo (Kanban). Só reporta; não corrige."""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

import requests

BASE = "https://inove4us.com.br"
MARKER = "[TESTE VARREDURA 119]"
HOMOLOG = "homologador@leaction.com.br"
COLAB = "sandbox999@leaction.com.br"
MAPA = "agil_mapeamento_mental"


def login(email: str) -> tuple[requests.Session, dict]:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=30)
    data = r.json() if r.content else {}
    if data.get("status") not in ("granted", "ok") and not data.get("id_clie"):
        raise RuntimeError(f"login {email}: {data}")
    return s, data


def j(r: requests.Response) -> dict:
    if not r.content:
        return {}
    try:
        body = r.json()
    except Exception:
        return {"raw": r.text[:600]}
    return body if isinstance(body, dict) else {"value": body}


def tarefas(desafio: dict) -> list[dict]:
    pd = desafio.get("plan_data") if isinstance(desafio.get("plan_data"), dict) else {}
    plano = pd.get("plano") if isinstance(pd.get("plano"), dict) else {}
    raw = plano.get("tarefas_kanban") or pd.get("tarefas_kanban") or []
    return [t for t in raw if isinstance(t, dict)] if isinstance(raw, list) else []


def slim_t(t: dict) -> dict:
    return {
        "id": t.get("id"),
        "titulo": t.get("titulo"),
        "coluna": t.get("coluna"),
        "origem_card": t.get("origem_card"),
        "editado": t.get("editado"),
        "parent_card_id": t.get("parent_card_id"),
        "aula_id": t.get("aula_id"),
        "fonte_pei": t.get("fonte_pei") or (t.get("meta_json") or {}).get("fonte")
        if isinstance(t.get("meta_json"), dict)
        else t.get("fonte_pei"),
    }


def get_desafio(s: requests.Session, did: str) -> dict:
    r = s.get(f"{BASE}/api/desafios/{did}", timeout=30)
    body = j(r)
    return {
        "http": r.status_code,
        "desafio": body.get("desafio") or {},
        "error": body.get("error"),
    }


def get_mesa(s: requests.Session, did: str) -> dict:
    r = s.get(f"{BASE}/api/desafios/{did}/mesa", timeout=30)
    body = j(r)
    cards = body.get("cards") or []
    return {
        "http": r.status_code,
        "error": body.get("error"),
        "n_cards": len(cards) if isinstance(cards, list) else None,
        "cards": [slim_t(c) for c in cards] if isinstance(cards, list) else [],
        "encerrado": (body.get("desafio") or {}).get("encerrado")
        if isinstance(body.get("desafio"), dict)
        else body.get("encerrado"),
        "encerramento": body.get("encerramento")
        or (body.get("desafio") or {}).get("encerramento"),
        "n_aulas": len(body.get("eventos") or body.get("aulas") or []),
        "id_evento_ancora": body.get("id_evento_ancora"),
    }


def creditos(s: requests.Session) -> int | None:
    me = s.get(f"{BASE}/api/auth/me", timeout=20).json()
    u = me.get("user") or me
    try:
        return int(u.get("creditos_ia"))
    except (TypeError, ValueError):
        return None


def main() -> int:
    out: dict = {
        "prompt": 119,
        "marker": MARKER,
        "ids": {},
        "item1": {},
        "item2": {},
        "item3": {},
        "cleanup": {},
        "ui": "separado (_scan-119-ui.py)",
    }
    health = requests.get(f"{BASE}/api/health", timeout=20).json()
    out["health"] = {"ok": health.get("ok"), "git_sha": health.get("git_sha")}

    s, auth = login(HOMOLOG)
    out["homolog"] = {"id_clie": auth.get("id_clie") or (auth.get("user") or {}).get("id_clie")}
    c0 = creditos(s)
    out["creditos_antes"] = c0

    suffix = uuid.uuid4().hex[:8]
    titulo = f"{MARKER} kanban {suffix}"
    cid_cat = f"c119-cat-{suffix}"
    cid_custom = f"c119-cus-{suffix}"
    dia1 = (date.today() + timedelta(days=42)).isoformat()
    dia2 = (date.today() + timedelta(days=43)).isoformat()
    turma = f"119-{suffix}"

    plan = {
        "problema": f"{MARKER} persistencia kanban",
        "hipotese": "autosave 78 + retrieval 102",
        "causas": [{"titulo": "c1", "descricao": "scan 119"}],
        "plano": {
            "missao": f"{MARKER} mesa",
            "id_metodologia": MAPA,
            "tarefas_kanban": [],
        },
    }

    r = s.post(
        f"{BASE}/api/desafios",
        json={"titulo": titulo, "tema": titulo, "plan_data": plan},
        timeout=30,
    )
    body = j(r)
    did = body.get("desafio_id") or (body.get("desafio") or {}).get("id")
    out["ids"]["desafio_main"] = did
    out["item1"]["criar_desafio"] = {"http": r.status_code, "id": did, "error": body.get("error")}
    if not did:
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 1

    # --- 1.1 criar cards (sem id_evento) ---
    cards_v1 = [
        {
            "id": cid_cat,
            "titulo": f"{MARKER} card catalogo",
            "coluna": "para_fazer",
            "origem_card": "catalogo",
            "editado": False,
            "ordem": 0,
            "descricao": "Passo do roteiro-base do mapa mental.",
        }
    ]
    put = s.put(
        f"{BASE}/api/desafios/{did}",
        json={"kanban_state": {"tarefas": cards_v1}},
        timeout=30,
    )
    g1 = get_desafio(s, did)
    ts1 = tarefas(g1["desafio"])
    out["item1"]["1_criar_cards"] = {
        "put_http": put.status_code,
        "reabrir_http": g1["http"],
        "n": len(ts1),
        "cards": [slim_t(t) for t in ts1],
        "ok": put.ok and any(t.get("id") == cid_cat for t in ts1),
        "sem_id_evento": True,
        "encerrado": (g1["desafio"] or {}).get("encerrado"),
    }

    # --- 1.2 mover colunas ---
    cards_v2 = [{**cards_v1[0], "coluna": "fazendo"}]
    put2 = s.put(
        f"{BASE}/api/desafios/{did}",
        json={"kanban_state": {"tarefas": cards_v2}},
        timeout=30,
    )
    g2 = get_desafio(s, did)
    ts2 = tarefas(g2["desafio"])
    col = next((t.get("coluna") for t in ts2 if t.get("id") == cid_cat), None)
    out["item1"]["2_mover_colunas"] = {
        "put_http": put2.status_code,
        "reabrir_coluna": col,
        "origem_card": next((t.get("origem_card") for t in ts2 if t.get("id") == cid_cat), None),
        "ok": col == "fazendo",
        "rastro_indice_55": "coluna persistida; origem_card=catalogo (carimbo do índice 55)",
        "cards": [slim_t(t) for t in ts2],
    }

    # --- 1.3a editar sem id_evento (78) ---
    cards_v3 = [
        {
            **cards_v2[0],
            "titulo": f"{MARKER} card catalogo EDITADO",
            "descricao": "Conteudo editado sem evento.",
            "editado": True,
        }
    ]
    put3 = s.put(
        f"{BASE}/api/desafios/{did}",
        json={"kanban_state": {"tarefas": cards_v3}},
        timeout=30,
    )
    g3 = get_desafio(s, did)
    ts3 = tarefas(g3["desafio"])
    tcat = next((t for t in ts3 if t.get("id") == cid_cat), {})
    out["item1"]["3a_editar_sem_id_evento"] = {
        "put_http": put3.status_code,
        "titulo": tcat.get("titulo"),
        "editado": tcat.get("editado"),
        "ok": "EDITADO" in str(tcat.get("titulo") or "") and tcat.get("editado") is True,
    }
    out["item3"]["78_autosave_sem_id_evento"] = out["item1"]["3a_editar_sem_id_evento"]

    # --- 1.4 / 3.1 / 3.4 🧩 PEI canônico ---
    c_before_pei = creditos(s)
    pei = s.post(
        f"{BASE}/api/kanban/adaptar-pei",
        json={
            "card_id": cid_cat,
            "titulo_card": tcat.get("titulo") or "card catalogo",
            "descricao_card": tcat.get("descricao") or "Passo do roteiro",
            "perfil_selecionado": "TEA",
            "metodologia_id": MAPA,
            "desafio_id": did,
            "coluna": "fazendo",
        },
        timeout=90,
    )
    pei_body = j(pei)
    g4 = get_desafio(s, did)
    mesa4 = get_mesa(s, did)
    ts4 = tarefas(g4["desafio"])
    mesa_cards = mesa4.get("cards") or []
    tem_parent_plan = any(str(t.get("parent_card_id") or "") == cid_cat for t in ts4)
    tem_parent_mesa = any(str(c.get("parent_card_id") or "") == cid_cat for c in mesa_cards)
    pei_ok = (
        pei.ok
        and pei_body.get("fonte") == "card_modificado_79_81"
        and pei_body.get("ia_called") is False
        and tem_parent_mesa
    )
    out["item1"]["4_pei_puzzle"] = {
        "http": pei.status_code,
        "fonte": pei_body.get("fonte"),
        "ia_called": pei_body.get("ia_called"),
        "error": pei_body.get("error"),
        "creditos_antes": c_before_pei,
        "creditos_depois": creditos(s),
        "sub_titulo": (pei_body.get("kanban_task") or pei_body.get("subcard") or {}).get("titulo"),
        "tem_parent_plan_data": tem_parent_plan,
        "tem_parent_mesa_reabrir": tem_parent_mesa,
        "mesa_http": mesa4["http"],
        "mesa_cards": mesa_cards,
        "ok": pei_ok,
    }
    out["item3"]["76_pei_reabrir"] = {
        "ok": tem_parent_mesa,
        "fonte": pei_body.get("fonte"),
        "detalhe": "subcard na mesa após GET (fechar/reabrir API)",
    }
    out["item3"]["102_retrieval_canonico"] = {
        "ok": pei_body.get("fonte") == "card_modificado_79_81"
        and pei_body.get("ia_called") is False,
        "fonte": pei_body.get("fonte"),
        "ia_called": pei_body.get("ia_called"),
        "nao_gastou_credito": creditos(s) == c_before_pei,
    }

    # --- 1.5 card custom ---
    cards_v5 = cards_v3 + [
        {
            "id": cid_custom,
            "titulo": f"{MARKER} card custom mesa",
            "coluna": "para_fazer",
            "origem_card": "custom",
            "editado": False,
            "ordem": 1,
            "descricao": "Passo criado na Mesa, fora do catalogo.",
        }
    ]
    put5 = s.put(
        f"{BASE}/api/desafios/{did}",
        json={"kanban_state": {"tarefas": cards_v5}},
        timeout=30,
    )
    g5 = get_desafio(s, did)
    ts5 = tarefas(g5["desafio"])
    custom = next((t for t in ts5 if t.get("id") == cid_custom), None)
    mesa5 = get_mesa(s, did)
    custom_mesa = next((c for c in (mesa5.get("cards") or []) if c.get("id") == cid_custom), None)
    out["item1"]["5_card_custom"] = {
        "put_http": put5.status_code,
        "reabrir_plan": slim_t(custom) if custom else None,
        "reabrir_mesa": custom_mesa,
        "ok": bool(custom) and custom.get("origem_card") == "custom",
    }

    # --- registrar 2 aulas (cadeia continuidade / id_evento_pai) ---
    plan_reg = {
        **plan,
        "plano": {
            **plan["plano"],
            "tarefas_kanban": cards_v5,
        },
    }
    reg = s.post(
        f"{BASE}/api/agenda-eventos/registrar-aulas",
        json={
            "titulo": titulo,
            "tema": titulo,
            "desafio_id": did,
            "plano_session": str(uuid.uuid4()),
            "plan_data": plan_reg,
            "kanban_state": {"tarefas": cards_v5},
            "causas": plan["causas"],
            "aulas": [
                {
                    "data": dia1,
                    "turma": turma,
                    "turno": "manha",
                    "modo_execucao": "reinicio",
                    "card_ids": [cid_cat, cid_custom],
                    "escopos": {
                        cid_cat: "Turma faz o mapa (scan 119 aula 1)",
                        cid_custom: "Turma faz o passo custom (aula 1)",
                    },
                },
                {
                    "data": dia2,
                    "turma": turma,
                    "turno": "manha",
                    "modo_execucao": "continuidade",
                    "card_ids": [cid_cat, cid_custom],
                    "escopos": {
                        cid_cat: "Turma continua o mapa (scan 119 aula 2)",
                        cid_custom: "Turma continua o custom (aula 2)",
                    },
                },
            ],
        },
        timeout=40,
    )
    rb = j(reg)
    eventos = rb.get("eventos") or []
    ev_ids = [e.get("id_evento") for e in eventos if e.get("id_evento")]
    out["ids"]["eventos_main"] = ev_ids
    out["item1"]["registrar_aulas"] = {
        "http": reg.status_code,
        "error": rb.get("error"),
        "n": len(eventos),
        "ids": ev_ids,
        "pais": [e.get("id_evento_pai") for e in eventos],
        "status": [e.get("status") for e in eventos],
    }

    # --- 1.3b editar COM id_evento ---
    edit_com_ev = None
    if ev_ids:
        ev0 = ev_ids[0]
        put_ev = s.put(
            f"{BASE}/api/agenda-eventos/{ev0}/estado",
            json={
                "kanban_state": {
                    "tarefas": [
                        {
                            **cards_v5[0],
                            "titulo": f"{MARKER} card catalogo COM EVENTO",
                            "coluna": "pronto",
                            "aula_id": ev0,
                            "editado": True,
                        },
                        {**cards_v5[1], "aula_id": ev0},
                    ]
                }
            },
            timeout=30,
        )
        kb = s.get(f"{BASE}/api/agenda-eventos/{ev0}/kanban", timeout=30)
        kb_body = j(kb)
        kb_cards = kb_body.get("cards") or kb_body.get("tarefas") or []
        g_ev = s.get(f"{BASE}/api/agenda-eventos/{ev0}", timeout=30)
        ev_body = j(g_ev).get("evento") or {}
        ks = ev_body.get("kanban_state") or {}
        ks_t = ks.get("tarefas") if isinstance(ks, dict) else ks
        if not isinstance(ks_t, list):
            ks_t = []
        edit_com_ev = {
            "put_http": put_ev.status_code,
            "reabrir_evento_http": g_ev.status_code,
            "kanban_http": kb.status_code,
            "titulo_no_evento": next(
                (t.get("titulo") for t in ks_t if isinstance(t, dict) and t.get("id") == cid_cat),
                None,
            ),
            "coluna_no_evento": next(
                (t.get("coluna") for t in ks_t if isinstance(t, dict) and t.get("id") == cid_cat),
                None,
            ),
            "n_kanban": len(kb_cards) if isinstance(kb_cards, list) else None,
        }
        edit_com_ev["ok"] = (
            put_ev.ok
            and "COM EVENTO" in str(edit_com_ev["titulo_no_evento"] or "")
            and edit_com_ev["coluna_no_evento"] == "pronto"
        )
    out["item1"]["3b_editar_com_id_evento"] = edit_com_ev

    # --- 1.6 / 2.2 board editável até TODAS as aulas ---
    g_mid = get_desafio(s, did)
    enc_mid = (g_mid["desafio"] or {}).get("encerramento") or {}
    put_ainda = s.put(
        f"{BASE}/api/desafios/{did}",
        json={"kanban_state": {"tarefas": cards_v5}},
        timeout=30,
    )
    conc1 = None
    if ev_ids:
        conc1 = s.post(
            f"{BASE}/api/agenda-eventos/{ev_ids[0]}/concluir-aula",
            json={
                "relato_sala": f"{MARKER} encerrou so a primeira aula",
                "participantes": turma,
            },
            timeout=30,
        )
    g_one = get_desafio(s, did)
    enc_one = (g_one["desafio"] or {}).get("encerramento") or {}
    put_one = s.put(
        f"{BASE}/api/desafios/{did}",
        json={
            "kanban_state": {
                "tarefas": [{**cards_v5[0], "titulo": f"{MARKER} ainda editavel apos 1/2"}]
                + cards_v5[1:]
            }
        },
        timeout=30,
    )
    g_one_re = get_desafio(s, did)
    ts_one = tarefas(g_one_re["desafio"])
    out["item2"]["2_multi_aula_cadeia"] = {
        "n_eventos": len(ev_ids),
        "id_evento_pai": [e.get("id_evento_pai") for e in eventos],
        "antes_qualquer_conclusao": {
            "encerrado": (g_mid["desafio"] or {}).get("encerrado"),
            "encerramento": enc_mid,
            "put_http": put_ainda.status_code,
        },
        "so_primeira_concluida": {
            "concluir_http": conc1.status_code if conc1 is not None else None,
            "concluir_error": j(conc1).get("error") if conc1 is not None and not conc1.ok else None,
            "encerrado": (g_one["desafio"] or {}).get("encerrado"),
            "encerramento": enc_one,
            "put_ainda_ok": put_one.ok,
            "reabrir_titulo": next((t.get("titulo") for t in ts_one if "ainda editavel" in str(t.get("titulo") or "")), None),
        },
        "ok_permanece_editavel": (g_one["desafio"] or {}).get("encerrado") is False and put_one.ok,
    }

    conc2 = None
    if len(ev_ids) > 1:
        conc2 = s.post(
            f"{BASE}/api/agenda-eventos/{ev_ids[1]}/concluir-aula",
            json={
                "relato_sala": f"{MARKER} encerrou a segunda aula da cadeia",
                "participantes": turma,
            },
            timeout=30,
        )
    g_all = get_desafio(s, did)
    enc_all = (g_all["desafio"] or {}).get("encerramento") or {}
    put_after = s.put(
        f"{BASE}/api/desafios/{did}",
        json={
            "kanban_state": {
                "tarefas": [{**cards_v5[0], "titulo": f"{MARKER} editou DEPOIS de encerrado"}]
                + cards_v5[1:]
            }
        },
        timeout=30,
    )
    g_after = get_desafio(s, did)
    ts_after = tarefas(g_after["desafio"])
    titulo_after = next((t.get("titulo") for t in ts_after if t.get("id") == cid_cat), None)
    blocked = put_after.status_code in (400, 403, 409) or not put_after.ok
    out["item1"]["6_encerramento"] = {
        "concluir_2_http": conc2.status_code if conc2 is not None else None,
        "encerrado": (g_all["desafio"] or {}).get("encerrado"),
        "encerramento": enc_all,
        "ok_marca_encerrado_so_no_fim": (g_all["desafio"] or {}).get("encerrado") is True,
        "ui_boardEditavel_nota": (
            "StepEduScrum: boardEditavel permanece true se aulaConcluida; "
            "taskEditavel retorna true quando TODAS as aulas ligadas estão concluido. "
            "Trava pós-encerramento NÃO está aplicada (comentário 78 / docstring PUT)."
        ),
    }
    out["item2"]["1_editar_depois_encerrado"] = {
        "put_http": put_after.status_code,
        "put_error": j(put_after).get("error") if not put_after.ok else None,
        "persistiu_titulo": titulo_after,
        "bloqueou": blocked,
        "ok_esperado_bloquear": blocked,
        "falha": (not blocked)
        and "DEPOIS de encerrado" in str(titulo_after or ""),
        "nota": "PUT /api/desafios aceita escrita mesmo encerrado (ciclo futuro).",
    }

    # --- 2.3 dois professores ---
    colab_out = {"skipped": False}
    try:
        sb, auth_b = login(COLAB)
    except Exception as exc:
        sb = None
        colab_out = {"skipped": True, "reason": f"login {COLAB} falhou: {exc}"}
    if sb is not None:
        titulo_b = f"{MARKER} colab {suffix}"
        cid_b = f"c119-colab-{suffix}"
        plan_b = {
            "problema": f"{MARKER} dois professores",
            "hipotese": "trava por desafio",
            "causas": [{"titulo": "c1", "descricao": "colab"}],
            "plano": {
                "missao": titulo_b,
                "id_metodologia": MAPA,
                "tarefas_kanban": [
                    {"id": cid_b, "titulo": f"{MARKER} card colab", "coluna": "para_fazer"}
                ],
            },
        }
        dia_a = (date.today() + timedelta(days=44)).isoformat()
        dia_b = (date.today() + timedelta(days=45)).isoformat()
        ra = s.post(
            f"{BASE}/api/agenda-eventos/registrar-aulas",
            json={
                "titulo": titulo_b,
                "tema": titulo_b,
                "plano_session": str(uuid.uuid4()),
                "plan_data": plan_b,
                "kanban_state": {"tarefas": plan_b["plano"]["tarefas_kanban"]},
                "causas": plan_b["causas"],
                "aulas": [
                    {
                        "data": dia_a,
                        "turma": f"{turma}-A",
                        "turno": "tarde",
                        "modo_execucao": "reinicio",
                        "card_ids": [cid_b],
                        "escopos": {cid_b: "Professor A realiza o card (119)"},
                    }
                ],
            },
            timeout=40,
        )
        ba = j(ra)
        did_b = ba.get("desafio_id")
        ev_a = (ba.get("eventos") or [{}])[0]
        out["ids"]["desafio_colab"] = did_b
        out["ids"]["evento_colab_a"] = ev_a.get("id_evento")
        conv = (
            s.post(
                f"{BASE}/api/desafios/{did_b}/convidar",
                json={"email": COLAB, "papel_ou_parte": "Colab 119", "card_id": cid_b},
                timeout=30,
            )
            if did_b
            else None
        )
        cj = j(conv) if conv is not None else {}
        token = (cj.get("colaborador") or {}).get("token_convite")
        acc = sb.post(f"{BASE}/api/convites/{token}/aceitar", json={}, timeout=30) if token else None
        rb2 = (
            sb.post(
                f"{BASE}/api/desafios/{did_b}/replicar",
                json={
                    "turma": f"{turma}-B",
                    "turno": "tarde",
                    "aulas": [
                        {
                            "titulo": "Parte B 119",
                            "data": dia_b,
                            "turno": "tarde",
                            "modo_execucao": "reinicio",
                            "card_ids": [cid_b],
                            "escopos": {cid_b: "Professor B realiza o card (119)"},
                        }
                    ],
                },
                timeout=40,
            )
            if did_b
            else None
        )
        bj = j(rb2) if rb2 is not None else {}
        ev_b = (bj.get("eventos") or [{}])[0]
        out["ids"]["evento_colab_b"] = ev_b.get("id_evento")
        conc_a = (
            s.post(
                f"{BASE}/api/agenda-eventos/{ev_a['id_evento']}/concluir-aula",
                json={"relato_sala": f"{MARKER} A encerrou", "participantes": f"{turma}-A"},
                timeout=30,
            )
            if ev_a.get("id_evento")
            else None
        )
        ga = s.get(f"{BASE}/api/desafios/{did_b}", timeout=30) if did_b else None
        gb = sb.get(f"{BASE}/api/desafios/{did_b}", timeout=30) if did_b else None
        da = (j(ga).get("desafio") if ga else {}) or {}
        db = (j(gb).get("desafio") if gb else {}) or {}
        put_a = (
            s.put(
                f"{BASE}/api/desafios/{did_b}",
                json={"kanban_state": {"tarefas": [{"id": cid_b, "titulo": f"{MARKER} edit A", "coluna": "fazendo"}]}},
                timeout=30,
            )
            if did_b
            else None
        )
        put_b = (
            sb.put(
                f"{BASE}/api/desafios/{did_b}",
                json={"kanban_state": {"tarefas": [{"id": cid_b, "titulo": f"{MARKER} edit B", "coluna": "para_fazer"}]}},
                timeout=30,
            )
            if did_b
            else None
        )
        colab_out = {
            "skipped": False,
            "colab_email": COLAB,
            "colab_id_clie": auth_b.get("id_clie") or (auth_b.get("user") or {}).get("id_clie"),
            "registrar_a": {"http": ra.status_code, "desafio_id": did_b, "error": ba.get("error")},
            "convidar": {"http": conv.status_code if conv else None, "token": bool(token), "error": cj.get("error")},
            "aceitar": {"http": acc.status_code if acc else None},
            "replicar_b": {
                "http": rb2.status_code if rb2 else None,
                "error": bj.get("error"),
                "ev_b": ev_b.get("id_evento"),
            },
            "concluir_so_a": {"http": conc_a.status_code if conc_a else None},
            "encerrado_a": da.get("encerrado"),
            "encerrado_b": db.get("encerrado"),
            "encerramento_a": da.get("encerramento"),
            "put_a": put_a.status_code if put_a else None,
            "put_b": put_b.status_code if put_b else None,
            "ok_trava_por_desafio": da.get("encerrado") is False
            and db.get("encerrado") is False
            and bool(put_a and put_a.ok)
            and bool(put_b and put_b.ok),
        }
    out["item2"]["3_dois_professores"] = colab_out

    # --- 3.3 / 80 rascunho sem tema ---
    r80 = s.post(
        f"{BASE}/api/daily/planejar",
        json={"data_planejada": (date.today() + timedelta(days=50)).isoformat(), "tema_aula": ""},
        timeout=20,
    )
    r80b = s.post(
        f"{BASE}/api/daily/planejar",
        json={"data_planejada": (date.today() + timedelta(days=50)).isoformat()},
        timeout=20,
    )
    agenda = s.get(f"{BASE}/api/agenda-eventos", timeout=30)
    ag_body = j(agenda)
    eventos_ag = ag_body.get("eventos") or ag_body.get("items") or []
    if not isinstance(eventos_ag, list):
        eventos_ag = []
    ghosts = [
        e
        for e in eventos_ag
        if MARKER in str(e.get("titulo") or "") and str(e.get("tipo") or "") not in ("aula_eduscrum",)
    ]
    daily_ghosts = [
        e
        for e in eventos_ag
        if MARKER in str(e.get("titulo") or "") and "daily" in str(e.get("origem") or e.get("tipo") or "").lower()
    ]
    out["item3"]["80_rascunho_sem_tema"] = {
        "aplicavel": (
            "Diário de Bordo (desafio) não cria aula via daily/planejar. "
            "Caminho equivalente: POST /api/daily/planejar sem tema_aula."
        ),
        "planejar_tema_vazio": {"http": r80.status_code, "error": j(r80).get("error")},
        "planejar_sem_campo": {"http": r80b.status_code, "error": j(r80b).get("error")},
        "bloqueou": r80.status_code == 400 and r80b.status_code == 400,
        "ghosts_marker_nao_eduscrum": len(ghosts),
        "ghosts_daily": len(daily_ghosts),
        "ok": r80.status_code == 400 and r80b.status_code == 400,
    }

    # --- cleanup via DELETE eventos + list leftover desafios ---
    deleted = []
    for eid in list(out["ids"].get("eventos_main") or []) + [
        out["ids"].get("evento_colab_a"),
        out["ids"].get("evento_colab_b"),
    ]:
        if not eid:
            continue
        dlt = s.delete(f"{BASE}/api/agenda-eventos/{eid}", timeout=20)
        deleted.append({"id": eid, "http": dlt.status_code, "error": j(dlt).get("error")})
    listed = s.get(f"{BASE}/api/desafios", params={"q": MARKER, "limit": 100}, timeout=30)
    lb = j(listed)
    leftover = []
    for d in lb.get("desafios") or lb.get("items") or []:
        if MARKER in str(d.get("titulo") or ""):
            leftover.append({"id": d.get("id"), "titulo": d.get("titulo")})
    out["cleanup"]["delete_eventos"] = deleted
    out["cleanup"]["desafios_ainda_listados"] = leftover
    out["cleanup"]["precisa_ecs"] = bool(leftover)
    out["creditos_depois"] = creditos(s)
    out["ids_para_ecs"] = {
        "desafio_main": did,
        "desafio_colab": out["ids"].get("desafio_colab"),
        "marker": MARKER,
    }

    # persist ids for UI + ECS
    Path_ids = __import__("pathlib").Path(r"C:\Projetos\inove4us\scripts\_scan-119-ids.json")
    Path_ids.write_text(json.dumps(out["ids_para_ecs"] | {"ids": out["ids"]}, indent=2), encoding="utf-8")

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
