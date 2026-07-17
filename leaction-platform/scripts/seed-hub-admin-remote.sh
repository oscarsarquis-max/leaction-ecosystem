#!/usr/bin/env bash
# Roda no EC2 (tem acesso RDS). Usa /var/www/leaction-platform/.env
set -euo pipefail
APP_ROOT="${APP_ROOT:-/var/www/leaction-platform}"
cd "$APP_ROOT"
set -a
# shellcheck disable=SC1091
source .env
set +a
# pg / deps do gateway
export NODE_PATH="$APP_ROOT/services/gateway-api/node_modules${NODE_PATH:+:$NODE_PATH}"
node "$APP_ROOT/scripts/seed-hub-admin.js"
