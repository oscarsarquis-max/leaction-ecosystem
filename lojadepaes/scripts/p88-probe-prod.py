"""Probes live Gigio after Prompt 88. No order or email."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

ORIGIN = "https://lojadepaes.com.br"
OUT = Path(__file__).resolve().parents[1] / "readme" / "evidence" / "prompt-88" / "prod"
OUT.mkdir(parents=True, exist_ok=True)
ARABIA = (
    "Vou dar um jantar com o tema noite das arábias. "
    "Que pão e acompanhamentos vc me recomenda? E bebidas?"
)


def dump(name: str, data: object) -> None:
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    with httpx.Client(timeout=90.0) as client:
        health = client.get(f"{ORIGIN}/api/v1/health")
        status = client.get(f"{ORIGIN}/api/v1/gigio/status")
        home = client.get(f"{ORIGIN}/")
        chat = client.post(
            f"{ORIGIN}/api/v1/gigio/chat",
            json={"messages": [{"role": "user", "content": ARABIA}], "page": {"path": "/"}},
        )
        payload = chat.json() if chat.headers.get("content-type", "").startswith("application/json") else {
            "status_code": chat.status_code,
            "text": chat.text[:800],
        }
        payload["_http"] = chat.status_code
        dump("health.json", {"http": health.status_code, "body": health.json()})
        dump("status.json", status.json())
        dump("chat-arabia.json", payload)
        reply = str(payload.get("reply") or "")
        summary = {
            "health": health.status_code,
            "home": home.status_code,
            "rules": status.json().get("rules_version"),
            "gigio_ready": status.json().get("ready"),
            "chat_http": chat.status_code,
            "unavailable": payload.get("unavailable"),
            "has_invoke": "invoke" in reply.casefold() or "<parameter" in reply.casefold(),
            "reply_preview": reply[:280],
            "cta": (payload.get("cta") or {}).get("label"),
            "builder": (payload.get("builder_cta") or {}).get("label"),
        }
        dump("summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
