"""Extract Inove RDS connection from gitignored terraform.tfvars — do not print secrets."""
from __future__ import annotations

import re
from pathlib import Path

TF = Path(__file__).resolve().parents[1] / "terraform" / "terraform.tfvars"
OUT = Path(r"C:\Users\Usuario\AppData\Local\Temp\inove-rds.env")


def main() -> None:
    text = TF.read_text(encoding="utf-8", errors="replace")
    def grab(key: str) -> str:
        m = re.search(rf'{key}\s*=\s*"([^"]*)"', text)
        if not m:
            raise SystemExit(f"missing {key}")
        return m.group(1)

    host = grab("db_host")
    if not host:
        # dedicated RDS address is in comments/other keys; fallback known endpoint
        host = "inove4us-prod.czqyam2auctn.us-east-2.rds.amazonaws.com"
    lines = [
        f"DB_HOST={host}",
        f"DB_PORT={grab('db_port')}",
        f"DB_NAME={grab('db_name')}",
        f"DB_USER={grab('db_user')}",
        f"DB_PASS={grab('db_pass')}",
        "DB_SSLMODE=require",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} host_ok={bool(host)} user_ok={bool(grab('db_user'))}")


if __name__ == "__main__":
    main()
