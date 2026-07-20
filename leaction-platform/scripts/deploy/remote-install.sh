#!/usr/bin/env bash
# Executado NO servidor EC2 (Ubuntu) — instala/atualiza Action Hub
set -euo pipefail

APP_ROOT="${APP_ROOT:-/var/www/leaction-platform}"
cd "$APP_ROOT"

echo "==> Action Hub — install/update em $APP_ROOT"

mkdir -p logs

if [[ ! -f .env ]]; then
  echo "ERRO: $APP_ROOT/.env ausente. Copie .env.production.example antes do deploy."
  exit 1
fi

# Versão de release (VERSION + SHA do checkout)
if [[ -f VERSION ]]; then
  export APP_VERSION="$(tr -d '[:space:]' < VERSION)"
  echo "==> APP_VERSION=$APP_VERSION"
fi
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || true)"
  if [[ -n "${GIT_SHA:-}" ]]; then
    export GIT_SHA
    printf '%s\n' "$GIT_SHA" > GIT_SHA
    echo "==> GIT_SHA=$GIT_SHA"
  fi
fi

echo "==> gateway-api — dependencias"
cd services/gateway-api
npm ci --omit=dev --no-audit --no-fund
cd "$APP_ROOT"

echo "==> action-hub — dependencias + build"
cd frontend/action-hub
if [[ ! -f .env.production ]]; then
  echo "ERRO: frontend/action-hub/.env.production ausente."
  exit 1
fi
npm ci --no-audit --no-fund
npm run build
cd "$APP_ROOT"

echo "==> marketplace-api — dependencias Python"
cd backend
sudo mkdir -p /var/lib/leaction-platform
sudo chown "$(whoami):$(whoami)" /var/lib/leaction-platform 2>/dev/null || true
chmod 700 /var/lib/leaction-platform 2>/dev/null || true
if [[ ! -f .venv/bin/activate ]]; then
  rm -rf .venv
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd "$APP_ROOT"

echo "==> PM2"
if pm2 describe action-hub >/dev/null 2>&1; then
  pm2 restart ecosystem.config.js --update-env
else
  pm2 start ecosystem.config.js
fi
pm2 save

echo "==> Nginx"
if [[ -f nginx.conf ]]; then
  sudo cp nginx.conf /etc/nginx/sites-available/action-hub
  # Mantém o site SSL do Certbot (actionhub) quando já configurado
  if [[ ! -L /etc/nginx/sites-enabled/actionhub ]]; then
    sudo ln -sf /etc/nginx/sites-available/action-hub /etc/nginx/sites-enabled/action-hub
  else
    sudo rm -f /etc/nginx/sites-enabled/action-hub
  fi
  sudo rm -f /etc/nginx/sites-enabled/default
  sudo nginx -t
  sudo systemctl reload nginx
fi

echo "==> Health local"
sleep 3
curl -sf -o /dev/null -w "gateway /health HTTP %{http_code}\n" "http://127.0.0.1:4001/health" \
  || echo "[!] gateway sem resposta"
curl -sS "http://127.0.0.1:4001/health" 2>/dev/null | head -c 300 || true
echo
curl -sf -o /dev/null -w "marketplace HTTP %{http_code}\n" "http://127.0.0.1:4012/api/marketplace/health" || echo "[!] marketplace sem resposta"
curl -sf -o /dev/null -w "action-hub /api/health HTTP %{http_code}\n" "http://127.0.0.1:4000/api/health" \
  || curl -sf -o /dev/null -w "action-hub / HTTP %{http_code}\n" "http://127.0.0.1:4000/" || true
curl -sS "http://127.0.0.1:4000/api/health" 2>/dev/null | head -c 300 || true
echo

pm2 status
echo "==> Concluido."
