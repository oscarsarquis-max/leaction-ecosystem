#!/usr/bin/env python3
"""120 — confirmação pós-deploy: 403 quando encerrado; 200 com cadeia 1/2."""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

import requests

BASE = "https://inove4us.com.br"
MARKER = "[TESTE VARREDURA 120]"
HOMOLOG = "homologador@leaction.com.br"
COLAB = "sandbox999@leaction.com.br"
MAPA = "agil_mapeamento_mental"


def login(email: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=30)
    data = r.json() if r.content else {}
    if data.get("status") not in ("granted", "ok") and not data.get("id_clie"):
        raise RuntimeError(f"login {email}: {data}")
    return s


def j(r: requests.Response) -> dict:
    if not r.content:
        return {}
    try:
        body = r.json()
    except Exception:
        return {"raw": r.text[:500]}
    return body if isinstance(body, dict) else {"value": body}


def tarefas(desafio: dict) -> list:
    pd = desafio.get("plan_data") if isinstance(desafio.get("plan_data"), dict) else {}
    plano = pd.get("plano") if isinstance(pd.get("plano"), dict) else {}
    raw = plano.get("tarefas_kanban") or pd.get("tarefas_kanban") or []
    return [t for t in raw if isinstance(t, dict)] if isinstance(raw, list) else []


