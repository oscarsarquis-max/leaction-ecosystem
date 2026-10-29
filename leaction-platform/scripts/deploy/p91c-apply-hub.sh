#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform

echo '=== 91C backup ==='
if [ -f /tmp/p91c-backup-dbs.sh ]; then
  sed -i 's/\r$//' /tmp/p91c-backup-dbs.sh
  bash /tmp/p91c-backup-dbs.sh
elif [ -f scripts/deploy/_prod-backup-dbs.sh ]; then
  bash scripts/deploy/_prod-backup-dbs.sh
else
  echo 'backup_script_missing'
  exit 1
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK=/var/lib/leaction-platform/backups/p91c-$STAMP
mkdir -p "$BK"
cp -a services/gateway-api/domain/contract-service.js "$BK/contract-service.js"
cp -a services/gateway-api/domain/entitlements-api.js "$BK/entitlements-api.js"
cp -a services/gateway-api/server.js "$BK/server.js"
echo "rollback_files $BK"

install -m 644 /tmp/p91c-credits-ops.js services/gateway-api/domain/credits-ops.js
install -m 644 /tmp/p91c-credits-ops.test.js services/gateway-api/domain/credits-ops.test.js
install -m 644 /tmp/p91c-credits-api.js services/gateway-api/domain/credits-api.js
install -m 644 /tmp/p91c-entitlements-api.js services/gateway-api/domain/entitlements-api.js
install -m 644 /tmp/p91c-contract-service.js services/gateway-api/domain/contract-service.js

python3 - <<'PY'
from pathlib import Path
p = Path('/var/www/leaction-platform/services/gateway-api/server.js')
text = p.read_text()
changed = False
if "registerCreditsRoutes" not in text:
    if "const { registerEntitlementsRoutes } = require('./domain/entitlements-api');" in text:
        text = text.replace(
            "const { registerEntitlementsRoutes } = require('./domain/entitlements-api');",
            "const { registerEntitlementsRoutes } = require('./domain/entitlements-api');\n"
            "const { registerCreditsRoutes } = require('./domain/credits-api');",
        )
        changed = True
    if "registerEntitlementsRoutes(app, pool);" in text and "registerCreditsRoutes(app, pool);" not in text:
        text = text.replace(
            "registerEntitlementsRoutes(app, pool);",
            "registerEntitlementsRoutes(app, pool);\nregisterCreditsRoutes(app, pool);",
        )
        changed = True
    if changed:
        p.write_text(text)
print('server_has_credits', 'registerCreditsRoutes' in p.read_text())
print('ops_has_buckets', 'principal_credits' in Path('services/gateway-api/domain/credits-ops.js').read_text())
print('contract_passes_endsAt', 'mergeEntitlement(prevObj, items, hubPayload, endsAt)' in Path('services/gateway-api/domain/contract-service.js').read_text())
PY

node --test services/gateway-api/domain/credits-ops.test.js

pm2 restart gateway-api --update-env
sleep 3
pm2 jlist | python3 -c "import json,sys; apps=json.load(sys.stdin); g=[a for a in apps if a.get('name')=='gateway-api'][0]; print('gateway_status='+g['pm2_env']['status']); print('gateway_restarts='+str(g['pm2_env']['restart_time']))"
curl -s -o /dev/null -w "hub_health=%{http_code}\n" http://127.0.0.1:4001/health || true
curl -s -o /tmp/p91c-credits.json -w "credits_no_auth=%{http_code}\n" -X POST http://127.0.0.1:4001/v1/credits/reserve -H 'Content-Type: application/json' -d '{}'
curl -s -o /tmp/p91c-catalog.json -w "catalog_loja=%{http_code}\n" http://127.0.0.1:4001/v1/catalog/lojadepaes
python3 - <<'PY'
import json
from pathlib import Path
body = Path('/tmp/p91c-credits.json').read_text(encoding='utf-8', errors='replace')
print('credits_body', body[:240])
cat = json.loads(Path('/tmp/p91c-catalog.json').read_text(encoding='utf-8', errors='replace'))
print('catalog_plans', len(cat.get('plans') or []))
PY
bash /tmp/p91c-upsert-prod-plans.sh
