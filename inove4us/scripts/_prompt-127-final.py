#!/usr/bin/env python3
"""127 — checagem final pós-curadoria."""
import json
import requests

BASE = "https://inove4us.com.br"
s = requests.Session()
s.post(f"{BASE}/api/auth/check-email", json={"email": "homologador@leaction.com.br"}, timeout=20)
out = {}
me = s.get(f"{BASE}/api/auth/me", timeout=20).json()
u = me.get("user") or me
out["creditos"] = u.get("creditos_ia")
out["institutional"] = u.get("is_institutional")
aloc = s.get(f"{BASE}/api/me/alocacoes-escola", timeout=20).json()
out["alocacoes"] = [
    {"turma": a.get("turma_nome") or a.get("turma"), "disc": a.get("disciplina_nome") or a.get("disciplina"), "curso": a.get("curso_nome")}
    for a in (aloc.get("alocacoes") or [])
]
mural = s.get(f"{BASE}/api/mural", timeout=20).json()
itens = mural.get("items") or []
out["mural"] = [{"titulo": (i.get("titulo") or "")[:80], "tipo": i.get("tipo")} for i in itens]
avisos = s.get(f"{BASE}/api/avisos-mesa", timeout=20).json()
out["avisos"] = [
    {"id": a.get("id"), "tipo": a.get("tipo"), "texto": (a.get("texto") or "")[:160]}
    for a in (avisos.get("avisos") or [])
]
agenda = s.get(f"{BASE}/api/agenda-eventos", params={"mes": "2026-09"}, timeout=20).json()
out["hoje"] = []
for e in agenda.get("eventos") or []:
    de = str(e.get("data_evento") or "")
    if de.startswith("2026-09-15") or de.startswith("2026-09-16"):
        out["hoje"].append({"id": e.get("id_evento"), "quando": de, "turma": e.get("turma"), "turno": e.get("turno"), "tipo": e.get("tipo"), "status": e.get("status"), "titulo": (e.get("titulo") or "")[:70]})
grafo = s.get(f"{BASE}/api/agenda-eventos/grafo", timeout=20).json()
nodes = grafo.get("nodes") or []
out["grafo"] = {
    "n_nodes": len(nodes),
    "n_edges": len(grafo.get("edges") or []),
    "hoje_horarios": sorted({str(n.get("data_evento") or n.get("quando") or "")[11:19] for n in nodes if str(n.get("data_evento") or n.get("quando") or "").startswith("2026-09-15")}),
}
g1 = s.get("https://inove4us.com.br/api/desafios/3221a3a5-0a5b-4a7a-bb40-8de21bfd9097", timeout=20).json()
d1 = g1.get("desafio") or {}
out["campus"] = {"titulo": d1.get("titulo"), "encerrado": d1.get("encerrado")}
g2 = s.get("https://inove4us.com.br/api/desafios/5a6a7ed0-f805-4647-94ea-f87de431bf47", timeout=20).json()
d2 = g2.get("desafio") or {}
out["sintese"] = {"titulo": d2.get("titulo"), "encerrado": d2.get("encerrado")}
put = s.put(
    "https://inove4us.com.br/api/desafios/5a6a7ed0-f805-4647-94ea-f87de431bf47",
    json={"kanban_state": {"tarefas": [{"id": "x", "titulo": "nope"}]}},
    timeout=20,
)
out["put_encerrado"] = {"http": put.status_code, "code": (put.json() if put.content else {}).get("code")}
mesa = s.get("https://inove4us.com.br/api/desafios/3221a3a5-0a5b-4a7a-bb40-8de21bfd9097/mesa", timeout=20).json()
out["mesa"] = {
    "n_cards": len(mesa.get("cards") or []),
    "pei": [c.get("titulo") for c in (mesa.get("cards") or []) if c.get("parent_card_id")],
    "aulas": [(e.get("id_evento"), e.get("status"), e.get("turma"), e.get("turno")) for e in (mesa.get("eventos") or mesa.get("aulas") or [])][:6],
}
daily = s.get(f"{BASE}/api/daily/13", timeout=20).json()
aula = daily.get("aula") or {}
out["daily"] = {"id": 13, "status": aula.get("status"), "tema": aula.get("tema_aula"), "met": aula.get("dinamica_ativa_id")}
aloc2 = s.get(f"{BASE}/api/me/alocacoes-escola", timeout=20).json()
out["persist_aloc"] = aloc2.get("count")
print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
