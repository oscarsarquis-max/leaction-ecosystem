#!/usr/bin/env python3
"""Prompt 114 — mural + agenda B2C via check-email. Sem senhas."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

BASE = "https://inove4us.com.br"
MARKER114 = "[TESTE VARREDURA 114]"
MARKER113 = "[TESTE VARREDURA 113]"
TZ = ZoneInfo("America/Sao_Paulo")
HOMOLOG = "homologador@leaction.com.br"
INOVA = "inovador@inove4us.com.br"


def login(email: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") not in ("granted", "ok") and not data.get("id_clie"):
        raise SystemExit(f"login falhou {email}: {data}")
    return s, data


def dump_user(email: str) -> dict:
    s, auth = login(email)
    mural = s.get(f"{BASE}/api/mural", timeout=30)
    agenda = s.get(f"{BASE}/api/agenda-eventos", timeout=30)
    mural_body = mural.json() if mural.ok else {"error": mural.text[:300], "http": mural.status_code}
    agenda_body = agenda.json() if agenda.ok else {"error": agenda.text[:300], "http": agenda.status_code}
    items = mural_body.get("items") or []
    eventos = agenda_body.get("eventos") or agenda_body.get("items") or []
    if not isinstance(eventos, list):
        eventos = []

    def is_com(ev):
        return (ev.get("origem") or "") == "comunicado_escola" or "comunicado" in str(ev.get("origem") or "")

    coms = [e for e in eventos if is_com(e)]
    marker114_mural = [i for i in items if MARKER114 in (i.get("titulo") or "")]
    marker113_mural = [i for i in items if MARKER113 in (i.get("titulo") or "")]
    marker114_ag = [e for e in coms if MARKER114 in (e.get("titulo") or "")]
    marker113_ag = [e for e in coms if MARKER113 in (e.get("titulo") or "")]
    cancelados = [e for e in coms if (e.get("status") or "") == "cancelado"]

    def slim_m(i):
        ini = i.get("data_hora_inicio")
        day = None
        if ini:
            try:
                dt = datetime.fromisoformat(str(ini).replace("Z", "+00:00"))
                day = dt.astimezone(TZ).date().isoformat()
            except ValueError:
                day = str(ini)[:10]
        return {
            "id": i.get("id"),
            "titulo": i.get("titulo"),
            "data_hora_inicio": ini,
            "data_hora_fim": i.get("data_hora_fim"),
            "day_br": day,
        }

    def slim_e(e):
        de = str(e.get("data_evento") or "")
        return {
            "id": e.get("id_evento") or e.get("id"),
            "titulo": e.get("titulo"),
            "data_evento": de,
            "day": de[:10] if de else None,
            "status": e.get("status"),
            "origem": e.get("origem"),
        }

    return {
        "email": email,
        "auth_status": auth.get("status"),
        "id_clie": auth.get("id_clie"),
        "mural_http": mural.status_code,
        "agenda_http": agenda.status_code,
        "mural_n": len(items),
        "mural_114": [slim_m(i) for i in marker114_mural],
        "mural_113": [slim_m(i) for i in marker113_mural],
        "mural_titulos": [i.get("titulo") for i in items],
        "agenda_com_n": len(coms),
        "agenda_114": [slim_e(e) for e in marker114_ag],
        "agenda_113": [slim_e(e) for e in marker113_ag],
        "agenda_cancelados": [slim_e(e) for e in cancelados],
        "agenda_com_titulos": [e.get("titulo") for e in coms],
    }


def main() -> int:
    who = sys.argv[1] if len(sys.argv) > 1 else "both"
    out = {}
    if who in ("both", "homolog"):
        out["homologador"] = dump_user(HOMOLOG)
    if who in ("both", "inova"):
        out["inovador"] = dump_user(INOVA)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
