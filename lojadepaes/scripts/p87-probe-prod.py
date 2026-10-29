"""Probes live Gigio ↔ Criador. No order, email or payment."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

ORIGIN = "https://lojadepaes.com.br"
OUT = Path(__file__).resolve().parents[1] / "readme" / "evidence" / "prompt-87" / "prod"
OUT.mkdir(parents=True, exist_ok=True)

SANDWICH_Q = (
    "Quero um sanduíche para receber amigos, com pão de farinha branca "
    "e fermentação natural, em pão de forma."
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


def main() -> None:
    with httpx.Client(timeout=90.0) as client:
        status = client.get(f"{ORIGIN}/api/v1/gigio/status").json()
        dump("status.json", status)
        catalog = client.get(f"{ORIGIN}/api/v1/catalog/bread-builder").json()
        dump("builder-catalog.json", {
            "flours": [row.get("slug") or row.get("name") for row in catalog.get("flours") or []],
            "doughs": [row.get("slug") or row.get("name") for row in catalog.get("doughs") or []],
            "inclusions": [row.get("slug") or row.get("name") for row in catalog.get("ingredients") or []],
            "shapes": [row.get("slug") or row.get("name") for row in catalog.get("shapes") or []],
            "price_cents": catalog.get("price_cents"),
        })
        sandwich = chat(client, "sanduiche", [{"role": "user", "content": SANDWICH_Q}])
        builder_cta = sandwich.get("builder_cta") or {}
        token = ""
        href = str(builder_cta.get("href") or "")
        if "proposta=" in href:
            token = parse_qs(urlparse(href.replace("/?", "/?")).query).get("proposta", [""])[0]
            if not token and "proposta=" in href:
                token = href.split("proposta=", 1)[1].split("#", 1)[0]
        proposal = {}
        if token:
            response = client.get(f"{ORIGIN}/api/v1/catalog/bread-builder/proposal", params={"token": token})
            proposal = response.json() if response.status_code == 200 else {"_http": response.status_code, "text": response.text[:400]}
            dump("proposal.json", proposal)
        flour = next((row for row in catalog.get("flours") or [] if row.get("slug") == "farinha-branca-strong-white"), None)
        dough = next((row for row in catalog.get("doughs") or [] if row.get("slug") == "fermentacao-natural-curta"), None)
        shape = next((row for row in catalog.get("shapes") or [] if row.get("slug") == "pao-de-forma"), None)
        tip = {}
        if flour and dough and shape:
            response = client.post(
                f"{ORIGIN}/api/v1/gigio/builder-tip",
                json={
                    "flour_id": flour["id"],
                    "dough_id": dough["id"],
                    "ingredient_ids": [],
                    "shape_id": shape["id"],
                    "free_text": "",
                    "occasion": "sanduíche para amigos",
                },
                timeout=90.0,
            )
            tip = response.json() if response.headers.get("content-type", "").startswith("application/json") else {
                "status_code": response.status_code,
                "text": response.text[:800],
            }
            tip["_http"] = response.status_code
            dump("builder-tip.json", tip)
        health = client.get(f"{ORIGIN}/api/v1/health").json()
        dump("summary.json", {
            "health": health,
            "rules": status.get("rules_version"),
            "builder_cta": builder_cta,
            "proposal_flour": proposal.get("flour_name"),
            "proposal_prep": proposal.get("dough_name"),
            "proposal_shape": proposal.get("shape_name"),
            "tip_ok": tip.get("ok"),
            "tip_observation": str(tip.get("observation") or "")[:180],
            "reply": str(sandwich.get("reply") or "")[:280],
        })
        print(json.dumps({
            "rules": status.get("rules_version"),
            "cta": builder_cta.get("label"),
            "flour": proposal.get("flour_name"),
            "tip": tip.get("ok"),
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
