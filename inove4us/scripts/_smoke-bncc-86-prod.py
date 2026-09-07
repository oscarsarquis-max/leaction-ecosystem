#!/usr/bin/env python3
"""Smoke 86: cache tema×nivel + metodologia sem IA. Sem senhas."""
from __future__ import annotations

import json
import sys

import requests

BASE = "https://inove4us.com.br"
EMAIL_GERA = "inovador@inove4us.com.br"
EMAIL_CACHE = "homologador@leaction.com.br"


def login(email: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=20)
    data = r.json() if r.ok else {}
    if data.get("status") != "granted":
        raise SystemExit(f"login {email}: {data.get('status')}")
    return s


def main() -> int:
    h = requests.get(f"{BASE}/api/health", timeout=15).json()
    s_gera = login(EMAIL_GERA)
    s_cache = login(EMAIL_CACHE)
    out = {"health": h, "tests": {}}
    payload = {
        "fonte": "bncc",
        "tema": "Sistema de numeração decimal",
        "nivel_turma": "6º ano",
        "habilidade_codigo": "EF06MA01",
        "disciplina": "Matemática",
        "texto_oficial": (
            "Comparar, ordenar, ler e escrever números naturais e números racionais "
            "cuja representação decimal é finita, fazendo uso da reta numérica."
        ),
    }
    r1 = s_gera.post(f"{BASE}/api/daily/conteudo-sugerido", json=payload, timeout=90)
    d1 = r1.json() if r1.content else {}
    out["tests"]["primeira"] = {
        "http": r1.status_code,
        "ia_called": d1.get("ia_called"),
        "cached": d1.get("cached"),
        "code": d1.get("code"),
        "error": d1.get("error"),
        "has_texto": bool(d1.get("texto_montado")),
        "pontos": bool((d1.get("conteudo") or {}).get("pontos_chave")),
    }
    r2 = s_cache.post(f"{BASE}/api/daily/conteudo-sugerido", json=payload, timeout=30)
    d2 = r2.json() if r2.content else {}
    out["tests"]["segunda"] = {
        "http": r2.status_code,
        "ia_called": d2.get("ia_called"),
        "cached": d2.get("cached"),
        "has_texto": bool(d2.get("texto_montado")),
    }
    cats = s_cache.get(f"{BASE}/api/daily/dinamicas", timeout=20)
    cd = cats.json() if cats.content else {}
    first_id = (cd.get("dinamicas") or [{}])[0].get("id")
    out["tests"]["catalogo"] = {"http": cats.status_code, "ia_called": cd.get("ia_called"), "n": cd.get("total"), "id": first_id}
    rm = s_cache.get(f"{BASE}/api/daily/metodologia", params={"id": first_id or "agil_minute_paper", "turma_nome": "6º Ano A"}, timeout=20)
    dm = rm.json() if rm.content else {}
    out["tests"]["metodologia"] = {
        "http": rm.status_code,
        "ia_called": dm.get("ia_called"),
        "fonte": dm.get("fonte"),
        "nome": (dm.get("dinamica") or {}).get("nome"),
        "aee": bool(dm.get("aee")),
        "aee_condicao": (dm.get("aee") or {}).get("condicao_categoria") if dm.get("aee") else None,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    t1, t2, tm = out["tests"]["primeira"], out["tests"]["segunda"], out["tests"]["metodologia"]
    ok = (
        t2.get("cached") is True
        and t2.get("ia_called") is False
        and tm.get("ia_called") is False
        and tm.get("http") == 200
        and (t1.get("http") in (200, 402))
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
