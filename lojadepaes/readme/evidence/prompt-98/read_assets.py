"""Cabeçalhos públicos do HTML e da vitrine. Sem autenticação."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

OUT = Path(__file__).resolve().parent
URLS = (
    "https://lojadepaes.com.br/",
    "https://lojadepaes.com.br/images/vitrine%20da%20loja.png",
    "https://lojadepaes.com.br/images/lojadepaeslogo.png",
)


def headish(url: str) -> dict:
    req = Request(url, method="GET", headers={"User-Agent": "loja-prompt-98"})
    with urlopen(req, timeout=30) as resp:
        body = resp.read(64) if "images/" in url else resp.read(2048)
        return {
            "url": url,
            "status": resp.status,
            "content_type": resp.headers.get("Content-Type"),
            "length": resp.headers.get("Content-Length"),
            "cache": resp.headers.get("Cache-Control"),
            "sniff": body[:16].hex() if "images/" in url else body.decode("utf-8", "replace")[:180],
        }


def main() -> None:
    report = {"assets": [headish(url) for url in URLS]}
    (OUT / "prod-assets.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote prod-assets.json")


if __name__ == "__main__":
    main()
