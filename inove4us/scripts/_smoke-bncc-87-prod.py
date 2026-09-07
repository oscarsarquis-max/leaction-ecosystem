#!/usr/bin/env python3
"""Smoke 87: BNCC seletor em produção. Não imprime senhas."""
from __future__ import annotations

import json
import sys

import requests

BASE = "https://inove4us.com.br"
EMAILS = [
    "homologador@leaction.com.br",
    "inovador@inove4us.com.br",
    "marina.alves@escolateste.edu.br",
]


def login(email: str) -> requests.Session | None:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=20)
    if not r.ok:
        print(json.dumps({"email": email, "login_http": r.status_code}))
        return None
    data = r.json()
    if data.get("status") != "granted":
        print(json.dumps({"email": email, "login": data.get("status")}))
        return None
    return s


def main() -> int:
    health = requests.get(f"{BASE}/api/health", timeout=15).json()
    out = {"health": health, "tests": {}}
    session = None
    used = None
    for email in EMAILS:
        session = login(email)
        if session:
            used = email
            break
    if not session:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 2
    out["email"] = used

    r = session.get(
        f"{BASE}/api/daily/bncc-temas",
        params={"disciplina": "Matemática", "curso_ano": "6º ano"},
        timeout=20,
    )
    data = r.json() if r.content else {}
    items = data.get("items") or []
    out["tests"]["matematica_6"] = {
        "http": r.status_code,
        "count": data.get("count"),
        "n_items": len(items),
        "sample": items[:3],
    }

    r2 = session.get(
        f"{BASE}/api/daily/bncc-temas",
        params={"disciplina": "Ciências", "curso_ano": "6º ano"},
        timeout=20,
    )
    d2 = r2.json() if r2.content else {}
    items2 = d2.get("items") or []
    ef06 = next((i for i in items2 if i.get("habilidade_codigo") == "EF06CI04"), None)
    out["tests"]["ciencias_6"] = {
        "http": r2.status_code,
        "count": d2.get("count"),
        "ef06ci04": ef06,
    }

    r3 = session.get(f"{BASE}/api/instituicoes", timeout=20)
    insts = (r3.json() or {}).get("instituicoes") or []
    ementa_ok = None
    disc_names = []
    for inst in insts[:3]:
        pers = session.get(
            f"{BASE}/api/instituicoes/{inst['id']}/periodos-letivos", timeout=20
        )
        periodos = (pers.json() or {}).get("periodos") if pers.ok else []
        if not isinstance(periodos, list):
            periodos = []
        for per in periodos[:4]:
            pid = per.get("id")
            if not pid:
                continue
            cr = session.get(f"{BASE}/api/periodos-letivos/{pid}/cursos", timeout=20)
            cursos = (cr.json() or {}).get("cursos") or []
            for cur in cursos:
                dr = session.get(f"{BASE}/api/cursos/{cur['id']}/disciplinas", timeout=20)
                discs = (dr.json() or {}).get("disciplinas") or []
                for d in discs:
                    disc_names.append(d.get("nome"))
                    if (d.get("nome") or "") in ("Matemática", "Ciências"):
                        ementa_ok = {
                            "nome": d.get("nome"),
                            "ementa_prefix": str(d.get("ementa") or "")[:80],
                            "ementa_len": len(str(d.get("ementa") or "")),
                        }
    out["tests"]["ementa_espelho"] = ementa_ok
    out["tests"]["disciplinas_visiveis"] = sorted({n for n in disc_names if n})[:20]

    print(json.dumps(out, ensure_ascii=False, indent=2))
    mat_ok = len(items) >= 30
    ci_ok = bool(ef06) and "materiais sintéticos" in str(ef06.get("texto_oficial") or "").lower()
    return 0 if mat_ok and ci_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
