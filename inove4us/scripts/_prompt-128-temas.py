#!/usr/bin/env python3
"""128 — listar temas BNCC + radar cobertura atual."""
import json
import requests

BASE = "https://inove4us.com.br"
s = requests.Session()
r = s.post(f"{BASE}/api/auth/check-email", json={"email": "homologador@leaction.com.br"}, timeout=20)
print("login", r.status_code, r.json().get("status"))
out = {}
for ano in ("9º ano", "9º Ano", "1ª série", "1ª Série", "1º ano", "Ensino Médio", "EM"):
    g = s.get(f"{BASE}/api/daily/bncc-temas", params={"disciplina": "Matemática", "curso_ano": ano}, timeout=30)
    b = g.json() if g.content else {}
    items = b.get("items") or []
    sample = []
    for t in items[:4]:
        if isinstance(t, dict):
            sample.append({
                "codigo": t.get("habilidade_codigo") or t.get("codigo"),
                "tema": (t.get("tema") or t.get("titulo") or "")[:80],
                "curso_ano": t.get("curso_ano"),
            })
    out[ano] = {"http": g.status_code, "n": b.get("count") or len(items), "sample": sample}
print(json.dumps(out, ensure_ascii=False, indent=2))
