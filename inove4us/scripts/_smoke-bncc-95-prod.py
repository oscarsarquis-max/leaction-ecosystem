#!/usr/bin/env python3
"""Smoke 95: persiste 3 códigos BNCC e devolve o que a API gravou. Sem senhas."""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta

import requests

BASE = "https://inove4us.com.br"
EMAIL = "homologador@leaction.com.br"
CODES = ["EF06MA07", "EF06MA08", "EF06MA09"]


def login(email: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=20)
    data = r.json() if r.ok else {}
    if data.get("status") != "granted":
        raise SystemExit(f"login {email}: {data.get('status')}")
    return s


def disciplina_matematica(session: requests.Session) -> int | None:
    r = session.get(f"{BASE}/api/me/cursos", timeout=20)
    cursos = (r.json() or {}).get("cursos") or (r.json() or {}).get("items") or r.json()
    if not isinstance(cursos, list):
        return None
    for curso in cursos:
        cid = curso.get("id")
        if not cid:
            continue
        rd = session.get(f"{BASE}/api/cursos/{cid}/disciplinas", timeout=20)
        discs = (rd.json() or {}).get("disciplinas") or (rd.json() or {}).get("items") or []
        if not isinstance(discs, list):
            continue
        for d in discs:
            nome = str(d.get("nome") or d.get("disciplina_nome") or "")
            if "matem" in nome.casefold():
                return int(d["id"])
    return None


def main() -> int:
    health = requests.get(f"{BASE}/api/health", timeout=15).json()
    s = login(EMAIL)
    disc_id = disciplina_matematica(s)
    dia = (date.today() + timedelta(days=21)).isoformat()
    payload = {
        "tema_aula": "Cobertura 95 — três habilidades",
        "data_planejada": dia,
        "turma_nome": "6º Ano A",
        "disciplina_id": disc_id,
        "habilidades_bncc": CODES,
        "objetivo_aprendizagem": "Prova 95: três temas BNCC na mesma aula.",
        "acolhida": "",
        "conteudo_essencial": "",
        "fechamento_checkout": "",
    }
    r = s.post(f"{BASE}/api/daily/planejar", json=payload, timeout=30)
    body = r.json() if r.content else {}
    aula = body.get("aula") or {}
    got = aula.get("habilidades_bncc") or []
    out = {
        "health": health,
        "http": r.status_code,
        "aula_id": body.get("id") or aula.get("id"),
        "disciplina_id": disc_id,
        "enviados": CODES,
        "gravados": got,
        "tema_aula": aula.get("tema_aula"),
        "error": body.get("error"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    ok = r.status_code in (200, 201) and got == CODES
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
