"""Probes live Gigio CTA restore. No order, email or payment."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

ORIGIN = "https://lojadepaes.com.br"
OUT = Path(__file__).resolve().parents[1] / "readme" / "evidence" / "prompt-85" / "prod"
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
    href = ((payload.get("cta") or {}) or {}).get("href") or ""
    query = parse_qs(urlparse(href).query)
    return {
        "name": name,
        "http": payload.get("_http"),
        "cta_label": ((payload.get("cta") or {}) or {}).get("label") or "",
        "cta": href,
        "cats": (query.get("cats") or [""])[0],
        "mesa": (query.get("mesa") or [""])[0],
        "ids": (query.get("ids") or [""])[0],
        "notice": payload.get("notice") or "",
        "sources": [item.get("title") or item.get("label") for item in payload.get("sources") or []],
        "links": [item.get("label") for item in payload.get("links") or []],
        "reply": str(payload.get("reply") or "")[:280],
    }


def main() -> None:
    cases = [
        (
            "sardinhas-combina",
            [{"role": "user", "content": "O que combina com a receita de sardinhas com homus de vocês?"}],
        ),
        (
            "sardinhas-acompanhamento",
            [{"role": "user", "content": "Sugestões de acompanhamento para a receita de sardinhas com homus"}],
        ),
        (
            "sardinhas-vinho",
            [{"role": "user", "content": "Qual vinho combina com a receita de sardinhas com homus?"}],
        ),
        (
            "peixe",
            [{"role": "user", "content": "Qual vinho combina com peixe grelhado?"}],
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
        (
            "nota-guia",
            [{"role": "user", "content": "O Sacramentos Sabina Entre Serras 2025 tem avaliação?"}],
        ),
    ]
    follow = [
        {"role": "user", "content": "O que combina com a receita de sardinhas com homus?"},
        {"role": "assistant", "content": "A receita publicada é a de sardinhas com homus."},
        {"role": "user", "content": "Agora sem álcool."},
    ]
    summary = []
    with httpx.Client() as client:
        dump("health.json", client.get(f"{ORIGIN}/api/v1/health", timeout=20.0).json())
        dump("gigio-status.json", client.get(f"{ORIGIN}/api/v1/gigio/status", timeout=20.0).json())
        for name, messages in cases:
            summary.append(summarize(name, chat(client, name, messages)))
        summary.append(summarize("sem-alcool", chat(client, "sem-alcool", follow)))
    dump("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
