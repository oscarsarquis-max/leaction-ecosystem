#!/usr/bin/env python3
"""Smoke 98: pool institucional, billing bloqueado, geração 86, solo intacto."""
from __future__ import annotations

import json
import sys

import requests

BASE = "https://inove4us.com.br"
HOMOLOG = "homologador@leaction.com.br"
SOLO = "inovador@inove4us.com.br"


def login(email: str) -> tuple[requests.Session, dict]:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=20)
    data = r.json() if r.content else {}
    if data.get("status") != "granted":
        raise SystemExit(f"login {email}: {data.get('status')} http={r.status_code}")
    return s, data.get("user") or {}


def main() -> int:
    health = requests.get(f"{BASE}/api/health", timeout=15).json()
    s_h, u_h = login(HOMOLOG)
    s_s, u_s = login(SOLO)
    me_h = s_h.get(f"{BASE}/api/auth/me", timeout=20)
    me_s = s_s.get(f"{BASE}/api/auth/me", timeout=20)
    uh = me_h.json() if me_h.content else {}
    us = me_s.json() if me_s.content else {}
    user_h = uh.get("user") or uh
    user_s = us.get("user") or us

    bill = s_h.post(f"{BASE}/api/billing/checkout", json={"sku": "golive-50"}, timeout=20)
    bill_j = bill.json() if bill.content else {}

    # Cache conhecido (não gasta crédito) + miss de cache (gasta 1, prova que não é 402).
    cached_payload = {
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
    r_cache = s_h.post(f"{BASE}/api/daily/conteudo-sugerido", json=cached_payload, timeout=30)
    d_cache = r_cache.json() if r_cache.content else {}

    gen_payload = dict(cached_payload)
    gen_payload["nivel_turma"] = "6º ano piloto-98"
    r_gen = s_h.post(f"{BASE}/api/daily/conteudo-sugerido", json=gen_payload, timeout=90)
    d_gen = r_gen.json() if r_gen.content else {}

    after = s_h.get(f"{BASE}/api/auth/me", timeout=20)
    uh2 = after.json() if after.content else {}
    user_h2 = uh2.get("user") or uh2

    accept = s_h.post(
        f"{BASE}/api/school/aceitar-convite",
        json={"instituicao_id": "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"},
        timeout=30,
    )
    accept_j = accept.json() if accept.content else {}
    ia_pool = ((accept_j.get("result") or {}).get("ia_pool") or accept_j.get("ia_pool") or {})

    out = {
        "health": {
            "git_sha": health.get("git_sha") or health.get("sha"),
            "ok": health.get("ok") or health.get("status"),
        },
        "homologador": {
            "id_clie": user_h.get("id_clie") or u_h.get("id_clie"),
            "is_institutional": user_h.get("is_institutional"),
            "creditos_ia": user_h.get("creditos_ia"),
            "instituicao_b2b_id": user_h.get("instituicao_b2b_id"),
        },
        "solo": {
            "id_clie": user_s.get("id_clie") or u_s.get("id_clie"),
            "is_institutional": user_s.get("is_institutional"),
            "creditos_ia": user_s.get("creditos_ia"),
            "instituicao_b2b_id": user_s.get("instituicao_b2b_id"),
        },
        "billing_institutional": {
            "http": bill.status_code,
            "code": bill_j.get("code"),
            "error": bill_j.get("error"),
        },
        "conteudo_cache": {
            "http": r_cache.status_code,
            "cached": d_cache.get("cached"),
            "ia_called": d_cache.get("ia_called"),
            "code": d_cache.get("code"),
        },
        "conteudo_gera": {
            "http": r_gen.status_code,
            "cached": d_gen.get("cached"),
            "ia_called": d_gen.get("ia_called"),
            "code": d_gen.get("code"),
            "has_texto": bool(d_gen.get("texto_montado")),
            "creditos_ia": d_gen.get("creditos_ia"),
        },
        "homologador_depois": {"creditos_ia": user_h2.get("creditos_ia")},
        "aceitar_convite_replay": {
            "http": accept.status_code,
            "ok": accept_j.get("ok"),
            "ia_pool": ia_pool,
            "creditos_ia": (accept_j.get("user") or {}).get("creditos_ia"),
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    ok = (
        bill.status_code == 403
        and bill_j.get("code") == "INSTITUTIONAL_BILLING_BLOCKED"
        and "pool de créditos de IA" in str(bill_j.get("error") or "")
        and user_h.get("is_institutional") is True
        and int(user_h.get("creditos_ia") or 0) >= 50
        and user_s.get("is_institutional") is False
        and r_cache.status_code == 200
        and r_gen.status_code != 402
        and r_gen.status_code != 403
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
