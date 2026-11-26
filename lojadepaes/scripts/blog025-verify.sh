#!/usr/bin/env bash
set -euo pipefail
KEY="${BLOG025_KEY:?}"
docker commit infra-api-1 lojadepaes:prod-blog025-20261126b >/dev/null
sudo sed -i 's|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=lojadepaes:prod-blog025-20261126b|' /opt/lojadepaes/app/infra/.env || true
curl -s -o /tmp/v.json -w "vitrine=%{http_code}\n" -H "X-Service-Key: $KEY" https://lojadepaes.com.br/api/v1/integracoes/vitrine
python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("/tmp/v.json").read_text() or "null")
print("VITRINE", type(d).__name__, len(d) if isinstance(d, list) else d)
if isinstance(d, list) and d:
    print("SAMPLE_KEYS", sorted(d[0].keys()))
PY
curl -s -o /dev/null -w "no_key=%{http_code}\n" https://lojadepaes.com.br/api/v1/integracoes/vitrine
docker exec infra-api-1 test -f /app/backend/app/api/v1/integracoes.py
docker exec infra-api-1 test -f /app/backend/app/domain/integracoes_lepain.py
echo FILES_OK
curl -s -o /dev/null -w "loja=%{http_code}\n" https://lojadepaes.com.br/api/v1/health
curl -s -o /dev/null -w "gestao=%{http_code}\n" https://gestao.lojadepaes.com.br/
curl -s -o /dev/null -w "lepain=%{http_code}\n" https://lepain.lojadepaes.com.br/api/v1/health
echo BLOG025_LOJA_VERIFY_OK
