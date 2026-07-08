#!/bin/bash
set -euo pipefail

APP_ROOT="/opt/chamelleon"
HOTPAGE_ROOT="${APP_ROOT}/hotpages/diario-obra"
API_ROOT="${APP_ROOT}/hotpages/diario-obra-api"
NGINX_SITE="/etc/nginx/sites-available/chamelleon"
CHAM_ENV="${APP_ROOT}/backend/.env"

echo "==> Diario de Obra — deploy hotpage (aditivo, sem apagar dados)"

sudo mkdir -p "${HOTPAGE_ROOT}" "${API_ROOT}"
sudo chown -R ubuntu:ubuntu "${APP_ROOT}/hotpages"

# .env derivado do PostgreSQL do Chamelleon (mesmo host/user, base dedicada)
if [ -f "${CHAM_ENV}" ]; then
  CHAM_DATABASE_URL="$(grep '^DATABASE_URL=' "${CHAM_ENV}" | cut -d= -f2- | tr -d '"' | tr -d "'")"
  DATABASE_URL="$(python3 -c "import sys; from urllib.parse import urlparse, urlunparse; u=urlparse(sys.argv[1]); print(urlunparse(u._replace(path='/diario-obra')))" "${CHAM_DATABASE_URL}")"
else
  DATABASE_URL="postgresql://admin:password123@127.0.0.1:5432/diario-obra"
fi

# Preserva .env existente (não sobrescreve API keys / DATABASE_URL / webhooks de produção)
if [ -f "${API_ROOT}/.env" ]; then
  echo "Mantendo .env existente (compatibilidade)"
else
  cat > "${API_ROOT}/.env" <<EOF
PORT=6010
FLASK_DEBUG=0
DATABASE_URL=${DATABASE_URL}
INTEGRATION_API_KEY=change-me-diario-obra-integration-key
CORS_ORIGINS=https://chamelleon.com.br,https://www.chamelleon.com.br
CHAMELLEON_WEBHOOK_URL=https://chamelleon.com.br/api/webhooks/gemba/rdo
EOF
  chmod 600 "${API_ROOT}/.env"
fi

# Cria base dedicada apenas se não existir (nunca DROP)
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='diario-obra'" | grep -q 1; then
  sudo -u postgres psql -c 'CREATE DATABASE "diario-obra" OWNER chamelleon;'
  echo "Base diario-obra criada"
fi

# API
cd "${API_ROOT}"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
. .venv/bin/activate
pip install -q -U pip
pip install -q -r requirements.txt gunicorn

export PYTHONPATH="${API_ROOT}"
set -a
# shellcheck disable=SC1091
source "${API_ROOT}/.env"
set +a

# Schema aditivo: create_all + ADD COLUMN — nunca DROP/TRUNCATE/seed
python -c "
from app import create_app
from app.db_migrate import ensure_rdo_schema
app = create_app()
with app.app_context():
    ensure_rdo_schema()
    print('Schema OK (aditivo)')
"

# systemd
sudo cp /tmp/diario-obra-api.service /etc/systemd/system/diario-obra-api.service
sudo systemctl daemon-reload
sudo systemctl enable diario-obra-api
sudo systemctl restart diario-obra-api

# nginx — injeta blocos se ainda nao existirem
if ! grep -q 'location /diario-obra/api/' "${NGINX_SITE}"; then
  sudo cp "${NGINX_SITE}" "${NGINX_SITE}.diario-obra.bak"
  sudo python3 <<'PY'
from pathlib import Path
site = Path("/etc/nginx/sites-available/chamelleon")
snippet = Path("/tmp/nginx-diario-obra-snippet.conf")
text = site.read_text()
marker = "    location /api/ {"
insert = snippet.read_text().rstrip() + "\n\n"
if marker not in text:
    raise SystemExit("nginx: bloco /api/ nao encontrado")
text = text.replace(marker, insert + marker, 1)
site.write_text(text)
print("nginx: blocos /diario-obra/ adicionados")
PY
fi

sudo nginx -t
sudo systemctl reload nginx

echo "==> Hotpage ativa em https://chamelleon.com.br/diario-obra/"
