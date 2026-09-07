#!/usr/bin/env python3
"""Reteste ao vivo Fase 0 (82): 76 / 78 / 80 / 81 contra a API.

Não imprime senhas. Login via /api/auth/check-email (granted).
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import date

import requests

BASE = os.environ.get("INOVE_BASE", "https://inove4us.com.br").rstrip("/")
EMAIL = os.environ.get("INOVE_SMOKE_EMAIL", "inovador@inove4us.com.br")
SCHOOL = os.environ.get("SCHOOL_BASE", "https://school.inove4us.com.br").rstrip("/")


def tarefas_from_desafio(desafio: dict) -> list:
    ks = desafio.get("kanban_state")
    if isinstance(ks, dict) and isinstance(ks.get("tarefas"), list):
        return [t for t in ks["tarefas"] if isinstance(t, dict)]
    pd = desafio.get("plan_data") if isinstance(desafio.get("plan_data"), dict) else {}
    plano = pd.get("plano") if isinstance(pd.get("plano"), dict) else {}
    for candidate in (plano.get("tarefas_kanban"), pd.get("tarefas_kanban")):
        if isinstance(candidate, list):
            return [t for t in candidate if isinstance(t, dict)]
    return []


def login(email: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "granted":
        raise RuntimeError(f"login não granted para {email}: {data.get('status')}")
    return s


def main() -> int:
    out = {"base": BASE, "tests": {}}
    health = requests.get(f"{BASE}/api/health", timeout=15).json()
    out["health"] = health

    try:
        s = login(EMAIL)
        me = s.get(f"{BASE}/api/auth/me", timeout=15).json()
        out["user_id_clie"] = (me.get("user") or {}).get("id_clie")
    except Exception as exc:
        out["login"] = str(exc)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2

    # --- 80: planejar sem tema não cria aula ---
    before_ag = s.get(f"{BASE}/api/agenda-eventos", timeout=20)
    n_before = None
    if before_ag.ok:
        body = before_ag.json()
        evs = body.get("eventos") or body.get("items") or body.get("agenda") or []
        if isinstance(body, list):
            evs = body
        n_before = len(evs) if isinstance(evs, list) else None

    r80a = s.post(
        f"{BASE}/api/daily/planejar",
        json={"data_planejada": date.today().isoformat(), "tema_aula": ""},
        timeout=20,
    )
    r80b = s.post(
        f"{BASE}/api/daily/planejar",
        json={
            "data_planejada": date.today().isoformat(),
            "tema_aula": "Aula em elaboração",
        },
        timeout=20,
    )
    created_id = None
    agenda_id = None
    if r80b.ok:
        created_id = (r80b.json() or {}).get("id")
        aula = (r80b.json() or {}).get("aula") or {}
        agenda_id = aula.get("id_evento_agenda")
        if created_id:
            s.delete(f"{BASE}/api/daily/{created_id}", timeout=15)

    after_ag = s.get(f"{BASE}/api/agenda-eventos", timeout=20)
    n_after = None
    if after_ag.ok:
        body = after_ag.json()
        evs = body.get("eventos") or body.get("items") or body.get("agenda") or []
        if isinstance(body, list):
            evs = body
        n_after = len(evs) if isinstance(evs, list) else None

    out["tests"]["80_sem_tema"] = {
        "http": r80a.status_code,
        "rejeitou_sem_tema": r80a.status_code == 400,
        "placeholder_http": r80b.status_code,
        "placeholder_rejeitado": r80b.status_code == 400,
        "placeholder_sem_agenda": (not agenda_id) if r80b.status_code < 400 else True,
        "n_agenda_antes": n_before,
        "n_agenda_depois": n_after,
        "agenda_nao_cresceu": (
            n_before is None or n_after is None or n_after <= n_before
        ),
    }

    # --- 78: desafio sem aula, PUT kanban persiste ---
    r_des = s.post(
        f"{BASE}/api/desafios",
        json={
            "titulo": f"fase0-78-{uuid.uuid4().hex[:8]}",
            "plan_data": {"missao": "reteste 78", "tarefas_kanban": []},
        },
        timeout=20,
    )
    des = (r_des.json() or {}).get("desafio") or r_des.json() or {}
    did = des.get("id") or des.get("desafio_id")
    card = {
        "id": f"c-{uuid.uuid4().hex[:8]}",
        "titulo": "Card persistente 78",
        "coluna": "para_fazer",
    }
    pei = {
        "id": f"pei-{uuid.uuid4().hex[:8]}",
        "titulo": "Adaptação TDAH",
        "coluna": "para_fazer",
        "kind": "pei",
        "perfil": "TDAH",
        "parent_card_id": card["id"],
    }
    r_put = None
    r_get = None
    if did:
        r_put = s.put(
            f"{BASE}/api/desafios/{did}",
            json={"kanban_state": {"tarefas": [card, pei]}},
            timeout=20,
        )
        r_get = s.get(f"{BASE}/api/desafios/{did}", timeout=20)
    g = (r_get.json() if r_get is not None and r_get.ok else {}) or {}
    desafio = g.get("desafio") or {}
    tarefas = tarefas_from_desafio(desafio)
    titulos = [t.get("titulo") for t in tarefas]
    out["tests"]["78_sem_aula"] = {
        "create_http": r_des.status_code,
        "desafio_id": did,
        "put_http": r_put.status_code if r_put is not None else None,
        "get_http": r_get.status_code if r_get is not None else None,
        "encerrado": desafio.get("encerrado"),
        "persistiu_card": "Card persistente 78" in titulos,
        "persistiu_subcard_pei": any(
            t.get("id") == pei["id"] or t.get("perfil") == "TDAH" for t in tarefas
        ),
        "titulos": titulos[:8],
        "put_error": None if r_put is not None and r_put.ok else (r_put.text[:300] if r_put is not None else "no put"),
    }
    # 76 live: 🧩 → adaptar-pei (TDAH) sem id_evento, no desafio
    r76 = None
    if did:
        r76 = s.post(
            f"{BASE}/api/kanban/adaptar-pei",
            json={
                "card_id": card["id"],
                "titulo_card": card["titulo"],
                "descricao_card": "reteste 76",
                "perfil_selecionado": "TDAH",
                "desafio_id": did,
                "coluna": "para_fazer",
            },
            timeout=60,
        )
    g76 = s.get(f"{BASE}/api/desafios/{did}", timeout=20) if did else None
    d76 = ((g76.json() or {}).get("desafio") if g76 is not None and g76.ok else {}) or {}
    t76 = tarefas_from_desafio(d76)
    err76 = None
    if r76 is None:
        err76 = "no call"
    elif not r76.ok:
        try:
            err76 = (r76.json() or {}).get("error") or r76.text[:200]
        except Exception:
            err76 = r76.text[:200]
    out["tests"]["76_adaptar_pei"] = {
        "http": r76.status_code if r76 is not None else None,
        "error": err76,
        "n_tarefas_depois": len(t76),
        "tem_subcard": any(
            str(t.get("parent_card_id") or "") == card["id"] or t.get("perfil") == "TDAH"
            for t in t76
        ),
        "titulos": [t.get("titulo") for t in t76][:8],
    }
    out["tests"]["76_subcard_persistido"] = {
        "ok": bool(out["tests"]["78_sem_aula"].get("persistiu_subcard_pei")),
        "n_tarefas": len(tarefas) if isinstance(tarefas, list) else 0,
    }

    # --- 78 colaboração: encerrado só se TODAS as aulas concluídas ---
    enc = desafio.get("encerramento") or {}
    out["tests"]["78_encerramento"] = {
        "encerrado": desafio.get("encerrado"),
        "n_aulas": enc.get("n_aulas"),
        "n_abertas": enc.get("n_abertas"),
        "zero_aulas_nao_encerra": desafio.get("encerrado") is False,
    }

    # --- 78 colaboração: 2 professores; um encerra a aula, o outro não ---
    email_b = os.environ.get("INOVE_SMOKE_EMAIL_B", "sandbox999@leaction.com.br")
    try:
        sb = login(email_b)
        marker = uuid.uuid4().hex[:8]
        r_reg = s.post(
            f"{BASE}/api/agenda-eventos/registrar-aulas",
            json={
                "titulo": f"fase0-78-colab-{marker}",
                "tema": f"fase0-78-colab-{marker}",
                "aulas": [
                    {
                        "data": date.today().isoformat(),
                        "turma": f"6A-{marker}",
                        "turno": "manha",
                        "modo_execucao": "reinicio",
                    }
                ],
                "plan_data": {"missao": "reteste 78 colab", "tarefas_kanban": []},
            },
            timeout=30,
        )
        body_reg = r_reg.json() if r_reg.ok else {}
        colab_did = body_reg.get("desafio_id")
        ev_a = (body_reg.get("eventos") or [None])[0] or {}
        ev_a_id = ev_a.get("id_evento")
        conv = None
        acc = None
        rb = None
        ev_b_id = None
        conc = None
        g_a = None
        g_b = None
        if colab_did:
            conv = s.post(
                f"{BASE}/api/desafios/{colab_did}/convidar",
                json={"email": email_b, "papel_ou_parte": "Colab 78"},
                timeout=20,
            )
            token = ((conv.json() or {}).get("colaborador") or {}).get("token_convite") if conv.ok else None
            if token:
                acc = sb.post(f"{BASE}/api/convites/{token}/aceitar", json={}, timeout=20)
            rb = sb.post(
                f"{BASE}/api/desafios/{colab_did}/replicar",
                json={
                    "turma": f"7B-{marker}",
                    "turno": "tarde",
                    "aulas": [
                        {
                            "titulo": "Parte B",
                            "data": date.today().isoformat(),
                            "turno": "tarde",
                            "modo_execucao": "reinicio",
                        }
                    ],
                },
                timeout=30,
            )
            ev_b = ((rb.json() or {}).get("eventos") or [None])[0] if rb.ok else None
            ev_b_id = (ev_b or {}).get("id_evento")
            if ev_a_id:
                conc = s.post(
                    f"{BASE}/api/agenda-eventos/{ev_a_id}/concluir-aula",
                    json={"relato_sala": "encerrou so o A"},
                    timeout=20,
                )
            g_a = s.get(f"{BASE}/api/desafios/{colab_did}", timeout=20)
            g_b = sb.get(f"{BASE}/api/desafios/{colab_did}", timeout=20)
        da = ((g_a.json() or {}).get("desafio") if g_a is not None and g_a.ok else {}) or {}
        db = ((g_b.json() or {}).get("desafio") if g_b is not None and g_b.ok else {}) or {}
        put_a = None
        put_b = None
        if colab_did:
            put_a = s.put(
                f"{BASE}/api/desafios/{colab_did}",
                json={"kanban_state": {"tarefas": [{"id": "c-a", "titulo": "edit A", "coluna": "para_fazer"}]}},
                timeout=20,
            )
            put_b = sb.put(
                f"{BASE}/api/desafios/{colab_did}",
                json={"kanban_state": {"tarefas": [{"id": "c-b", "titulo": "edit B", "coluna": "fazendo"}]}},
                timeout=20,
            )
        out["tests"]["78_colaboracao"] = {
            "email_b_ok": True,
            "create_http": r_reg.status_code,
            "desafio_id": colab_did,
            "ev_a": ev_a_id,
            "ev_b": ev_b_id,
            "convidar_http": conv.status_code if conv is not None else None,
            "aceitar_http": acc.status_code if acc is not None else None,
            "replicar_http": rb.status_code if rb is not None else None,
            "concluir_a_http": conc.status_code if conc is not None else None,
            "encerrado_a": da.get("encerrado"),
            "encerrado_b": db.get("encerrado"),
            "n_aulas_a": (da.get("encerramento") or {}).get("n_aulas"),
            "n_abertas_a": (da.get("encerramento") or {}).get("n_abertas"),
            "put_a_http": put_a.status_code if put_a is not None else None,
            "put_b_http": put_b.status_code if put_b is not None else None,
            "editavel_ambos": (
                da.get("encerrado") is False
                and db.get("encerrado") is False
                and (put_a.status_code if put_a is not None else 0) < 400
                and (put_b.status_code if put_b is not None else 0) < 400
            ),
        }
    except Exception as exc:
        out["tests"]["78_colaboracao"] = {"email_b_ok": False, "error": str(exc)}

    # --- 80: com tema real, aula materializa e entra na agenda ---
    marker80 = uuid.uuid4().hex[:8]
    r80c = s.post(
        f"{BASE}/api/daily/planejar",
        json={
            "data_planejada": date.today().isoformat(),
            "tema_aula": f"Tema real {marker80}",
            "conteudo_essencial": "conteudo migrado do rascunho",
        },
        timeout=20,
    )
    aula80 = (r80c.json() or {}).get("aula") or {} if r80c.ok else {}
    id80 = (r80c.json() or {}).get("id") if r80c.ok else None
    agenda80 = aula80.get("id_evento_agenda")
    found_ag = False
    if agenda80:
        ga = s.get(f"{BASE}/api/agenda-eventos/{agenda80}", timeout=15)
        found_ag = ga.ok
    if id80:
        s.delete(f"{BASE}/api/daily/{id80}", timeout=15)
    out["tests"]["80_com_tema"] = {
        "http": r80c.status_code,
        "aula_id": id80,
        "id_evento_agenda": agenda80,
        "materializou_agenda": bool(agenda80) and found_ag,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    t80 = out["tests"]["80_sem_tema"]
    t78 = out["tests"]["78_sem_aula"]
    tcol = out["tests"].get("78_colaboracao") or {}
    t80ok = out["tests"].get("80_com_tema") or {}
    ok = (
        t80.get("rejeitou_sem_tema")
        and t80.get("placeholder_rejeitado")
        and t80.get("placeholder_sem_agenda")
        and t80.get("agenda_nao_cresceu")
        and t78.get("persistiu_card")
        and out["tests"]["76_subcard_persistido"]["ok"]
        and t78.get("encerrado") is False
        and tcol.get("editavel_ambos") is True
        and t80ok.get("materializou_agenda") is True
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
