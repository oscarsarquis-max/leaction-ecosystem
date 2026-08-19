#!/usr/bin/env bash
# Mescla fragmento Phanton no docker-compose.yml e Caddyfile da EC2 (idempotente).
set -euo pipefail
cd /home/ubuntu

if [[ ! -f phanton-prod-secrets.env ]]; then
  echo "faltando phanton-prod-secrets.env" >&2
  exit 1
fi
if [[ ! -f docker-compose.phanton.fragment.yml ]]; then
  echo "faltando docker-compose.phanton.fragment.yml" >&2
  exit 1
fi
if [[ ! -f Caddyfile.phanton.fragment ]]; then
  echo "faltando Caddyfile.phanton.fragment" >&2
  exit 1
fi

python3 - <<'PY'
from pathlib import Path
import re

# --- load secrets ---
secrets = {}
for line in Path("phanton-prod-secrets.env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    secrets[k.strip()] = v.strip()

compose = Path("docker-compose.yml").read_text(encoding="utf-8")
# Prefer password efetiva do container MAtivas (YAML com # é ambíguo)
import subprocess

db_password = ""
try:
    db_password = subprocess.check_output(
        ["sudo", "docker", "exec", "mativas_prod_backend", "printenv", "DB_PASSWORD"],
        text=True,
    ).strip()
except Exception:
    pass
if not db_password:
    m = re.search(r"^\s*-\s*DB_PASSWORD=([^\s#]+)", compose, flags=re.M)
    if not m:
        raise SystemExit("Não foi possível obter DB_PASSWORD")
    db_password = m.group(1).strip().strip('"').strip("'")

frag = Path("docker-compose.phanton.fragment.yml").read_text(encoding="utf-8")
# Docker Compose interpolates $VAR — escape literal dollars
def esc_compose(val: str) -> str:
    return val.replace("\\", "\\\\").replace("$", "$$")

frag = (
    frag.replace("__DB_PASSWORD__", esc_compose(db_password))
    .replace("__GEMINI_API_KEY__", esc_compose(secrets.get("GEMINI_API_KEY", "")))
    .replace("__PHANTON_JWT_SECRET__", esc_compose(secrets.get("PHANTON_JWT_SECRET", "")))
)
if not secrets.get("GEMINI_API_KEY"):
    print("WARN: GEMINI_API_KEY vazio", flush=True)
if not secrets.get("PHANTON_JWT_SECRET"):
    raise SystemExit("PHANTON_JWT_SECRET obrigatório em phanton-prod-secrets.env")

# strip previous phanton block
compose = re.sub(r"\n# BEGIN PHANTON[\s\S]*?# END PHANTON\n?", "\n", compose)
compose = re.sub(
    r"\n  # --- PHANTON.*?phanton_frontend:.*?(?=\n  [a-zA-Z_]|\nvolumes:|\Z)",
    "\n",
    compose,
    flags=re.S,
)

# rstrip only — strip() removes the leading 2-space indent under services:
block = "\n# BEGIN PHANTON\n" + frag.rstrip() + "\n# END PHANTON\n"
if "\nvolumes:" in compose:
    compose = compose.replace("\nvolumes:", block + "\nvolumes:", 1)
else:
    compose = compose.rstrip() + "\n" + block

# Caddy depends_on — add phanton services once
if "phanton_backend" not in re.search(
    r"caddy:[\s\S]*?(?=\n  [a-z]|\Z)", compose
).group(0):
    compose = compose.replace(
        "    depends_on:\n      - frontend\n      - backend\n",
        "    depends_on:\n      - frontend\n      - backend\n"
        "      - phanton_frontend\n      - phanton_backend\n",
        1,
    )

Path("docker-compose.yml").write_text(compose.rstrip() + "\n", encoding="utf-8")
print("compose merged")

# Caddyfile
caddy = Path("Caddyfile").read_text(encoding="utf-8")
caddy = re.sub(r"\n# BEGIN PHANTON[\s\S]*?# END PHANTON\n?", "\n", caddy)
caddy_frag = Path("Caddyfile.phanton.fragment").read_text(encoding="utf-8")
Path("Caddyfile").write_text(
    caddy.rstrip()
    + "\n\n# BEGIN PHANTON\n"
    + caddy_frag.strip()
    + "\n# END PHANTON\n",
    encoding="utf-8",
)
print("caddy merged")
print("merge OK")
PY
