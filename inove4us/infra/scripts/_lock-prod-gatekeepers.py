"""Lock Inove/Hub gatekeepers using local PRODUCTION_MASTER_KEY. Never prints the secret."""
from __future__ import annotations

import ssl
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_key(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("PRODUCTION_MASTER_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def get(url: str) -> tuple[int, str]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "lancamento-lock/1"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body[:300]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body[:300]


def main() -> None:
    key = read_key(ROOT / ".env") or read_key(ROOT.parent / "leaction-platform" / ".env")
    if not key:
        raise SystemExit("PRODUCTION_MASTER_KEY ausente no .env local")
    q = urllib.parse.urlencode({"secret": key})
    for label, url in [
        ("inove_lock", f"https://inove4us.com.br/gatekeeper/lock?{q}"),
        ("inove_status", "https://inove4us.com.br/gatekeeper/status"),
        ("hub_lock", f"https://actionhub.com.br/hub-api/gatekeeper/lock?{q}"),
        ("hub_status", "https://actionhub.com.br/hub-api/gatekeeper/status"),
    ]:
        code, body = get(url)
        print(f"{label} {code} {body.replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
