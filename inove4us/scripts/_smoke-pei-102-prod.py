#!/usr/bin/env python3
"""Smoke 102: 🧩 retrieval canônico 79/81 (TEA×Mapa mental) + apêndice + fallback Dislexia."""
from __future__ import annotations

import json
import sys
import uuid

import requests

BASE = "https://inove4us.com.br"
HOMOLOG = "homologador@leaction.com.br"
MAPA = "agil_mapeamento_mental"
ALUNO_PEI = "Lucas Mendes"


def login(email: str) -> tuple[requests.Session, dict]:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=20)
    data = r.json() if r.content else {}
    if data.get("status") != "granted":
        raise SystemExit(f"login {email}: {data.get('status')}")
    return s, data.get("user") or {}


def creditos(s: requests.Session) -> int | None:
    me = s.get(f"{BASE}/api/auth/me", timeout=20).json()
    u = me.get("user") or me
    try:
        return int(u.get("creditos_ia"))
    except (TypeError, ValueError):
        return None


def adaptar(s: requests.Session, *, perfil: str, aluno: str = "", mid: str = MAPA) -> dict:
    card_id = f"c102-{uuid.uuid4().hex[:8]}"
    r = s.post(
        f"{BASE}/api/kanban/adaptar-pei",
        json={
            "card_id": card_id,
            "titulo_card": "Núcleo do mapa mental",
            "descricao_card": "Escrever o tema no centro da página.",
            "perfil_selecionado": perfil,
            "aluno_nome": aluno or None,
            "metodologia_id": mid,
            "coluna": "para_fazer",
        },
        timeout=90,
    )
    body = r.json() if r.content else {}
    descricao = str(
        (body.get("kanban_task") or {}).get("descricao")
        or (body.get("subcard") or {}).get("descricao")
        or ""
    )
    return {
        "http": r.status_code,
        "ia_called": body.get("ia_called"),
        "fonte": body.get("fonte"),
        "creditos_ia": body.get("creditos_ia"),
        "pei_apendice": (body.get("kanban_task") or {}).get("pei_apendice"),
        "descricao": descricao,
        "error": body.get("error"),
    }


def main() -> int:
    health = requests.get(f"{BASE}/api/health", timeout=15).json()
    s, user = login(HOMOLOG)
    c0 = creditos(s)
    tea = adaptar(s, perfil="TEA")
    c1 = creditos(s)
    lucas = adaptar(s, perfil="TDAH", aluno=ALUNO_PEI)
    c2 = creditos(s)
    disc = adaptar(s, perfil="Dislexia")
    c3 = creditos(s)
    out = {
        "health": {"git_sha": health.get("git_sha"), "ok": health.get("ok")},
        "user": {
            "id_clie": user.get("id_clie"),
            "is_institutional": user.get("is_institutional"),
        },
        "creditos": {"antes": c0, "depois_tea": c1, "depois_lucas": c2, "depois_dislexia": c3},
        "tea_mapa": {
            **{k: v for k, v in tea.items() if k != "descricao"},
            "preview": (tea.get("descricao") or "")[:280],
            "tem_dedo_ou_percorr": "dedo" in (tea.get("descricao") or "").lower()
            or "percorr" in (tea.get("descricao") or "").lower(),
        },
        "tdah_lucas": {
            **{k: v for k, v in lucas.items() if k != "descricao"},
            "preview": (lucas.get("descricao") or "")[:220],
            "tem_apendice": bool(lucas.get("pei_apendice"))
            or "PEI individual" in (lucas.get("descricao") or ""),
        },
        "dislexia": {k: v for k, v in disc.items() if k != "descricao"},
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    ok = (
        tea.get("http") == 200
        and tea.get("ia_called") is False
        and tea.get("fonte") == "card_modificado_79_81"
        and c0 == c1 == c2
        and lucas.get("http") == 200
        and lucas.get("ia_called") is False
        and disc.get("http") == 200
        and disc.get("ia_called") is True
        and (c3 is None or (c2 is not None and c3 == c2 - 1))
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
