#!/usr/bin/env bash
# Na EC2: pull imagens Phanton + compose up + schema (build fica no PC de deploy).
set -euo pipefail
cd /home/ubuntu

ECR=253137917703.dkr.ecr.us-east-2.amazonaws.com
REGION=us-east-2

echo "==> ECR login..."
aws ecr get-login-password --region "$REGION" | sudo docker login --username AWS --password-stdin "$ECR"

echo "==> Compose pull + up..."
sudo docker compose pull phanton_backend phanton_frontend
sudo docker compose up -d

echo "==> Reload Caddy (novo site block)..."
sudo docker exec mativas_prod_caddy caddy reload --config /etc/caddy/Caddyfile || \
  sudo docker compose up -d --force-recreate caddy

sleep 8
echo "==> Apply schema (idempotent)..."
sudo docker exec -e PYTHONPATH=/app:/app/backend phanton_prod_backend \
  python /app/backend/scripts/apply_prod_schema.py || true

echo "==> Health..."
curl -sk https://phanton.ia.br/health || true
echo
curl -sk -o /dev/null -w "phanton_home:%{http_code}\n" https://phanton.ia.br/ || true
curl -sk https://metodologiasinovativas.com.br/health || true
echo
sudo docker compose ps
