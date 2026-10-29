"""Extrai BUILD_ID e bundle da Loja sem dados pessoais."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "95b-verify"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def main() -> None:
    hub = get("https://actionhub.com.br/loja")
    loja = get("https://lojadepaes.com.br/")
    m = re.search(r'"buildId":"([^"]+)"', hub)
    m2 = re.search(r"/_next/static/([A-Za-z0-9_-]+)/", hub)
    report = {
        "hub_build_id": m.group(1) if m else None,
        "hub_static_id": m2.group(1) if m2 else None,
        "hub_next": re.findall(r"/_next/static/[^\"']+", hub)[:8],
        "loja_assets": re.findall(r"/assets/[^\"']+", loja)[:8],
    }
    (OUT / "read-build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
