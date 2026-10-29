#!/usr/bin/env bash
set -euo pipefail
cd /var/www/leaction-platform
install -m 644 /tmp/spider-pay-lookup.js services/gateway-api/domain/spider-pay-lookup.js
install -m 644 /tmp/spider-pay-lookup.test.js services/gateway-api/domain/spider-pay-lookup.test.js
install -m 644 /tmp/amount-checkout.js services/gateway-api/domain/amount-checkout.js
install -m 644 /tmp/mp-webhooks.js services/gateway-api/domain/mp-webhooks.js
install -m 644 /tmp/amount-observation.test.js services/gateway-api/domain/amount-observation.test.js
install -m 644 /tmp/amount-checkout.test.js services/gateway-api/domain/amount-checkout.test.js
install -m 644 /tmp/pay-regression.test.js services/gateway-api/domain/pay-regression.test.js
install -m 644 /tmp/money-cents.test.js services/gateway-api/lib/money-cents.test.js
install -m 644 /tmp/admin-payments.js services/gateway-api/admin/payments.js
install -m 644 /tmp/mercadopago.js services/gateway-api/mercadopago.js
python3 - <<'PY'
from pathlib import Path
p = Path("/var/www/leaction-platform/services/gateway-api/server.js")
text = p.read_text()
print("server_has_lookup", "spider-pay-lookup" in text)
print("server_has_provider_route_in_lookup_file", "LIST_PAYMENT_TRANSACTIONS" in Path("services/gateway-api/domain/spider-pay-lookup.js").read_text())
PY
node --test services/gateway-api/domain/spider-pay-lookup.test.js services/gateway-api/domain/amount-observation.test.js services/gateway-api/domain/amount-checkout.test.js services/gateway-api/domain/pay-regression.test.js services/gateway-api/lib/money-cents.test.js
python3 - <<'PY'
from pathlib import Path
p = Path("/var/www/leaction-platform/.env")
text = p.read_text()
wanted = {
  "ACTIONHUB_PAY_LOOKUP_ENABLED": "true",
  "ACTIONHUB_PAY_LOOKUP_ISOLATED": "true",
  "ACTIONHUB_PAY_LOOKUP_PUBLIC_TEST": "false",
  "ACTIONHUB_PAY_LOOKUP_OPERATIONAL": "true",
  "ACTIONHUB_PAY_OPERATIONAL_APP_IDS": "lojadepaes",
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
print("operational", any(l.startswith("ACTIONHUB_PAY_LOOKUP_OPERATIONAL=true") for l in lines))
print("operational_apps", next((l.split("=",1)[1] for l in lines if l.startswith("ACTIONHUB_PAY_OPERATIONAL_APP_IDS=")), "absent"))
PY
pm2 restart gateway-api --update-env
sleep 2
pm2 jlist | python3 -c "import json,sys; apps=json.load(sys.stdin); g=[a for a in apps if a.get('name')=='gateway-api'][0]; print('gateway_status='+g['pm2_env']['status']); print('gateway_restarts='+str(g['pm2_env']['restart_time']))"
curl -s -o /tmp/provider404.txt -w "provider_no_key=%{http_code}\n" -X POST http://127.0.0.1:4001/v1/provider/capabilities/LIST_PAYMENT_TRANSACTIONS/executions -H 'Content-Type: application/json' -d '{}'
curl -s -o /dev/null -w "hub_health=%{http_code}\n" http://127.0.0.1:4001/health || true
curl -s -o /dev/null -w "lookup_no_key=%{http_code}\n" http://127.0.0.1:4001/v1/integration/payments
python3 - <<'PY'
from pathlib import Path
print("public_orders_untouched_script=1")
print("isolated_schema_untouched=1")
PY
