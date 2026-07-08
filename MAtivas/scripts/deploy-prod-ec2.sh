#!/usr/bin/env bash
# Deploy completo na EC2 (build remoto + migrations + compose up)
set -euo pipefail
cd /home/ubuntu

ECR=253137917703.dkr.ecr.us-east-2.amazonaws.com
REGION=us-east-2

echo "==> Backend rebuild..."
rm -rf mativas-build
mkdir mativas-build
tar -xzf mativas-backend-deploy.tgz -C mativas-build
cd mativas-build
aws ecr get-login-password --region $REGION | sudo docker login --username AWS --password-stdin $ECR
sudo docker build --platform linux/amd64 -t mativas-backend:latest -f backend/Dockerfile .
sudo docker tag mativas-backend:latest $ECR/mativas-backend:latest
sudo docker push $ECR/mativas-backend:latest

echo "==> Frontend rebuild..."
cd /home/ubuntu
rm -rf frontend-dist
mkdir frontend-dist
tar -xzf mativas-frontend-dist.tgz -C frontend-dist
cd frontend-dist
sudo docker build -f Dockerfile.prod -t mativas-frontend:latest .
sudo docker tag mativas-frontend:latest $ECR/mativas-frontend:latest
sudo docker push $ECR/mativas-frontend:latest

echo "==> Compose up..."
cd /home/ubuntu
sudo docker compose pull
sudo docker compose up -d

echo "==> Migrations (ui_content + logo labels + email dedup)..."
sudo docker exec -e PYTHONPATH=/app mativas_prod_backend python database/migrations/apply_002.py || true
sudo docker exec -e PYTHONPATH=/app mativas_prod_backend python database/migrations/apply_003.py || true
sudo docker exec -e PYTHONPATH=/app mativas_prod_backend python database/migrations/apply_004.py || true
sudo docker exec -e PYTHONPATH=/app mativas_prod_backend python database/migrations/apply_005.py || true

sleep 4
echo "==> Health check..."
curl -sk https://metodologiasinovativas.com.br/health || true
echo
echo "==> UI content endpoint..."
curl -sk https://metodologiasinovativas.com.br/api/ui/conteudo | head -c 200 || true
echo
sudo docker compose ps