def main() -> int:
    health = requests.get(f"{BASE}/api/health", timeout=20).json()
    out: dict = {"health": {"ok": health.get("ok"), "git_sha": health.get("git_sha")}, "ids": {}}
    s = login(HOMOLOG)
    suffix = uuid.uuid4().hex[:8]
    cid = f"c120-{suffix}"
    cid_c = f"c120c-{suffix}"
    titulo = f"{MARKER} {suffix}"
    dia1 = (date.today() + timedelta(days=52)).isoformat()
    dia2 = (date.today() + timedelta(days=53)).isoformat()
    turma = f"120-{suffix}"
    plan = {
        "problema": f"{MARKER} trava",
        "hipotese": "403 so quando encerrado",
        "causas": [{"titulo": "c1", "descricao": "120"}],
        "plano": {"missao": titulo, "id_metodologia": MAPA, "tarefas_kanban": []},
    }
    r = s.post(f"{BASE}/api/desafios", json={"titulo": titulo, "tema": titulo, "plan_data": plan}, timeout=30)
    did = j(r).get("desafio_id") or (j(r).get("desafio") or {}).get("id")
    out["ids"]["desafio"] = did
    cards = [
        {"id": cid, "titulo": f"{MARKER} cat", "coluna": "para_fazer", "origem_card": "catalogo", "editado": False},
    ]
    p1 = s.put(f"{BASE}/api/desafios/{did}", json={"kanban_state": {"tarefas": cards}}, timeout=30)
    g1 = s.get(f"{BASE}/api/desafios/{did}", timeout=30)
    d1 = j(g1).get("desafio") or {}
    cards2 = [{**cards[0], "coluna": "fazendo", "titulo": f"{MARKER} cat EDITADO", "editado": True}]
    p2 = s.put(f"{BASE}/api/desafios/{did}", json={"kanban_state": {"tarefas": cards2}}, timeout=30)
    g2 = s.get(f"{BASE}/api/desafios/{did}", timeout=30)
    t2 = next((t for t in tarefas(j(g2).get("desafio") or {}) if t.get("id") == cid), {})
    pei = s.post(
        f"{BASE}/api/kanban/adaptar-pei",
        json={
            "card_id": cid,
            "titulo_card": t2.get("titulo") or "cat",
            "descricao_card": "passo",
            "perfil_selecionado": "TEA",
            "metodologia_id": MAPA,
            "desafio_id": did,
            "coluna": "fazendo",
        },
        timeout=90,
    )
    pei_b = j(pei)
    mesa_pei = s.get(f"{BASE}/api/desafios/{did}/mesa", timeout=30)
    mesa_cards = j(mesa_pei).get("cards") or []
    cards3 = cards2 + [
        {"id": cid_c, "titulo": f"{MARKER} custom", "coluna": "para_fazer", "origem_card": "custom", "editado": False}
    ]
    p3 = s.put(f"{BASE}/api/desafios/{did}", json={"kanban_state": {"tarefas": cards3}}, timeout=30)
    g3 = s.get(f"{BASE}/api/desafios/{did}", timeout=30)
    custom_ok = any(t.get("id") == cid_c for t in tarefas(j(g3).get("desafio") or {}))
    out["item3"] = {
        "78_sem_id_evento": {"put": p1.status_code, "reabrir": p1.ok and any(t.get("id") == cid for t in tarefas(d1)), "ok": p1.ok},
        "editar_sem_evento": {"put": p2.status_code, "titulo": t2.get("titulo"), "editado": t2.get("editado"), "ok": t2.get("editado") is True},
        "mover_rastro": {"coluna": t2.get("coluna"), "origem": t2.get("origem_card"), "ok": t2.get("coluna") == "fazendo"},
        "102_76_pei": {
            "http": pei.status_code,
            "fonte": pei_b.get("fonte"),
            "ia_called": pei_b.get("ia_called"),
            "reabrir": any(str(c.get("parent_card_id") or "") == cid for c in mesa_cards),
            "ok": pei.ok and pei_b.get("fonte") == "card_modificado_79_81" and pei_b.get("ia_called") is False,
        },
        "custom": {"put": p3.status_code, "ok": custom_ok},
    }

    reg = s.post(
        f"{BASE}/api/agenda-eventos/registrar-aulas",
        json={
            "titulo": titulo,
            "tema": titulo,
            "desafio_id": did,
            "plano_session": str(uuid.uuid4()),
            "plan_data": {**plan, "plano": {**plan["plano"], "tarefas_kanban": cards3}},
            "kanban_state": {"tarefas": cards3},
            "causas": plan["causas"],
            "aulas": [
                {
                    "data": dia1,
                    "turma": turma,
                    "turno": "noite",
                    "modo_execucao": "reinicio",
                    "card_ids": [cid, cid_c],
                    "escopos": {cid: "aula 1 cat 120", cid_c: "aula 1 custom 120"},
                },
                {
                    "data": dia2,
                    "turma": turma,
                    "turno": "noite",
                    "modo_execucao": "continuidade",
                    "card_ids": [cid, cid_c],
                    "escopos": {cid: "aula 2 cat 120", cid_c: "aula 2 custom 120"},
                },
            ],
        },
        timeout=40,
    )
    rb = j(reg)
    evs = rb.get("eventos") or []
    eids = [e.get("id_evento") for e in evs]
    out["ids"]["eventos"] = eids
    out["registrar"] = {"http": reg.status_code, "pais": [e.get("id_evento_pai") for e in evs]}
    put_ev = None
    if eids:
        put_ev = s.put(
            f"{BASE}/api/agenda-eventos/{eids[0]}/estado",
            json={"kanban_state": {"tarefas": [{**cards3[0], "aula_id": eids[0], "titulo": f"{MARKER} com evento"}]}},
            timeout=30,
        )
    out["item3"]["editar_com_id_evento"] = {
        "put": put_ev.status_code if put_ev else None,
        "ok": bool(put_ev and put_ev.ok),
    }

    conc1 = s.post(
        f"{BASE}/api/agenda-eventos/{eids[0]}/concluir-aula",
        json={"relato_sala": f"{MARKER} so a primeira", "participantes": turma},
        timeout=30,
    ) if eids else None
    g_mid = s.get(f"{BASE}/api/desafios/{did}", timeout=30)
    dmid = j(g_mid).get("desafio") or {}
    put_mid = s.put(
        f"{BASE}/api/desafios/{did}",
        json={"kanban_state": {"tarefas": [{**cards3[0], "titulo": f"{MARKER} ainda 1/2"}]}},
        timeout=30,
    )
    out["item2_cadeia"] = {
        "concluir_1": conc1.status_code if conc1 else None,
        "encerrado": dmid.get("encerrado"),
        "put_http": put_mid.status_code,
        "ok": dmid.get("encerrado") is False and put_mid.ok,
    }

    conc2 = s.post(
        f"{BASE}/api/agenda-eventos/{eids[1]}/concluir-aula",
        json={"relato_sala": f"{MARKER} segunda e ultima", "participantes": turma},
        timeout=30,
    ) if len(eids) > 1 else None
    g_end = s.get(f"{BASE}/api/desafios/{did}", timeout=30)
    dend = j(g_end).get("desafio") or {}
    put_end = s.put(
        f"{BASE}/api/desafios/{did}",
        json={"kanban_state": {"tarefas": [{**cards3[0], "titulo": f"{MARKER} DEPOIS"}]}},
        timeout=30,
    )
    put_end_b = j(put_end)
    g_after = s.get(f"{BASE}/api/desafios/{did}", timeout=30)
    t_after = next((t for t in tarefas(j(g_after).get("desafio") or {}) if t.get("id") == cid), {})
    put_estado = None
    if eids:
        put_estado = s.put(
            f"{BASE}/api/agenda-eventos/{eids[0]}/estado",
            json={"kanban_state": {"tarefas": cards3}},
            timeout=30,
        )
    out["item2_encerrado"] = {
        "concluir_2": conc2.status_code if conc2 else None,
        "encerrado": dend.get("encerrado"),
        "put_desafio_http": put_end.status_code,
        "put_code": put_end_b.get("code"),
        "put_estado_http": put_estado.status_code if put_estado else None,
        "nao_persistiu_depois": "DEPOIS" not in str(t_after.get("titulo") or ""),
        "ok": dend.get("encerrado") is True
        and put_end.status_code == 403
        and put_end_b.get("code") == "DESAFIO_ENCERRADO",
    }

    # dois professores — segundo desafio, só A conclui
    sb = login(COLAB)
    cid_b = f"c120b-{suffix}"
    titulo_b = f"{MARKER} colab {suffix}"
    plan_b = {
        "problema": f"{MARKER} colab",
        "hipotese": "trava por desafio",
        "causas": [{"titulo": "c1", "descricao": "colab"}],
        "plano": {"missao": titulo_b, "tarefas_kanban": [{"id": cid_b, "titulo": f"{MARKER} colab card", "coluna": "para_fazer"}]},
    }
    dia_a = (date.today() + timedelta(days=54)).isoformat()
    dia_b = (date.today() + timedelta(days=55)).isoformat()
    ra = s.post(
        f"{BASE}/api/agenda-eventos/registrar-aulas",
        json={
            "titulo": titulo_b,
            "tema": titulo_b,
            "plan_data": plan_b,
            "kanban_state": {"tarefas": plan_b["plano"]["tarefas_kanban"]},
            "causas": plan_b["causas"],
            "aulas": [{
                "data": dia_a, "turma": f"{turma}-A", "turno": "tarde", "modo_execucao": "reinicio",
                "card_ids": [cid_b], "escopos": {cid_b: "A realiza 120"},
            }],
        },
        timeout=40,
    )
    ba = j(ra)
    did_b = ba.get("desafio_id")
    ev_a = (ba.get("eventos") or [{}])[0]
    out["ids"]["desafio_colab"] = did_b
    out["ids"]["ev_a"] = ev_a.get("id_evento")
    conv = s.post(f"{BASE}/api/desafios/{did_b}/convidar", json={"email": COLAB, "papel_ou_parte": "120", "card_id": cid_b}, timeout=30) if did_b else None
    token = (j(conv).get("colaborador") or {}).get("token_convite") if conv else None
    if token:
        sb.post(f"{BASE}/api/convites/{token}/aceitar", json={}, timeout=30)
    rb2 = sb.post(
        f"{BASE}/api/desafios/{did_b}/replicar",
        json={"turma": f"{turma}-B", "turno": "tarde", "aulas": [{
            "titulo": "Parte B 120", "data": dia_b, "turno": "tarde", "modo_execucao": "reinicio",
            "card_ids": [cid_b], "escopos": {cid_b: "B realiza 120"},
        }]},
        timeout=40,
    ) if did_b else None
    ev_b = (j(rb2).get("eventos") or [{}])[0] if rb2 else {}
    out["ids"]["ev_b"] = ev_b.get("id_evento")
    if ev_a.get("id_evento"):
        s.post(f"{BASE}/api/agenda-eventos/{ev_a['id_evento']}/concluir-aula", json={"relato_sala": f"{MARKER} A", "participantes": f"{turma}-A"}, timeout=30)
    ga = s.get(f"{BASE}/api/desafios/{did_b}", timeout=30) if did_b else None
    da = (j(ga).get("desafio") if ga else {}) or {}
    put_a = s.put(f"{BASE}/api/desafios/{did_b}", json={"kanban_state": {"tarefas": [{"id": cid_b, "titulo": f"{MARKER} A edit", "coluna": "fazendo"}]}}, timeout=30) if did_b else None
    put_b = sb.put(f"{BASE}/api/desafios/{did_b}", json={"kanban_state": {"tarefas": [{"id": cid_b, "titulo": f"{MARKER} B edit", "coluna": "para_fazer"}]}}, timeout=30) if did_b else None
    out["item3_dois_prof"] = {
        "encerrado": da.get("encerrado"),
        "put_a": put_a.status_code if put_a else None,
        "put_b": put_b.status_code if put_b else None,
        "ok": da.get("encerrado") is False and bool(put_a and put_a.ok) and bool(put_b and put_b.ok),
    }

    r80 = s.post(f"{BASE}/api/daily/planejar", json={"data_planejada": (date.today() + timedelta(days=60)).isoformat()}, timeout=20)
    out["item3_80"] = {"http": r80.status_code, "error": j(r80).get("error"), "ok": r80.status_code == 400}

    listed = s.get(f"{BASE}/api/desafios", params={"q": MARKER, "limit": 50}, timeout=30)
    leftover = [d.get("id") for d in (j(listed).get("desafios") or []) if MARKER in str(d.get("titulo") or "")]
    out["desafios_restantes"] = leftover
    out["ok"] = (
        out["item2_cadeia"]["ok"]
        and out["item2_encerrado"]["ok"]
        and out["item3"]["78_sem_id_evento"]["ok"]
        and out["item3"]["102_76_pei"]["ok"]
        and out["item3"]["custom"]["ok"]
        and out["item3_dois_prof"]["ok"]
        and out["item3_80"]["ok"]
    )
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
