#!/usr/bin/env bash
set -eu
cd /opt/lojadepaes/app/infra
echo FLAGS
sudo docker compose -f docker-compose.prod.yml exec -T api python -c 'from app.core.config import get_settings; s=get_settings(); print("public_acc", s.public_accompaniments_enabled); print("gigio_acc", s.gigio_accompaniments_enabled); print("preview", s.accompaniments_preview); print("gigio", s.gigio_enabled); print("payments", s.public_payments_enabled); print("orders", s.public_orders_enabled); print("mkt", bool(s.actionhub_marketplace_url))'
echo READY
curl -fsS https://lojadepaes.com.br/api/v1/ready
echo
echo ACC
curl -sS -w " http=%{http_code}\n" https://lojadepaes.com.br/api/v1/accompaniments
echo GIGIO
curl -fsS https://lojadepaes.com.br/api/v1/gigio/status
echo
echo HTML
curl -fsS https://lojadepaes.com.br/ | grep -oE '/assets/index-[A-Za-z0-9]+\.(js|css)' | head
echo CATALOG
curl -sS -w " http=%{http_code}\n" https://lojadepaes.com.br/api/v1/catalog/products | python3 -c 'import json,sys; raw=sys.stdin.read(); print(raw[-80:] if len(raw)<200 else "catalog_ok")'
echo LOGS
sudo docker compose -f docker-compose.prod.yml logs --tail 60 api | tail -20
