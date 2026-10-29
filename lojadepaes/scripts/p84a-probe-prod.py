"""Probes live Gigio for Adendo 84A. No order, email or payment."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

ORIGIN = "https://lojadepaes.com.br"
OUT = Path(__file__).resolve().parents[1] / "readme" / "evidence" / "prompt-84a" / "prod"
OUT.mkdir(parents=True, exist_ok=True)


def dump(name: str, data: object) -> None:
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def chat(client: httpx.Client, name: str, messages: list[dict]) -> dict:
    response = client.post(
        f"{ORIGIN}/api/v1/gigio/chat",
        json={"messages": messages, "page": {"path": "/"}},
        timeout=90.0,
    )
    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {
        "status_code": response.status_code,
        "text": response.text[:800],
    }
    payload["_http"] = response.status_code
    dump(f"chat-{name}.json", payload)
    return payload


def summarize(name: str, payload: dict) -> dict:
    return {
        "name": name,
        "http": payload.get("_http"),
        "sources": [
            {
                "href": item.get("href"),
                "title": item.get("title") or item.get("label"),
                "role": item.get("retrieval_role"),
                "score_line": item.get("score_line"),
            }
            for item in payload.get("sources") or []
        ],
        "cta": ((payload.get("cta") or {}) or {}).get("href") or "",
        "reply": str(payload.get("reply") or "")[:400],
    }


def main() -> None:
    cases = [
        (
            "sacramentos",
            [{"role": "user", "content": "O Sacramentos Sabina Entre Serras Sauvignon Blanc 2025 tem avaliação?"}],
        ),
        (
            "almeida",
            [{"role": "user", "content": "O Casa Almeida Barreto Paralelas Cabernet Franc 2024 tem nota no Descorchados?"}],
        ),
        (
            "sauvignon-estilo",
            [{"role": "user", "content": "Qual sauvignon blanc combina com peixe grelhado?"}],
        ),
        (
            "peixe",
            [{"role": "user", "content": "Qual vinho combina com peixe grelhado?"}],
        ),
        (
            "adega",
            [{"role": "user", "content": "Vocês usam o guia ADEGA Brasil 2026 para avaliar vinhos?"}],
        ),
        (
            "descorchados-guia",
            [{"role": "user", "content": "O que é o guia Descorchados?"}],
        ),
        (
            "frios",
            [{"role": "user", "content": "Vou receber amigos e quero montar uma mesa de frios. Que pães e acompanhamentos você sugere?"}],
        ),
        (
            "churrasco",
            [{"role": "user", "content": "Vou fazer churrasco de porco e linguiça. Qual vinho?"}],
        ),
        (
            "pedido",
            [{"role": "user", "content": "Como acompanho o pagamento do meu pedido?"}],
        ),
    ]
    summary = []
    with httpx.Client() as client:
        health = client.get(f"{ORIGIN}/api/v1/health", timeout=20.0).json()
        dump("health.json", health)
        status = client.get(f"{ORIGIN}/api/v1/gigio/status", timeout=20.0).json()
        dump("gigio-status.json", status)
        for name, messages in cases:
            summary.append(summarize(name, chat(client, name, messages)))
    dump("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
