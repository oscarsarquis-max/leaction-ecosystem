#!/usr/bin/env python3
"""Prompt 121 — B2C: fechamento → sugestão de curadoria. Só reporta; não corrige."""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from pathlib import Path

import requests

BASE = "https://inove4us.com.br"
SCHOOL = "https://school.inove4us.com.br"
MARKER = "[TESTE VARREDURA 121]"
HOMOLOG = "homologador@leaction.com.br"
MAPA = "agil_mapeamento_mental"
MET_NOME = "Mapa mental"
STATE = Path(r"C:\Projetos\inove4us\scripts\_scan-121-state.json")


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
        return {"raw": (r.text or "")[:600]}
    return body if isinstance(body, dict) else {"value": body}


def slim_sync(body: dict) -> dict:
    ss = body.get("school_sync") if isinstance(body.get("school_sync"), dict) else {}
    return {
        "ok": ss.get("ok"),
        "status_code": ss.get("status_code"),
        "error": ss.get("error"),
        "skipped": ss.get("skipped"),
        "response": str(ss.get("response") or "")[:300],
    }


def creditos(s: requests.Session) -> int | None:
    me = s.get(f"{BASE}/api/auth/me", timeout=20).json()
    u = me.get("user") or me
    try:
        return int(u.get("creditos_ia"))
    except (TypeError, ValueError):
        return None


def registrar(s: requests.Session, *, titulo: str, turma: str, dias: list[str], cid: str, suffix: str):
    plan = {
        "problema": f"{MARKER} fechamento curadoria",
        "hipotese": "sugestão opcional no relato",
        "causas": [{"titulo": "c1", "descricao": "121"}],
        "plano": {
            "missao": titulo,
            "id_metodologia": MAPA,
            "metodologia_nome": MET_NOME,
            "tarefas_kanban": [
                {
                    "id": cid,
                    "titulo": f"{MARKER} passo metodologia {suffix}",
                    "coluna": "para_fazer",
                    "origem_card": "catalogo",
                    "editado": True,
                }
            ],
        },
    }
    aulas = []
    for i, dia in enumerate(dias):
        aulas.append(
            {
                "data": dia,
                "turma": turma,
                "turno": "noite",
                "modo_execucao": "reinicio" if i == 0 else "continuidade",
                "card_ids": [cid],
                "escopos": {cid: f"{MARKER} aula {i + 1}"},
            }
        )
    r = s.post(
        f"{BASE}/api/agenda-eventos/registrar-aulas",
        json={
            "titulo": titulo,
            "tema": titulo,
            "plan_data": plan,
            "kanban_state": {"tarefas": plan["plano"]["tarefas_kanban"]},
            "causas": plan["causas"],
            "aulas": aulas,
        },
        timeout=40,
    )
    body = j(r)
    evs = body.get("eventos") or []
    return r, body, plan, evs


def concluir(s: requests.Session, eid, *, relato: str, participantes: str, sugestao: str | None):
    payload = {
        "relato_sala": relato,
        "participantes": participantes,
        "ocorrencia_tipo": "concluida",
        "metodologia_usada": MET_NOME,
        "aula_contexto": relato,
    }
    if sugestao:
        payload["has_teacher_adaptations"] = True
        payload["teacher_adaptation_text"] = sugestao
        payload["sugestao_coordenacao"] = sugestao
        payload["texto_sugestao"] = sugestao
    r = s.post(f"{BASE}/api/agenda-eventos/{eid}/concluir-aula", json=payload, timeout=40)
    return r, j(r)


def put_desafio(s: requests.Session, did: str, cid: str, titulo: str):
    return s.put(
        f"{BASE}/api/desafios/{did}",
        json={"kanban_state": {"tarefas": [{"id": cid, "titulo": titulo, "coluna": "fazendo", "origem_card": "catalogo", "editado": True}]}},
        timeout=30,
    )


