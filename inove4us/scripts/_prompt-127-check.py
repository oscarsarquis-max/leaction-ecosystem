#!/usr/bin/env python3
"""GET evento 68 + reabrir checagens B2C."""
import json
import requests

BASE = "https://inove4us.com.br"
s = requests.Session()
r = s.post(f"{BASE}/api/auth/check-email", json={"email": "homologador@leaction.com.br"}, timeout=20)
print("login", r.status_code, r.json().get("status"))
for eid in (68, 65, 66):
    g = s.get(f"{BASE}/api/agenda-eventos/{eid}", timeout=20)
    b = g.json() if g.content else {}
    ev = b.get("evento") or b
    print(json.dumps({"id": eid, "http": g.status_code, "status": ev.get("status"), "tipo": ev.get("tipo"), "titulo": (ev.get("titulo") or "")[:80], "relato": bool(ev.get("relato_sala")), "desafio": ev.get("desafio_id")}, ensure_ascii=False))

aloc = s.get(f"{BASE}/api/me/alocacoes-escola", timeout=20).json()
print("alocacoes", aloc.get("count"), [(a.get("turma_nome") or a.get("turma"), a.get("disciplina_nome") or a.get("disciplina")) for a in (aloc.get("alocacoes") or [])])
mural = s.get(f"{BASE}/api/mural", timeout=20).json()
itens = mural.get("itens") or mural.get("comunicados") or mural.get("items") or mural.get("avisos") or []
print("mural_n", len(itens), "keys", list(mural.keys())[:10])
for it in itens[:6]:
    print(" mural", (it.get("titulo") or it.get("texto") or "")[:80], it.get("publico_alvo") or it.get("tipo"))
avisos = s.get(f"{BASE}/api/avisos-mesa", timeout=20).json()
print("avisos", avisos.get("avisos"))
me = s.get(f"{BASE}/api/auth/me", timeout=20).json()
u = me.get("user") or me
print("creditos", u.get("creditos_ia"))
grafo = s.get(f"{BASE}/api/agenda-eventos/grafo", timeout=20).json()
nos = grafo.get("nos") or grafo.get("nodes") or []
print("grafo", grafo.get("success"), "nos", len(nos))
# eixos? dump keys
print("grafo_keys", list(grafo.keys()))
mesa = s.get("https://inove4us.com.br/api/desafios/3221a3a5-0a5b-4a7a-bb40-8de21bfd9097/mesa", timeout=20).json()
cards = mesa.get("cards") or []
print("mesa_cards", len(cards), "colunas", [c.get("coluna") for c in cards], "pei", [c.get("titulo") for c in cards if c.get("parent_card_id")])
enc = s.get("https://inove4us.com.br/api/desafios/5a6a7ed0-f805-4647-94ea-f87de431bf47", timeout=20).json()
print("encerrado", (enc.get("desafio") or {}).get("encerrado"), (enc.get("desafio") or {}).get("titulo"))
