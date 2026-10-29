"""Scan live frontend for Prompt 87 strings. No order."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ORIGIN = "https://lojadepaes.com.br"
OUT = Path(__file__).resolve().parents[1] / "readme" / "evidence" / "prompt-87" / "prod"
OUT.mkdir(parents=True, exist_ok=True)

NEEDLES = [
    "Uma dica do Gigio para o seu pão",
    "Montar esse pão",
    "Aplicar sugestão",
    "Conversar com o Gigio",
    "Pedir nova dica",
    "Sugestão do Gigio",
    "Continuar com seu pão",
    "builder-tip",
    "proposta=",
]


def main() -> None:
    html = urllib.request.urlopen(f"{ORIGIN}/", timeout=30).read().decode("utf-8", "replace")
    (OUT / "home.html").write_text(html, encoding="utf-8")
    assets = re.findall(r"/assets/[^\"']+", html)
    js = [item for item in assets if item.endswith(".js")]
    css = [item for item in assets if item.endswith(".css")]
    found: dict[str, bool] = {}
    js_name = js[0] if js else ""
    size = 0
    if js_name:
        data = urllib.request.urlopen(f"{ORIGIN}{js_name}", timeout=60).read().decode("utf-8", "replace")
        size = len(data)
        for needle in NEEDLES:
            found[needle] = needle in data
        (OUT / "bundle-scan.txt").write_text(
            "\n".join([f"file: {js_name}", f"css: {','.join(css)}", f"size: {size}"] + [f"{k}: {v}" for k, v in found.items()])
            + "\n",
            encoding="utf-8",
        )
    print({"js": js_name, "css": css, "found": found})


if __name__ == "__main__":
    main()
