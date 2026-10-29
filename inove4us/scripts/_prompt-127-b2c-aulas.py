#!/usr/bin/env python3
"""127 — aulas Campus em tarde/noite (manhã bloqueada por comunicado)."""
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
    if data.get("status") not in ("granted", "ok"):
        raise SystemExit(data)
    return s


def j(r):
    try:
        return r.json() if r.content else {}
    except Exception:
        return {"raw": (r.text or "")[:800]}


def main():
    s = login()
    g = s.get(f"{BASE}/api/desafios/{DID}", timeout=30)
    d = j(g).get("desafio") or {}
    pd = d.get("plan_data") if isinstance(d.get("plan_data"), dict) else {}
    plano = pd.get("plano") if isinstance(pd.get("plano"), dict) else {}
    cards = plano.get("tarefas_kanban") or []
    ids = [str(c.get("id")) for c in cards if isinstance(c, dict) and c.get("id")]
    t1, t2, t3, t4, t5 = (ids + ["t1", "t2", "t3", "t4", "t5"])[:5]
    payload = {
        "titulo": d.get("titulo") or "Operação Campus 2.0 — Projeto Executivo",
        "tema": d.get("tema") or d.get("titulo"),
        "desafio_id": DID,
        "plano_session": str(uuid.uuid4()),
        "plan_data": pd,
        "kanban_state": {"tarefas": [{"id": c.get("id"), "titulo": c.get("titulo"), "coluna": c.get("coluna") or "para_fazer"} for c in cards if isinstance(c, dict)]},
        "causas": pd.get("causas") or [],
        "aulas": [
            {
                "data": HOJE,
                "turma": "6º Ano A",
                "turno": "tarde",
                "modo_execucao": "reinicio",
                "card_ids": [t1, t2],
                "escopos": {
                    t1: "Auditoria de divergência no pátio (trena) — Observação da Realidade",
                    t2: "Filtrar variáveis da planta vs. campo — Pontos-chave",
                },
            },
            {
                "data": HOJE,
                "turma": "1ª Série A",
                "turno": "noite",
                "modo_execucao": "reinicio",
                "card_ids": [t3, t4],
                "escopos": {
                    t3: "Teorizar inflação da construção e juros do orçamento",
                    t4: "Hipóteses de paginação com desperdício abaixo de 5%",
                },
            },
            {
                "data": AMANHA,
                "turma": "9º Ano A",
                "turno": "noite",
                "modo_execucao": "reinicio",
                "card_ids": [t5],
                "escopos": {t5: "Aplicação: pitch do masterplan e ROI solar em Fortaleza"},
            },
        ],
    }
    r = s.post(f"{BASE}/api/agenda-eventos/registrar-aulas", json=payload, timeout=50)
    body = j(r)
    out = {
        "registrar": {
            "http": r.status_code,
            "error": body.get("error"),
            "code": body.get("code"),
            "eventos": [
                {"id": e.get("id_evento"), "turma": e.get("turma"), "turno": e.get("turno"), "data": e.get("data_evento"), "pai": e.get("id_evento_pai")}
                for e in (body.get("eventos") or [])
            ],
        }
    }
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
                "aula_contexto": "Operação Campus 2.0 — tarde, 6º Ano A",
            },
            timeout=40,
        )
        out["concluir_curadoria"] = {"http": rc.status_code, "ok": rc.ok, "body_keys": list(j(rc).keys())[:12], "error": j(rc).get("error")}
    agenda = s.get(f"{BASE}/api/agenda-eventos", params={"mes": HOJE[:7]}, timeout=20)
    slots = []
    for e in j(agenda).get("eventos") or []:
        de = str(e.get("data_evento") or "")
        if de[:10] in (HOJE, AMANHA):
            slots.append({"id": e.get("id_evento"), "data": de, "turma": e.get("turma"), "turno": e.get("turno"), "tipo": e.get("tipo"), "titulo": (e.get("titulo") or "")[:90]})
    out["agenda_hoje_amanha"] = slots
    grafo = j(s.get(f"{BASE}/api/agenda-eventos/grafo", timeout=20))
    out["grafo_n"] = {"nos": len(grafo.get("nos") or grafo.get("nodes") or []), "arestas": len(grafo.get("arestas") or grafo.get("edges") or [])}
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
