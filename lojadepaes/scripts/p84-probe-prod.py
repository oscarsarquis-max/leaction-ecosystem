"""Probes live Gigio and vitrine. No order, email or payment."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

ORIGIN = "https://lojadepaes.com.br"
OUT = Path(__file__).resolve().parents[1] / "readme" / "evidence" / "prompt-84" / "prod"
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
        "sources": [
            {"href": item.get("href"), "title": item.get("title") or item.get("label")}
            for item in payload.get("sources") or []
        ],
        "cta": href,
        "cats": (query.get("cats") or [""])[0],
        "mesa": (query.get("mesa") or [""])[0],
        "ids": (query.get("ids") or [""])[0],
        "reply": str(payload.get("reply") or "")[:400],
    }


def main() -> None:
    cases = [
        (
            "frios",
            [{"role": "user", "content": "Vou receber amigos e quero montar uma mesa de frios. Que pães e acompanhamentos você sugere?"}],
        ),
        (
            "sem-carne-alcool",
            [{"role": "user", "content": "Mesa de frios sem carne e sem álcool. O que servir?"}],
        ),
        (
            "sardinhas",
            [{"role": "user", "content": "O que combina com a receita de sardinhas com homus de vocês?"}],
        ),
        (
            "peixe",
            [{"role": "user", "content": "Qual vinho combina com peixe grelhado?"}],
        ),
        (
            "camarao",
            [{"role": "user", "content": "Camarão com molho de limão e ervas. O que combina?"}],
        ),
        (
            "lagosta",
            [{"role": "user", "content": "Lagosta grelhada com manteiga. Qual vinho?"}],
        ),
        (
            "churrasco",
            [{"role": "user", "content": "Vou fazer churrasco de porco e linguiça. Qual vinho?"}],
        ),
        (
            "tabua",
            [{"role": "user", "content": "Qual vinho combina com a tábua de queijos?"}],
        ),
        (
            "pedido",
            [{"role": "user", "content": "Como acompanho o pagamento do meu pedido?"}],
        ),
    ]
    follow = [
        {"role": "user", "content": "O que combina com a receita de sardinhas com homus?"},
        {"role": "assistant", "content": "A receita publicada é a de sardinhas com homus."},
        {"role": "user", "content": "Agora é camarão, sem álcool."},
    ]
    summary = []
    with httpx.Client() as client:
        health = client.get(f"{ORIGIN}/api/v1/health", timeout=20.0).json()
        dump("health.json", health)
        recipes = client.get(f"{ORIGIN}/api/v1/catalog/week-recipes", params={"q": "sardinhas"}, timeout=20.0).json()
        dump("recipe-sardinhas.json", recipes)
        breads = client.get(f"{ORIGIN}/api/v1/catalog/products", timeout=20.0).json()
        dump("catalog-breads.json", breads)
        for name, messages in cases:
            summary.append(summarize(name, chat(client, name, messages)))
        summary.append(summarize("follow-camarao", chat(client, "follow-camarao", follow)))
        for label, params in (
            ("vitrine-frios", {"cats": "queijos,frios,azeites", "mesa": "frios"}),
            ("vitrine-sardinha", {"cats": "vinhos,azeites", "mesa": "sardinha"}),
            ("vitrine-camarao", {"cats": "vinhos,azeites", "mesa": "camarao"}),
            ("vitrine-leitao", {"cats": "vinhos", "mesa": "leitao,salada"}),
            ("vitrine-geral", {}),
        ):
            catalog = client.get(f"{ORIGIN}/api/v1/accompaniments", params=params, timeout=30.0).json()
            dump(f"{label}.json", catalog)
            summary.append(
                {
                    "name": label,
                    "title": catalog.get("title") or (catalog.get("context") or {}).get("title"),
                    "count": len(catalog.get("items") or []),
                    "names": [item.get("name") for item in (catalog.get("items") or [])[:6]],
                }
            )
    dump("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
