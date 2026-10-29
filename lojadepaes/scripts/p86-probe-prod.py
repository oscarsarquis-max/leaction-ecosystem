"""Probes live hamburger meal + 85A/regression. No order, email or payment."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

ORIGIN = "https://lojadepaes.com.br"
OUT = Path(__file__).resolve().parents[1] / "readme" / "evidence" / "prompt-86" / "prod"
OUT.mkdir(parents=True, exist_ok=True)

HAMBURGER_Q = (
    "queremos fazer um hamburguer bem legal, com batatas e molho. "
    "que sugestao de acompanhamento vc poderia me dar? "
    "que tipo de pao vc aconselha? e que bebidas ficariam bem?"
)


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
        "forma": (query.get("forma") or [""])[0],
        "ids": (query.get("ids") or [""])[0],
        "notice": payload.get("notice") or "",
        "sources": [item.get("title") or item.get("label") for item in payload.get("sources") or []],
        "links": [item.get("label") for item in payload.get("links") or []],
        "reply": str(payload.get("reply") or "")[:400],
    }


def catalog(client: httpx.Client, name: str, path: str) -> dict:
    response = client.get(f"{ORIGIN}{path}", timeout=30.0)
    payload = response.json()
    payload["_http"] = response.status_code
    dump(f"catalog-{name}.json", payload)
    items = payload.get("items") or []
    return {
        "name": name,
        "http": response.status_code,
        "title": payload.get("title"),
        "cats": sorted({item.get("category") for item in items}),
        "names": [item.get("name") for item in items][:8],
        "occasions": sorted({story.get("occasion") for story in payload.get("stories") or []}),
        "verified_count": len(items),
    }


def main() -> None:
    cases = [
        ("hamburguer", [{"role": "user", "content": HAMBURGER_Q}]),
        (
            "sardinhas-combina",
            [{"role": "user", "content": "O que combina com a receita de sardinhas com homus de vocês?"}],
        ),
        (
            "frios",
            [{"role": "user", "content": "Vou receber amigos e quero montar uma mesa de frios. Que pães e acompanhamentos você sugere?"}],
        ),
        ("pedido", [{"role": "user", "content": "Como acompanho o pagamento do meu pedido?"}]),
        ("nota-guia", [{"role": "user", "content": "O Sacramentos Sabina Entre Serras 2025 tem avaliação?"}]),
    ]
    follows = [
        (
            "prefiro-cerveja",
            [
                {"role": "user", "content": HAMBURGER_Q},
                {"role": "assistant", "content": "Cerveja e batatas palito. Sem pão de hambúrguer no catálogo."},
                {"role": "user", "content": "prefiro cerveja"},
            ],
        ),
        (
            "sem-alcool",
            [
                {"role": "user", "content": HAMBURGER_Q},
                {"role": "assistant", "content": "Cerveja e batatas palito."},
                {"role": "user", "content": "sem álcool"},
            ],
        ),
        (
            "fritar-nao-chips",
            [
                {"role": "user", "content": HAMBURGER_Q},
                {"role": "assistant", "content": "Cerveja e batatas."},
                {"role": "user", "content": "quero batatas para fritar, não chips"},
            ],
        ),
        (
            "so-bebidas",
            [
                {"role": "user", "content": HAMBURGER_Q},
                {"role": "assistant", "content": "Cerveja e batatas."},
                {"role": "user", "content": "só as bebidas"},
            ],
        ),
    ]
    summary = []
    catalogs = []
    with httpx.Client() as client:
        dump("health.json", client.get(f"{ORIGIN}/api/v1/health", timeout=20.0).json())
        dump("gigio-status.json", client.get(f"{ORIGIN}/api/v1/gigio/status", timeout=20.0).json())
        for name, messages in cases:
            summary.append(summarize(name, chat(client, name, messages)))
        for name, messages in follows:
            summary.append(summarize(name, chat(client, name, messages)))
        catalogs.append(catalog(client, "hamburguer", "/api/v1/accompaniments?cats=cervejas,batatas&mesa=hamburguer"))
        catalogs.append(catalog(client, "ghost", "/api/v1/accompaniments?ids=MLBGHOST"))
        catalogs.append(catalog(client, "sardinhas", "/api/v1/accompaniments?cats=azeites&mesa=sardinha"))
        catalogs.append(catalog(client, "frios", "/api/v1/accompaniments?cats=frios,queijos,azeites&mesa=frios"))
    dump("summary.json", summary)
    dump("catalogs.json", catalogs)
    print(json.dumps({"chats": summary, "catalogs": catalogs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
