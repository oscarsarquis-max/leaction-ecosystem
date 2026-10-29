#!/usr/bin/env bash
set -euo pipefail
# Prompt 75 — publica imagem i com flags de complemento desligadas.
# Nao copia .env local. Nao altera pagamento, Gigio existente nem segredos.

INFRA=/opt/lojadepaes/app/infra
COMPOSE="$INFRA/docker-compose.prod.yml"
APPENV=/opt/lojadepaes/secrets/app.env
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

echo "start $STAMP"
cd "$INFRA"

# Backup verificado do Postgres de producao.
sudo bash "$INFRA/loja-backup-now.sh" || sudo bash "$INFRA/backup-pg.sh"
echo "backup_done"

# Carrega imagem nova (nao e a h).
sudo docker load -i /tmp/loja-prod-20261006i.tar
sudo docker image inspect lojadepaes:prod-20261006i >/dev/null
echo "image_loaded prod-20261006i"

# So chaves novas, se ainda nao existirem.
ensure_key() {
  local key="$1" value="$2"
  if sudo grep -q "^${key}=" "$APPENV"; then
    echo "keep $key"
  else
    echo "${key}=${value}" | sudo tee -a "$APPENV" >/dev/null
    echo "append $key"
  fi
}
ensure_key LOJADEPAES_PUBLIC_ACCOMPANIMENTS_ENABLED false
ensure_key LOJADEPAES_GIGIO_ACCOMPANIMENTS_ENABLED false
ensure_key LOJADEPAES_ACCOMPANIMENTS_PREVIEW false
ensure_key LOJADEPAES_ACTIONHUB_MARKETPLACE_URL https://actionhub.com.br/marketplace-api
ensure_key LOJADEPAES_ACTIONHUB_MARKETPLACE_TIMEOUT_SECONDS 2

# Troca so a tag da imagem no .env do compose.
if grep -q "^LOJADEPAES_API_IMAGE=" "$INFRA/.env"; then
  sed -i 's/^LOJADEPAES_API_IMAGE=.*/LOJADEPAES_API_IMAGE=lojadepaes:prod-20261006i/' "$INFRA/.env"
else
  echo "LOJADEPAES_API_IMAGE=lojadepaes:prod-20261006i" >> "$INFRA/.env"
fi
grep "^LOJADEPAES_API_IMAGE=" "$INFRA/.env"

sudo docker compose -f "$COMPOSE" up -d api
echo "compose_up"

# Espera health do container.
for i in 1 2 3 4 5 6 7 8 9 10; do
  if sudo docker compose -f "$COMPOSE" exec -T api curl -fsS http://127.0.0.1:8080/api/v1/health >/tmp/p75-loja-health.json; then
    echo "api_health_ok try=$i"
    break
  fi
  sleep 4
  if [ "$i" -eq 10 ]; then
    echo "api_health_fail" >&2
    sudo docker compose -f "$COMPOSE" logs --tail 80 api
    exit 1
  fi
done

sudo docker compose -f "$COMPOSE" exec -T -w /app/database api alembic upgrade head
sudo docker compose -f "$COMPOSE" exec -T -w /app/database api alembic current
echo "alembic_done"

# Flags efetivas, sem segredos.
sudo docker compose -f "$COMPOSE" exec -T api python - <<'PY'
from app.core.config import get_settings
s = get_settings()
print("env", s.env)
print("public_acc", s.public_accompaniments_enabled)
print("gigio_acc", s.gigio_accompaniments_enabled)
print("preview", s.accompaniments_preview)
print("gigio", s.gigio_enabled)
print("mkt_set", bool((s.actionhub_marketplace_url or "").strip()))
print("mkt_host", (s.actionhub_marketplace_url or "").split("/")[2] if "://" in (s.actionhub_marketplace_url or "") else "")
print("app_id", s.actionhub_app_id)
print("payments", s.public_payments_enabled)
print("orders", s.public_orders_enabled)
PY

curl -fsS --max-time 10 https://lojadepaes.com.br/api/v1/health
echo
echo "loja_done $STAMP"
