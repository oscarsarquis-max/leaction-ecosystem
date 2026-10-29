#!/usr/bin/env python3
"""127 — completar aulas do Campus 2.0 + curadoria + cache roteiro."""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

import requests

BASE = "https://inove4us.com.br"
HOMOLOG = "homologador@leaction.com.br"
DID = "3221a3a5-0a5b-4a7a-bb40-8de21bfd9097"
HOJE = date.today().isoformat()
AMANHA = (date.today() + timedelta(days=1)).isoformat()


def login():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": HOMOLOG}, timeout=30)
    data = r.json() if r.content else {}
    if data.get("status") not in ("granted", "ok") and not data.get("id_clie"):
        raise SystemExit(data)
    return s


def j(r):
    try:
        return r.json() if r.content else {}
    except Exception:
        return {"raw": (r.text or "")[:800]}


def main():
    s = login()
    out = {}
    g = s.get(f"{BASE}/api/desafios/{DID}", timeout=30)
    d = j(g).get("desafio") or {}
    pd = d.get("plan_data") if isinstance(d.get("plan_data"), dict) else {}
    plano = pd.get("plano") if isinstance(pd.get("plano"), dict) else {}
    cards = plano.get("tarefas_kanban") or pd.get("tarefas_kanban") or []
    ids = [str(c.get("id")) for c in cards if isinstance(c, dict) and c.get("id")]
    out["desafio_get"] = {"http": g.status_code, "n_cards": len(ids), "ids": ids, "encerrado": d.get("encerrado")}
    if len(ids) < 5:
        ids = [f"t{i}" for i in range(1, 6)]

    def aulas(dia):
        return [
            {
                "data": dia,
                "turma": "6º Ano A",
                "turno": "manha",
                "modo_execucao": "reinicio",
                "card_ids": [ids[0], ids[1]],
                "escopos": {ids[0]: "Auditoria de divergência no pátio (trena) — Observação da Realidade", ids[1]: "Filtrar variáveis da planta vs. campo — Pontos-chave"},
            },
            {
                "data": dia,
                "turma": "1ª Série A",
                "turno": "tarde",
                "modo_execucao": "reinicio",
                "card_ids": [ids[2], ids[3]],
                "escopos": {ids[2]: "Teorizar inflação da construção e juros do orçamento", ids[3]: "Hipóteses de paginação com desperdício < 5%"},
            },
            {
                "data": dia,
                "turma": "9º Ano A",
                "turno": "noite",
                "modo_execucao": "reinicio",
                "card_ids": [ids[4]],
                "escopos": {ids[4]: "Aplicação: pitch do masterplan e ROI solar (Fortaleza)"},
            },
        ]

    payload = {
        "titulo": d.get("titulo") or "Operação Campus 2.0 — Projeto Executivo",
        "tema": d.get("tema") or d.get("titulo"),
        "desafio_id": DID,
        "plano_session": str(uuid.uuid4()),
        "plan_data": pd or plano,
        "kanban_state": {"tarefas": [{"id": c.get("id"), "titulo": c.get("titulo"), "coluna": c.get("coluna") or "para_fazer"} for c in cards if isinstance(c, dict)]},
        "causas": pd.get("causas") if isinstance(pd, dict) else [],
        "aulas": aulas(HOJE),
    }
    r = s.post(f"{BASE}/api/agenda-eventos/registrar-aulas", json=payload, timeout=50)
    body = j(r)
    out["registrar_hoje"] = {"http": r.status_code, "error": body.get("error"), "code": body.get("code"), "eventos": [{"id": e.get("id_evento"), "turma": e.get("turma"), "turno": e.get("turno"), "data": e.get("data_evento")} for e in (body.get("eventos") or [])]}
    if r.status_code == 409:
        payload["aulas"] = aulas(AMANHA)
        payload["plano_session"] = str(uuid.uuid4())
        r2 = s.post(f"{BASE}/api/agenda-eventos/registrar-aulas", json=payload, timeout=50)
        b2 = j(r2)
        out["registrar_amanha"] = {"http": r2.status_code, "error": b2.get("error"), "code": b2.get("code"), "eventos": [{"id": e.get("id_evento"), "turma": e.get("turma"), "turno": e.get("turno"), "data": e.get("data_evento")} for e in (b2.get("eventos") or [])]}
        r, body = r2, b2

    evs = body.get("eventos") or []
    eids = [e.get("id_evento") for e in evs]
    if eids and eids[0]:
        rc = s.post(
            f"{BASE}/api/agenda-eventos/{eids[0]}/concluir-aula",
            json={
                "relato_sala": (
                    "Turma 6º Ano A iniciou o mapeamento da área externa com trena. "
                    "Lucas Mendes (TEA) usou o roteiro visual do subcard PEI e concluiu "
                    "o registro das medidas do pátio com apoio de um par."
                ),
                "participantes": "6º Ano A — 6 alunos presentes, incluindo Lucas Mendes",
                "has_teacher_adaptations": True,
                "sugestao_coordenacao": (
                    "Na Auditoria de Divergência, o Minute Paper de saída funcionou melhor em duplas "
                    "heterogêneas: um aluno mede, o outro registra na planta. Sugiro formalizar esse "
                    "pareamento na diretriz da escola para a Abordagem Problematizadora."
                ),
                "metodologia_usada": "Abordagem Problematizadora",
                "aula_contexto": "Operação Campus 2.0 — Passo 1, 6º Ano A",
            },
            timeout=40,
        )
        out["concluir_curadoria"] = {"http": rc.status_code, "body": j(rc)}
    else:
        out["concluir_curadoria"] = {"skipped": True}

    rp = s.put(f"{BASE}/api/daily/13", json={"status": "planejado"}, timeout=20)
    out["daily_planejado"] = {"http": rp.status_code, "status": (j(rp).get("aula") or {}).get("status")}

    cache = s.post(
        f"{BASE}/api/daily/conteudo-sugerido",
        json={
            "fonte": "bncc",
            "tema": "Ângulos: noção, usos e medida",
            "nivel_turma": "6º ano",
            "habilidade_codigo": "EF06MA25",
            "disciplina": "Matemática",
            "texto_oficial": "Ângulos: noção, usos e medida",
        },
        timeout=40,
    )
    dc = j(cache)
    out["conteudo_cache"] = {"http": cache.status_code, "cached": dc.get("cached"), "ia_called": dc.get("ia_called")}

    agenda = s.get(f"{BASE}/api/agenda-eventos", params={"mes": HOJE[:7]}, timeout=20)
    ev_ag = j(agenda).get("eventos") or []
    out["agenda_slots"] = []
    for e in ev_ag:
        de = str(e.get("data_evento") or "")
        if de[:10] in (HOJE, AMANHA) and e.get("tipo") in ("aula_dia", "aula_eduscrum"):
            out["agenda_slots"].append({"id": e.get("id_evento"), "data": de, "turma": e.get("turma"), "turno": e.get("turno"), "tipo": e.get("tipo"), "titulo": (e.get("titulo") or "")[:90]})

    grafo = s.get(f"{BASE}/api/agenda-eventos/grafo", timeout=20)
    gb = j(grafo)
    out["grafo"] = {"http": grafo.status_code, "n_nos": len(gb.get("nos") or gb.get("nodes") or []), "n_arestas": len(gb.get("arestas") or gb.get("edges") or [])}
    me = s.get(f"{BASE}/api/auth/me", timeout=20)
    u = j(me).get("user") or j(me)
    out["creditos"] = u.get("creditos_ia")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
