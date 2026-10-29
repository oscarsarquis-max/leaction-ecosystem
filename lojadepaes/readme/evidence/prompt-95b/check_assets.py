"""Leitura HTTP sanitizada: BUILD_ID, logo e flags de sandbox. Sem credenciais."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent


def get(url: str) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "95b-verify"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.status, response.getheader("content-type") or "", response.read()


def main() -> None:
    report: dict = {}
    status, _, html_bytes = get("https://actionhub.com.br/loja")
    html = html_bytes.decode("utf-8", "replace")
    build = re.search(r'"buildId":"([^"]+)"', html)
    report["loja_html"] = {
        "status": status,
        "build_id": build.group(1) if build else None,
        "bytes": len(html),
        "has_pedido_fornada": "Pedido da fornada" in html,
        "has_planos_biblioteca": "Planos da Biblioteca" in html,
    }
    status, content_type, png = get("https://actionhub.com.br/brands/lojadepaes.png")
    report["logo"] = {"status": status, "content_type": content_type, "bytes": len(png)}
    try:
        status, _, cfg = get("https://actionhub.com.br/hub-api/config/payments")
        data = json.loads(cfg.decode("utf-8", "replace"))
        report["payments_flags"] = {
            "status": status,
            "sandbox_mode": data.get("sandbox_mode"),
            "allow_payment_simulation": data.get("allow_payment_simulation"),
            "keys": sorted(k for k in data if not any(x in k.lower() for x in ("key", "token", "secret", "public"))),
        }
    except Exception as exc:
        report["payments_flags"] = {"error": type(exc).__name__}
    (OUT / "check-assets.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
