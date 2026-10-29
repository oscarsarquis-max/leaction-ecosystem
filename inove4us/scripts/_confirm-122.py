#!/usr/bin/env python3
"""122 — confirma curadoria por aula na mesma cadeia + regressão 121/120."""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from pathlib import Path

import requests

BASE = "https://inove4us.com.br"
SCHOOL = "https://school.inove4us.com.br"
MARKER = "[TESTE VARREDURA 122]"
HOMOLOG = "homologador@leaction.com.br"
MAPA = "agil_mapeamento_mental"
MET_NOME = "Mapa mental"
STATE = Path(r"C:\Projetos\inove4us\scripts\_scan-122-state.json")


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
        return {"raw": (r.text or "")[:500]}
    return body if isinstance(body, dict) else {"value": body}


def slim_sync(body: dict) -> dict:
    ss = body.get("school_sync") if isinstance(body.get("school_sync"), dict) else {}
    resp = str(ss.get("response") or "")
    cid = None
    try:
        parsed = json.loads(resp) if resp.startswith("{") else {}
        cid = ((parsed.get("result") or {}).get("curadoria_id"))
    except Exception:
        cid = None
    return {
        "ok": ss.get("ok"),
        "status_code": ss.get("status_code"),
        "curadoria_id": cid,
        "response": resp[:280],
    }


