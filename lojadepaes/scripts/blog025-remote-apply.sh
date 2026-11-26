#!/usr/bin/env bash
# BLOG-025 — overlay no container vivo, commit imagem, recreate só api + alembic.
set -euo pipefail

KEY="${BLOG025_KEY:?BLOG025_KEY required}"
TAG="${BLOG025_TAG:-prod-blog025-$(date -u +%Y%m%d%H%M)}"
INFRA=/opt/lojadepaes/app/infra
STAGE=/tmp/blog025-loja
API=infra-api-1

docker cp "$STAGE/api/integracoes.py" "$API:/app/backend/app/api/v1/integracoes.py"
docker cp "$STAGE/api/__init__.py" "$API:/app/backend/app/api/v1/__init__.py"
docker cp "$STAGE/domain/integracoes_lepain.py" "$API:/app/backend/app/domain/integracoes_lepain.py"
docker cp "$STAGE/domain/house_fidelity_ledger.py" "$API:/app/backend/app/domain/house_fidelity_ledger.py"
docker cp "$STAGE/domain/config.py" "$API:/app/backend/app/core/config.py"
docker cp "$STAGE/migrations/a8c1d9e24f70_blog025_fidelity_integracao_ref.py" \
  "$API:/app/database/migrations/versions/a8c1d9e24f70_blog025_fidelity_integracao_ref.py"

export BLOG025_KEY="$KEY"
sudo -E python3 - <<'PY'
from pathlib import Path
import os, re
path = Path("/opt/lojadepaes/secrets/app.env")
key = os.environ["BLOG025_KEY"]
text = path.read_text()
line = f"LOJADEPAES_INTEGRACOES_SERVICE_KEY={key}"
if re.search(r"^LOJADEPAES_INTEGRACOES_SERVICE_KEY=.*$", text, re.M):
    text = re.sub(r"^LOJADEPAES_INTEGRACOES_SERVICE_KEY=.*$", line, text, flags=re.M)
else:
    if not text.endswith("\n"):
        text += "\n"
    text += line + "\n"
path.write_text(text)
print("ENV_KEY_UPSERT_OK")
PY

docker commit "$API" "lojadepaes:$TAG"
echo "IMAGE=lojadepaes:$TAG"

if grep -q '^LOJADEPAES_API_IMAGE=' "$INFRA/.env"; then
  sudo sed -i "s|^LOJADEPAES_API_IMAGE=.*|LOJADEPAES_API_IMAGE=lojadepaes:$TAG|" "$INFRA/.env"
else
  printf '\nLOJADEPAES_API_IMAGE=lojadepaes:%s\n' "$TAG" | sudo tee -a "$INFRA/.env" >/dev/null
fi

MONITOR=/tmp/blog025-loja-health.txt
: > "$MONITOR"
(
  for i in $(seq 1 90); do
    ts=$(date -Is)
    loja=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 https://lojadepaes.com.br/api/v1/health || echo 000)
    gestao=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 https://gestao.lojadepaes.com.br/ || echo 000)
    lepain=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 https://lepain.lojadepaes.com.br/api/v1/health || echo 000)
    echo "$ts loja=$loja gestao=$gestao lepain=$lepain" >> "$MONITOR"
    sleep 2
  done
) &
MON=$!

cd "$INFRA"
sudo docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate --no-deps api

ok=0
for _ in $(seq 1 45); do
  if sudo docker compose -f docker-compose.prod.yml --env-file .env exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/dev/null; then
    ok=1
    break
  fi
  sleep 2
done

sudo docker compose -f docker-compose.prod.yml --env-file .env exec -T -w /app/database api alembic upgrade head
sudo docker compose -f docker-compose.prod.yml --env-file .env exec -T -w /app/database api alembic current

kill "$MON" 2>/dev/null || true
wait "$MON" 2>/dev/null || true
echo "HEALTH_TAIL=$(tail -n 3 "$MONITOR" | tr '\n' ';')"
bad=$(grep -E 'loja=(000|5..)|gestao=(000|5..)|lepain=(000|5..)' "$MONITOR" || true)
echo "HEALTH_NON_200_LINES=$(printf '%s\n' "$bad" | grep -c . || true)"

CODE=$(curl -s -o /tmp/blog025-vitrine.json -w '%{http_code}' -H "X-Service-Key: $KEY" \
  https://lojadepaes.com.br/api/v1/integracoes/vitrine || echo 000)
echo "VITRINE_HTTP=$CODE"
python3 - <<'PY'
import json
from pathlib import Path
raw = Path("/tmp/blog025-vitrine.json").read_text() or "null"
data = json.loads(raw)
print("VITRINE_TYPE", type(data).__name__, "LEN", len(data) if isinstance(data, list) else "n/a")
PY

if [ "$ok" != "1" ]; then
  echo API_HEALTH_FAIL
  exit 1
fi
echo BLOG025_LOJA_OK