def slim_aviso(a: dict) -> dict:
    meta = a.get("meta") if isinstance(a.get("meta"), dict) else a.get("meta_json")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {"raw": meta[:120]}
    if not isinstance(meta, dict):
        meta = {}
    return {
        "id": a.get("id"),
        "tipo": a.get("tipo"),
        "professor_b2c_id": a.get("professor_b2c_id"),
        "texto": str(a.get("texto") or "")[:220],
        "rotulo": meta.get("rotulo"),
        "resultado": meta.get("resultado"),
        "retorno": str(meta.get("retorno_docente") or "")[:160],
        "sugestao_resumo": str(meta.get("sugestao_resumo") or "")[:160],
    }


def main() -> int:
    out: dict = {
        "prompt": 121,
        "marker": MARKER,
        "ids": {},
        "item1": {},
        "item2": {},
        "item3": {},
        "avisos_antes_retorno": [],
    }
    b2c_h = requests.get(f"{BASE}/api/health", timeout=20).json()
    sch_h = requests.get(f"{SCHOOL}/api/health", timeout=20).json()
    out["health"] = {
        "b2c": {"ok" : b2c_h.get("ok"), "git_sha": b2c_h.get("git_sha")},
        "school": {"ok": sch_h.get("ok"), "git_sha": sch_h.get("git_sha")},
    }

    s, auth = login(HOMOLOG)
    out["homolog"] = {"id_clie": auth.get("id_clie") or (auth.get("user") or {}).get("id_clie")}
    out["creditos_antes"] = creditos(s)

    suffix = uuid.uuid4().hex[:8]
    out["suffix"] = suffix
    dia0 = (date.today() + timedelta(days=70)).isoformat()
    dia1 = (date.today() + timedelta(days=71)).isoformat()
    dia2 = (date.today() + timedelta(days=72)).isoformat()
    dia3 = (date.today() + timedelta(days=73)).isoformat()
    dia4 = (date.today() + timedelta(days=74)).isoformat()
    dia5 = (date.today() + timedelta(days=75)).isoformat()

    # --- D0: 1 aula aberta só para a UI do Relato (Área 2) — não concluir ---
    t0 = f"{MARKER} relato UI {suffix}"
    cid0 = f"c121u-{suffix}"
    r0, b0, _plan0, evs0 = registrar(
        s, titulo=t0, turma=f"121u-{suffix}", dias=[dia0], cid=cid0, suffix=suffix
    )
    did0 = b0.get("desafio_id") or (b0.get("desafio") or {}).get("id")
    eids0 = [e.get("id_evento") for e in evs0]
    out["ids"]["d0"] = did0
    out["ids"]["eids0"] = eids0
    out["item1"]["d0_aberto_para_ui"] = {
        "http": r0.status_code,
        "id": did0,
        "n": len(eids0),
        "error": b0.get("error"),
        "ok": bool(did0 and eids0),
    }

    # --- D1: cadeia 2 aulas — 1ª sem sugestão (2.1), 2ª com sugestão A ---
    t1 = f"{MARKER} cadeia A {suffix}"
    cid1 = f"c121a-{suffix}"
    r1, b1, plan1, evs1 = registrar(s, titulo=t1, turma=f"121a-{suffix}", dias=[dia1, dia2], cid=cid1, suffix=suffix)
    did1 = b1.get("desafio_id") or (b1.get("desafio") or {}).get("id")
    eids1 = [e.get("id_evento") for e in evs1]
    out["ids"]["d1"] = did1
    out["ids"]["eids1"] = eids1
    out["item1"]["d1_registrar"] = {"http": r1.status_code, "n": len(eids1), "error": b1.get("error")}

    conc1 = None
    if eids1:
        conc1, c1b = concluir(
            s,
            eids1[0],
            relato=f"{MARKER} fechou sem sugestão {suffix}",
            participantes=f"121a-{suffix}",
            sugestao=None,
        )
    else:
        c1b = {}
    g_mid = s.get(f"{BASE}/api/desafios/{did1}", timeout=30) if did1 else None
    dmid = (j(g_mid).get("desafio") if g_mid else {}) or {}
    put_mid = put_desafio(s, did1, cid1, f"{MARKER} ainda 1/2") if did1 else None
    out["item2"]["sem_sugestao"] = {
        "http": conc1.status_code if conc1 else None,
        "ok_fecha": bool(conc1 and conc1.ok and (c1b.get("evento") or {}).get("status") == "concluido"),
        "school_sync": slim_sync(c1b),
        "encerrado_ainda_false": dmid.get("encerrado") is False,
        "put_ainda_200": put_mid.status_code if put_mid else None,
        "ok": bool(conc1 and conc1.ok)
        and dmid.get("encerrado") is False
        and bool(put_mid and put_mid.ok),
    }

    sug_a = f"{MARKER} proposta A: encurtar o passo 2 do mapa mental ({suffix})"
    conc2 = None
    if len(eids1) > 1:
        conc2, c2b = concluir(
            s,
            eids1[1],
            relato=f"{MARKER} fechou COM sugestão A {suffix}",
            participantes=f"121a-{suffix}",
            sugestao=sug_a,
        )
    else:
        c2b = {}
    g_end = s.get(f"{BASE}/api/desafios/{did1}", timeout=30) if did1 else None
    dend = (j(g_end).get("desafio") if g_end else {}) or {}
    put_end = put_desafio(s, did1, cid1, f"{MARKER} DEPOIS") if did1 else None
    put_end_b = j(put_end) if put_end else {}
    out["item1"]["enviar_sugestao_a"] = {
        "http": conc2.status_code if conc2 else None,
        "school_sync": slim_sync(c2b),
        "evento_status": (c2b.get("evento") or {}).get("status"),
        "ok": bool(conc2 and conc2.ok and slim_sync(c2b).get("ok") is True),
    }
    out["item3"]["trava_120_d1"] = {
        "encerrado": dend.get("encerrado"),
        "put_http": put_end.status_code if put_end else None,
        "put_code": put_end_b.get("code"),
        "ok": dend.get("encerrado") is True
        and bool(put_end)
        and put_end.status_code == 403
        and put_end_b.get("code") == "DESAFIO_ENCERRADO",
    }

    # GET reabrir desafio
    g_re = s.get(f"{BASE}/api/desafios/{did1}", timeout=30) if did1 else None
    out["item1"]["reabrir_d1"] = {
        "http": g_re.status_code if g_re else None,
        "encerrado": ((j(g_re).get("desafio") if g_re else {}) or {}).get("encerrado"),
    }

    # --- D2: 1 aula COM sugestão B (2ª pendente do mesmo professor) ---
    t2 = f"{MARKER} cadeia B {suffix}"
    cid2 = f"c121b-{suffix}"
    sug_b = f"{MARKER} proposta B: rotina visual no passo 1 ({suffix})"
    r2, b2, _plan2, evs2 = registrar(s, titulo=t2, turma=f"121b-{suffix}", dias=[dia3], cid=cid2, suffix=suffix)
    did2 = b2.get("desafio_id") or (b2.get("desafio") or {}).get("id")
    eids2 = [e.get("id_evento") for e in evs2]
    out["ids"]["d2"] = did2
    out["ids"]["eids2"] = eids2
    conc_b = None
    if eids2:
        conc_b, cb = concluir(
            s,
            eids2[0],
            relato=f"{MARKER} fechou COM sugestão B {suffix}",
            participantes=f"121b-{suffix}",
            sugestao=sug_b,
        )
    else:
        cb = {}
    g2 = s.get(f"{BASE}/api/desafios/{did2}", timeout=30) if did2 else None
    d2end = (j(g2).get("desafio") if g2 else {}) or {}
    put2 = put_desafio(s, did2, cid2, f"{MARKER} D2 DEPOIS") if did2 else None
    out["item1"]["enviar_sugestao_b"] = {
        "http": conc_b.status_code if conc_b else None,
        "school_sync": slim_sync(cb),
        "ok": bool(conc_b and conc_b.ok and slim_sync(cb).get("ok") is True),
    }
    out["item3"]["trava_120_d2"] = {
        "encerrado": d2end.get("encerrado"),
        "put_http": put2.status_code if put2 else None,
        "put_code": j(put2).get("code") if put2 else None,
        "ok": d2end.get("encerrado") is True
        and bool(put2)
        and put2.status_code == 403
        and j(put2).get("code") == "DESAFIO_ENCERRADO",
    }

    # --- D3: mesma cadeia, DUAS sugestões (merge vs lista) ---
    t3 = f"{MARKER} cadeia C merge {suffix}"
    cid3 = f"c121c-{suffix}"
    sug_c = f"{MARKER} proposta C aula1 merge ({suffix})"
    sug_d = f"{MARKER} proposta D aula2 merge ({suffix})"
    r3, b3, _plan3, evs3 = registrar(s, titulo=t3, turma=f"121c-{suffix}", dias=[dia4, dia5], cid=cid3, suffix=suffix)
    did3 = b3.get("desafio_id") or (b3.get("desafio") or {}).get("id")
    eids3 = [e.get("id_evento") for e in evs3]
    out["ids"]["d3"] = did3
    out["ids"]["eids3"] = eids3
    c3a_r, c3a = (None, {})
    c3b_r, c3b = (None, {})
    if eids3:
        c3a_r, c3a = concluir(
            s,
            eids3[0],
            relato=f"{MARKER} merge aula1 {suffix}",
            participantes=f"121c-{suffix}",
            sugestao=sug_c,
        )
    if len(eids3) > 1:
        c3b_r, c3b = concluir(
            s,
            eids3[1],
            relato=f"{MARKER} merge aula2 {suffix}",
            participantes=f"121c-{suffix}",
            sugestao=sug_d,
        )
    out["item2"]["duas_na_mesma_cadeia"] = {
        "http_1": c3a_r.status_code if c3a_r else None,
        "http_2": c3b_r.status_code if c3b_r else None,
        "sync_1": slim_sync(c3a),
        "sync_2": slim_sync(c3b),
        "ok_fecha": bool(c3a_r and c3a_r.ok and c3b_r and c3b_r.ok),
    }

    avisos = s.get(f"{BASE}/api/avisos-mesa", timeout=20)
    av_body = j(avisos)
    out["avisos_antes_retorno"] = [
        slim_aviso(a)
        for a in (av_body.get("avisos") or [])
        if MARKER in json.dumps(a, ensure_ascii=False, default=str)
        or a.get("tipo") == "resposta_proposta_metodologica"
    ]

    resumo = s.get(f"{BASE}/api/meu-resumo-periodo", timeout=20)
    rb = j(resumo)
    contrib = rb.get("contribuicao") if isinstance(rb.get("contribuicao"), dict) else rb
    blob = json.dumps(rb, ensure_ascii=False, default=str)
    out["item3"]["indice_b2c_professor"] = {
        "http": resumo.status_code,
        "keys": sorted(list(contrib.keys()))[:40] if isinstance(contrib, dict) else None,
        "tem_homologador_email": "homologador@leaction.com.br" in blob.lower(),
        "nota": "visão do próprio professor — índice 55 do coordenador é no School",
    }

    state = {
        "suffix": suffix,
        "marker": MARKER,
        "met_nome": MET_NOME,
        "id_clie": out["homolog"]["id_clie"],
        "d0": did0,
        "d1": did1,
        "d2": did2,
        "d3": did3,
        "eids1": eids1,
        "eids2": eids2,
        "eids3": eids3,
        "sug_a": sug_a,
        "sug_b": sug_b,
        "sug_c": sug_c,
        "sug_d": sug_d,
        "turma_a": f"121a-{suffix}",
        "turma_b": f"121b-{suffix}",
        "turma_c": f"121c-{suffix}",
    }
    state["d0"] = did0
    state["eids0"] = eids0
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    out["state_file"] = str(STATE)
    out["sugestoes"] = {"a": sug_a, "b": sug_b, "c": sug_c, "d": sug_d}

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
