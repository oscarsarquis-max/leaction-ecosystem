#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
from pathlib import Path
env = {}
for line in Path('/var/www/leaction-platform/.env').read_text(encoding='utf-8', errors='replace').splitlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    key, value = line.split('=', 1)
    env[key.strip()] = value.strip().strip('"').strip("'")
print('mp_access_set', bool(env.get('MP_ACCESS_TOKEN')))
print('mp_public_set', bool(env.get('MP_PUBLIC_KEY') or env.get('MERCADOPAGO_PUBLIC_KEY')))
PY
