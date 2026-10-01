#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform
eval "$(grep -E '^DATABASE_URL=' .env | tr -d '\r')"
BEFORE=$(psql "$DATABASE_URL" -tAc "select count(*) from public.orders")
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f /tmp/prm009-isolated-schema.sql >/tmp/prm009-schema.out
AFTER=$(psql "$DATABASE_URL" -tAc "select count(*) from public.orders")
ISOLATED=$(psql "$DATABASE_URL" -tAc "select count(*) from prm009_public_test.orders")
echo "public_before=$BEFORE public_after=$AFTER isolated=$ISOLATED"
install -m 644 /tmp/spider-pay-lookup.js services/gateway-api/domain/spider-pay-lookup.js
install -m 644 /tmp/spider-pay-lookup.test.js services/gateway-api/domain/spider-pay-lookup.test.js
python3 - <<'PY'
from pathlib import Path
p = Path("/var/www/leaction-platform/services/gateway-api/server.js")
t = p.read_text()
if "spider-pay-lookup" not in t:
    t = t.replace(
        "const { registerAmountCheckoutRoutes, parseHubPayload } = require('./domain/amount-checkout');",
        "const { registerAmountCheckoutRoutes, parseHubPayload } = require('./domain/amount-checkout');\nconst { registerSpiderPayLookupRoutes } = require('./domain/spider-pay-lookup');",
        1,
    )
    t = t.replace(
        "registerAmountCheckoutRoutes(app, pool);",
        "registerAmountCheckoutRoutes(app, pool);\nregisterSpiderPayLookupRoutes(app, pool);",
        1,
    )
    p.write_text(t)
print("server_has_lookup", "spider-pay-lookup" in p.read_text())
PY
python3 - <<'PY'
from pathlib import Path
p = Path("/var/www/leaction-platform/.env")
text = p.read_text()
wanted = {
  "ACTIONHUB_PAY_LOOKUP_ENABLED": "true",
  "ACTIONHUB_PAY_LOOKUP_ISOLATED": "true",
  "ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST": "false",
}
changed = False
lines = text.splitlines()
keys = {}
for i, line in enumerate(lines):
    if "=" in line and not line.strip().startswith("#"):
        keys[line.split("=", 1)[0]] = i
for k, v in wanted.items():
    if k in keys:
        if lines[keys[k]] != f"{k}={v}":
            lines[keys[k]] = f"{k}={v}"
            changed = True
    else:
        lines.append(f"{k}={v}")
        changed = True
if changed:
    p.write_text("\n".join(lines) + "\n")
print("flags_updated", changed)
print("provider_secret_present", any(
    l.startswith("ACTIONHUB_PAY_PROVIDER_SECRET=") and len(l.split("=", 1)[1].strip()) > 0
    for l in lines
))
print("pay_environment", next(
    ("set" for l in lines if l.startswith("ACTIONHUB_PAY_ENVIRONMENT=")),
    "absent",
))
PY
pm2 restart gateway-api --update-env
sleep 2
pm2 jlist | python3 -c "import json,sys; apps=json.load(sys.stdin); g=[a for a in apps if a.get('name')=='gateway-api'][0]; print('gateway_status='+g['pm2_env']['status']); print('gateway_restarts='+str(g['pm2_env']['restart_time']))"
curl -s -o /tmp/pay404.txt -w "lookup_no_key=%{http_code}\n" http://127.0.0.1:4001/v1/integration/payments
curl -s -o /dev/null -w "hub_health=%{http_code}\n" http://127.0.0.1:4001/health || true
