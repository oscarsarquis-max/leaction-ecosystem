#!/usr/bin/env python3
"""Prompt 123 — mural + agenda B2C via check-email. Sem senhas."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

BASE = "https://inove4us.com.br"
MARKER = "[TESTE VARREDURA 123]"
MARKER114 = "[TESTE VARREDURA 114]"
MARKER113 = "[TESTE VARREDURA 113]"
TZ = ZoneInfo("America/Sao_Paulo")
HOMOLOG = "homologador@leaction.com.br"
INOVA = "inovador@inove4us.com.br"


def login(email: str):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") not in ("granted", "ok") and not data.get("id_clie"):
        raise SystemExit(f"login falhou {email}: {data}")
    return s, data


def day_br(iso) -> str | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ).date().isoformat()
    except ValueError:
        return str(iso)[:10]


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
        return (ev.get("origem") or "") == "comunicado_escola"

    coms = [e for e in eventos if is_com(e)]
    m123 = [i for i in items if MARKER in (i.get("titulo") or "")]
    a123 = [e for e in coms if MARKER in (e.get("titulo") or "")]

    mural_order = [i.get("titulo") for i in m123]
    mural_starts = [i.get("data_hora_inicio") for i in m123]
    desc = True
    parsed = []
    for iso in mural_starts:
        try:
            parsed.append(datetime.fromisoformat(str(iso).replace("Z", "+00:00")))
        except Exception:
            parsed.append(None)
    if len(parsed) >= 2 and all(parsed):
        desc = all(parsed[i] >= parsed[i + 1] for i in range(len(parsed) - 1))

    mural_ids = {i.get("origem_comunicado_school_id") or i.get("id") for i in m123}
    agenda_titles = {e.get("titulo") for e in a123}

    return {
        "email": email,
        "auth_status": auth.get("status"),
        "id_clie": auth.get("id_clie"),
        "mural_http": mural.status_code,
        "agenda_http": agenda.status_code,
        "mural_error": mural_body.get("error") if not mural.ok else None,
        "mural_n": len(items),
        "mural_total_campo": mural_body.get("total"),
        "mural_123_n": len(m123),
        "mural_123_titulos": mural_order,
        "mural_123_inicios": mural_starts,
        "mural_123_days_br": [day_br(i.get("data_hora_inicio")) for i in m123],
        "mural_order_inicio_desc": desc,
        "mural_113_n": len([i for i in items if MARKER113 in (i.get("titulo") or "")]),
        "mural_114_n": len([i for i in items if MARKER114 in (i.get("titulo") or "")]),
        "agenda_com_n": len(coms),
        "agenda_123_n": len(a123),
        "agenda_123_titulos": [e.get("titulo") for e in a123],
        "agenda_123_days": [str(e.get("data_evento") or "")[:10] for e in a123],
        "agenda_123_days_br": [day_br(e.get("data_evento")) for e in a123],
        "consistencia_titulos_mural_em_agenda": all(
            t in agenda_titles for t in mural_order
        ),
        "mural_ids": list(mural_ids),
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
