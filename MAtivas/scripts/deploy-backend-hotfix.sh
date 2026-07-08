#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu
ECR=253137917703.dkr.ecr.us-east-2.amazonaws.com
REGION=us-east-2

echo "==> Backend rebuild..."
rm -rf mativas-build
mkdir mativas-build
tar -xzf mativas-backend-deploy.tgz -C mativas-build
cd mativas-build
aws ecr get-login-password --region "$REGION" | sudo docker login --username AWS --password-stdin "$ECR"
sudo docker build --platform linux/amd64 -t mativas-backend:latest -f backend/Dockerfile .
sudo docker tag mativas-backend:latest "$ECR/mativas-backend:latest"
sudo docker push "$ECR/mativas-backend:latest"

cd /home/ubuntu
sudo docker compose pull backend worker
sudo docker compose up -d backend worker

sleep 8
echo "==> Backend logs..."
sudo docker logs mativas_prod_backend --tail 20

echo "==> Migration 005..."
sudo docker exec -e PYTHONPATH=/app mativas_prod_backend python database/migrations/apply_005.py || true

echo "==> Migration 006..."
sudo docker exec -e PYTHONPATH=/app mativas_prod_backend python database/migrations/apply_006.py || true

echo "==> Health..."
curl -sk https://metodologiasinovativas.com.br/health
echo
sudo docker compose ps