def registrar(s, *, titulo: str, turma: str, dias: list[str], cid: str):
    plan = {
        "problema": f"{MARKER} curadoria por aula",
        "hipotese": "duas pendentes na mesma cadeia",
        "causas": [{"titulo": "c1", "descricao": "122"}],
        "plano": {
            "missao": titulo,
            "id_metodologia": MAPA,
            "metodologia_nome": MET_NOME,
            "tarefas_kanban": [
                {
                    "id": cid,
                    "titulo": f"{MARKER} passo {cid}",
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
    return r, body, [e.get("id_evento") for e in (body.get("eventos") or [])]


def concluir(s, eid, *, relato: str, participantes: str, sugestao: str | None):
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


def put_desafio(s, did: str, cid: str, titulo: str):
    return s.put(
        f"{BASE}/api/desafios/{did}",
        json={
            "kanban_state": {
                "tarefas": [
                    {
                        "id": cid,
                        "titulo": titulo,
                        "coluna": "fazendo",
                        "origem_card": "catalogo",
                        "editado": True,
                    }
                ]
            }
        },
        timeout=30,
    )


def main() -> int:
    out: dict = {"prompt": 122, "marker": MARKER, "ids": {}}
    b2c_h = requests.get(f"{BASE}/api/health", timeout=20).json()
    sch_h = requests.get(f"{SCHOOL}/api/health", timeout=20).json()
    out["health"] = {
        "b2c": {"ok": b2c_h.get("ok"), "git_sha": b2c_h.get("git_sha")},
        "school": {"ok": sch_h.get("ok"), "git_sha": sch_h.get("git_sha")},
    }
    s, auth = login(HOMOLOG)
    out["homolog"] = {"id_clie": auth.get("id_clie") or (auth.get("user") or {}).get("id_clie")}
    suffix = uuid.uuid4().hex[:8]
    out["suffix"] = suffix
    dia1 = (date.today() + timedelta(days=81)).isoformat()
    dia2 = (date.today() + timedelta(days=82)).isoformat()
    dia3 = (date.today() + timedelta(days=83)).isoformat()
    dia4 = (date.today() + timedelta(days=84)).isoformat()

    # D1: mesma cadeia, duas sugestões distintas (bug 121 / item 2.3)
    t1 = f"{MARKER} cadeia {suffix}"
    cid1 = f"c122a-{suffix}"
    sug_c = f"{MARKER} proposta C aula1 ({suffix})"
    sug_d = f"{MARKER} proposta D aula2 ({suffix})"
    r1, b1, eids1 = registrar(s, titulo=t1, turma=f"122a-{suffix}", dias=[dia1, dia2], cid=cid1)
    did1 = b1.get("desafio_id") or (b1.get("desafio") or {}).get("id")
    out["ids"]["d1"] = did1
    out["ids"]["eids1"] = eids1
    c1, b_c1 = concluir(s, eids1[0], relato=f"{MARKER} aula1 {suffix}", participantes=f"122a-{suffix}", sugestao=sug_c) if eids1 else (None, {})
    put_mid = put_desafio(s, did1, cid1, f"{MARKER} ainda 1/2") if did1 else None
    c2, b_c2 = concluir(s, eids1[1], relato=f"{MARKER} aula2 {suffix}", participantes=f"122a-{suffix}", sugestao=sug_d) if len(eids1) > 1 else (None, {})
    g_end = s.get(f"{BASE}/api/desafios/{did1}", timeout=30) if did1 else None
    dend = (j(g_end).get("desafio") if g_end else {}) or {}
    put_end = put_desafio(s, did1, cid1, f"{MARKER} DEPOIS") if did1 else None
    sync1, sync2 = slim_sync(b_c1), slim_sync(b_c2)
    out["item2_mesma_cadeia"] = {
        "registrar": r1.status_code,
        "conc1": c1.status_code if c1 else None,
        "conc2": c2.status_code if c2 else None,
        "curadoria_1": sync1.get("curadoria_id"),
        "curadoria_2": sync2.get("curadoria_id"),
        "ids_distintos": bool(sync1.get("curadoria_id") and sync2.get("curadoria_id") and sync1.get("curadoria_id") != sync2.get("curadoria_id")),
        "put_meio_200": put_mid.status_code if put_mid else None,
        "encerrado": dend.get("encerrado"),
        "put_fim": put_end.status_code if put_end else None,
        "put_code": j(put_end).get("code") if put_end else None,
        "sync1": sync1,
        "sync2": sync2,
    }

    # D2: desafio distinto, uma sugestão (regressão 121 desafios diferentes)
    t2 = f"{MARKER} outro {suffix}"
    cid2 = f"c122b-{suffix}"
    sug_b = f"{MARKER} proposta B outro desafio ({suffix})"
    r2, b2, eids2 = registrar(s, titulo=t2, turma=f"122b-{suffix}", dias=[dia3], cid=cid2)
    did2 = b2.get("desafio_id") or (b2.get("desafio") or {}).get("id")
    out["ids"]["d2"] = did2
    out["ids"]["eids2"] = eids2
    c_b, b_b = concluir(s, eids2[0], relato=f"{MARKER} B {suffix}", participantes=f"122b-{suffix}", sugestao=sug_b) if eids2 else (None, {})
    put2 = put_desafio(s, did2, cid2, f"{MARKER} D2 DEPOIS") if did2 else None
    out["item2_desafios_distintos"] = {
        "http": c_b.status_code if c_b else None,
        "curadoria": slim_sync(b_b).get("curadoria_id"),
        "put": put2.status_code if put2 else None,
        "put_code": j(put2).get("code") if put2 else None,
        "ok": bool(c_b and c_b.ok and slim_sync(b_b).get("ok")),
    }

    # D3: fechar SEM sugestão (regressão 3.1)
    t3 = f"{MARKER} sem sugestao {suffix}"
    cid3 = f"c122c-{suffix}"
    r3, b3, eids3 = registrar(s, titulo=t3, turma=f"122c-{suffix}", dias=[dia4], cid=cid3)
    did3 = b3.get("desafio_id") or (b3.get("desafio") or {}).get("id")
    out["ids"]["d3"] = did3
    out["ids"]["eids3"] = eids3
    c_s, b_s = concluir(s, eids3[0], relato=f"{MARKER} sem texto {suffix}", participantes=f"122c-{suffix}", sugestao=None) if eids3 else (None, {})
    out["item3_sem_sugestao"] = {
        "http": c_s.status_code if c_s else None,
        "curadoria_id": slim_sync(b_s).get("curadoria_id"),
        "ok_fecha": bool(c_s and c_s.ok),
        "sem_curadoria": slim_sync(b_s).get("curadoria_id") in (None, ""),
    }

    state = {
        "suffix": suffix,
        "marker": MARKER,
        "d1": did1,
        "d2": did2,
        "d3": did3,
        "eids1": eids1,
        "eids2": eids2,
        "sug_c": sug_c,
        "sug_d": sug_d,
        "sug_b": sug_b,
    }
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    out["sugestoes"] = {"c": sug_c, "d": sug_d, "b": sug_b}
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
