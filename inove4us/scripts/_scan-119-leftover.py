#!/usr/bin/env python3
"""119 — localiza restos de teste e tenta DELETE de eventos restantes."""
from __future__ import annotations

import json

import requests

BASE = "https://inove4us.com.br"
MARKER = "[TESTE VARREDURA 119]"
EMAILS = [
    "homologador@leaction.com.br",
    "sandbox999@leaction.com.br",
]


def login(email: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=20)
    data = r.json()
    if data.get("status") not in ("granted", "ok") and not data.get("id_clie"):
        raise RuntimeError(f"{email}: {data}")
    return s


def main():
    out = {}
    for email in EMAILS:
        s = login(email)
        desafios = s.get(f"{BASE}/api/desafios", params={"q": MARKER, "limit": 100}, timeout=30)
        dj = desafios.json() if desafios.content else {}
        items = dj.get("desafios") or dj.get("items") or []
        slim_d = [{"id": d.get("id"), "titulo": d.get("titulo")} for d in items if MARKER in str(d.get("titulo") or "")]
        agenda = s.get(f"{BASE}/api/agenda-eventos", timeout=30)
        aj = agenda.json() if agenda.content else {}
        evs = aj.get("eventos") or aj.get("items") or []
        if not isinstance(evs, list):
            evs = []
        marker_ev = [
            {
                "id": e.get("id_evento") or e.get("id"),
                "titulo": e.get("titulo"),
                "status": e.get("status"),
                "tipo": e.get("tipo"),
                "desafio_id": e.get("desafio_id"),
                "id_clie": e.get("id_clie"),
            }
            for e in evs
            if MARKER in str(e.get("titulo") or "")
            or str(e.get("desafio_id") or "") in {
                "f062ff9f-b961-4224-b39b-e6df04efd59b",
                "0716138b-8abb-4e5d-8bc1-e42aeabe1f82",
            }
        ]
        deleted = []
        for e in marker_ev:
            eid = e.get("id")
            if not eid:
                continue
            dlt = s.delete(f"{BASE}/api/agenda-eventos/{eid}", timeout=20)
            body = dlt.json() if dlt.content else {}
            deleted.append({"id": eid, "http": dlt.status_code, "error": body.get("error")})
        mesas = []
        for d in slim_d:
            m = s.get(f"{BASE}/api/desafios/{d['id']}/mesa", timeout=30)
            mb = m.json() if m.content else {}
            evm = mb.get("eventos") or []
            mesas.append(
                {
                    "id": d["id"],
                    "n_eventos_mesa": len(evm) if isinstance(evm, list) else None,
                    "eventos": [
                        {"id": x.get("id_evento"), "titulo": x.get("titulo"), "status": x.get("status")}
                        for x in (evm or [])[:10]
                    ]
                    if isinstance(evm, list)
                    else None,
                    "n_cards": len(mb.get("cards") or []),
                }
            )
        out[email] = {
            "desafios": slim_d,
            "agenda_marker": marker_ev,
            "deleted": deleted,
            "mesas": mesas,
        }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
