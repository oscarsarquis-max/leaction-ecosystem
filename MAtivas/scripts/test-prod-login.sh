#!/bin/bash
set -euo pipefail
cat /home/ubuntu/Caddyfile
echo "---"
printf '%s' '{"password":"InovAtivas2026!"}' > /tmp/login.json
curl -s -X POST http://127.0.0.1:5000/api/admin/login \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/login.json \
  --connect-to 127.0.0.1:5000:mativas_prod_backend:5000 2>/dev/null || \
sudo docker run --rm --network container:mativas_prod_backend curlimages/curl:8.5.0 \
  -s -X POST http://127.0.0.1:5000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"password":"InovAtivas2026!"}'
echo
curl -sk -X POST https://metodologiasinovativas.com.br/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"password":"InovAtivas2026!"}'
echo
