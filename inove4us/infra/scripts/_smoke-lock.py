"""Smoke mínimo pós-trava: health + bypass School sem imprimir o secret."""
from __future__ import annotations

import ssl
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_key() -> str:
    for path in (ROOT / ".env", ROOT.parent / "leaction-platform" / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRODUCTION_MASTER_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def fetch(url: str, follow: bool = False) -> tuple[int, str, str]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "lancamento-smoke/1"})
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPRedirectHandler() if follow else urllib.request.HTTPHandler(),
    )
    if not follow:
        class NoRedir(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
                return None

        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx),
            NoRedir(),
        )
    try:
        with opener.open(req, timeout=20) as resp:
            loc = resp.headers.get("Location") or ""
            return resp.status, loc, resp.read()[:80].decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        loc = exc.headers.get("Location") or ""
        return exc.code, loc, exc.read()[:80].decode("utf-8", "replace")


def main() -> None:
    key = read_key()
    if not key:
        raise SystemExit("PRODUCTION_MASTER_KEY ausente")
    q = urllib.parse.urlencode({"secret": key})
    for label, url, follow in [
        ("school_health", "https://school.inove4us.com.br/api/health", True),
        ("school_bypass", f"https://school.inove4us.com.br/gatekeeper/bypass?{q}", False),
        ("school_gk_status", "https://school.inove4us.com.br/gatekeeper/status", True),
    ]:
        code, loc, body = fetch(url, follow=follow)
        print(f"{label} {code} loc={loc} body={body.replace(chr(10), ' ')[:120]}")


if __name__ == "__main__":
    main()
