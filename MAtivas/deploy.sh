#!/usr/bin/env bash
# =====================================================================
# MAtivas - Deploy das imagens Docker para o Amazon ECR
# ---------------------------------------------------------------------
# Faz o build, tag e push das imagens de backend e frontend prontas
# para produção. Execute a partir da raiz do projeto:
#
#   ./deploy.sh
#
# Pré-requisitos: Docker em execução e AWS CLI autenticada com permissão
# de push no repositório ECR.
# =====================================================================
set -euo pipefail

# ----- Configuração --------------------------------------------------
ECR_REGISTRY="253137917703.dkr.ecr.us-east-2.amazonaws.com"
AWS_REGION="us-east-2"
TAG="${IMAGE_TAG:-latest}"
PLATFORM="linux/amd64"   # arquitetura da instância EC2 de produção

BACKEND_IMAGE="mativas-backend"
FRONTEND_IMAGE="mativas-frontend"

# Garante execução a partir da raiz do projeto (onde este script está).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Autenticando no Amazon ECR (${AWS_REGION})..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

# ----- Backend (contexto = raiz, para incluir backend/ e services/) --
echo "==> [1/2] Build do backend (${BACKEND_IMAGE}:${TAG})..."
docker build \
  --platform "$PLATFORM" \
  -t "${BACKEND_IMAGE}:${TAG}" \
  -f backend/Dockerfile \
  .

echo "==> Tag e push do backend..."
docker tag "${BACKEND_IMAGE}:${TAG}" "${ECR_REGISTRY}/${BACKEND_IMAGE}:${TAG}"
docker push "${ECR_REGISTRY}/${BACKEND_IMAGE}:${TAG}"

# ----- Frontend (contexto = pasta frontend) --------------------------
echo "==> [2/2] Build do frontend (${FRONTEND_IMAGE}:${TAG})..."
docker build \
  --platform "$PLATFORM" \
  -t "${FRONTEND_IMAGE}:${TAG}" \
  -f frontend/Dockerfile \
  frontend

echo "==> Tag e push do frontend..."
docker tag "${FRONTEND_IMAGE}:${TAG}" "${ECR_REGISTRY}/${FRONTEND_IMAGE}:${TAG}"
docker push "${ECR_REGISTRY}/${FRONTEND_IMAGE}:${TAG}"

echo ""
echo "====================================================================="
echo "  Deploy concluído com sucesso!"
echo "  Backend  -> ${ECR_REGISTRY}/${BACKEND_IMAGE}:${TAG}"
echo "  Frontend -> ${ECR_REGISTRY}/${FRONTEND_IMAGE}:${TAG}"
echo "====================================================================="
