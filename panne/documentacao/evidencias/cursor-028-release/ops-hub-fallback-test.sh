#!/bin/bash
set -euo pipefail
# Controlled brief Hub gateway outage for Panne editorial fallback check.
# Does NOT touch Panne services. Restores gateway immediately.

echo "==> pre health"
curl -fsS -o /dev/null -w "gw_pre:%{http_code}\n" http://127.0.0.1:4001/health || true

echo "==> stop gateway briefly"
pm2 stop gateway-api
sleep 2
curl -s -o /dev/null -w "gw_down:%{http_code}\n" http://127.0.0.1:4001/health || echo "gw_down:unreachable"

echo "==> panne editorial while hub down (from this host)"
# Call public demo API from EC2 if network allows; else note skip
curl -sS -m 20 -o /tmp/ed-fallback.json -w "panne_ed:%{http_code}\n" \
  https://api.demo.panne.ia.br/api/v1/public/login-editorial || echo "panne_ed:fail"
python3 - <<'PY'
import json
try:
  d=json.load(open('/tmp/ed-fallback.json'))
  print('fallback_source', d.get('source'))
  print('fallback_cols', len(d.get('columns') or []))
  print('fallback_has_titles', [c.get('title','')[:40] for c in (d.get('columns') or [])])
except Exception as e:
  print('fallback_parse_error', type(e).__name__)
PY

echo "==> start gateway"
pm2 start gateway-api --update-env || pm2 restart gateway-api --update-env
sleep 3
curl -fsS -o /dev/null -w "gw_post:%{http_code}\n" http://127.0.0.1:4001/health
curl -fsS -o /dev/null -w "cms_demo:%{http_code}\n" 'http://127.0.0.1:4001/api/public/cms?config_key=panne-demo'
curl -fsS -o /dev/null -w "cms_default:%{http_code}\n" 'http://127.0.0.1:4001/api/public/cms?config_key=default'
echo FALLBACK_TEST_DONE
