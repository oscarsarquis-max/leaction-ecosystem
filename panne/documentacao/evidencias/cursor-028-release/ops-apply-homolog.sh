#!/bin/bash
set -euo pipefail
cd /var/www/leaction-platform
set -a; . ./.env; set +a
export NODE_PATH=/var/www/leaction-platform/services/gateway-api/node_modules
node scripts/apply-cms-site-json.js --file=/tmp/cms-panne-demo-homolog.json
echo APPLY_HOMOLOG_OK
curl -fsS 'https://api.actionhub.com.br/api/public/cms?config_key=panne-demo' | python3 -c 'import sys,json; d=json.load(sys.stdin); lp=d["landing_page_data"]; print("title", lp.get("coluna1",{}).get("title")); print("img", (lp.get("coluna1",{}).get("image_url") or "")[:100]); print("right", ((lp.get("columns") or [{},{}])[1].get("description") or "")[:80]); print("updated", d.get("updated_at"))'
