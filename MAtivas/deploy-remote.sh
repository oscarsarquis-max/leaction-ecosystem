#!/usr/bin/env bash
# =====================================================================
# MAtivas - Deploy remoto na EC2 (via SSH)
# ---------------------------------------------------------------------
# Conecta na instância EC2, autentica no ECR, baixa as imagens mais
# recentes e recria os containers com docker compose.
#
# Fluxo recomendado:
#   1) ./deploy.sh           # build + push das imagens para o ECR
#   2) ./deploy-remote.sh    # pull + up -d no servidor de produção
#
# Para também enviar o docker-compose.yml local ao servidor:
#   SYNC_COMPOSE=1 ./deploy-remote.sh
#   (atenção: confirme se a senha do RDS no compose local está correta)
#
# Pré-requisitos no servidor: Docker + AWS CLI configurada com acesso
# de pull no ECR. Execute a partir da raiz do projeto.
# =====================================================================
set -euo pipefail

# ----- Configuração --------------------------------------------------
EC2_HOST="ubuntu@3.141.12.134"
ECR_REGISTRY="253137917703.dkr.ecr.us-east-2.amazonaws.com"
AWS_REGION="us-east-2"
REMOTE_DIR="/home/ubuntu"
SYNC_COMPOSE="${SYNC_COMPOSE:-0}"

# Resolve caminhos relativos à raiz do projeto (onde este script está).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSH_KEY="${SSH_KEY:-$SCRIPT_DIR/chaves/mativas-key.pem}"

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)

# ----- Validações ----------------------------------------------------
if [[ ! -f "$SSH_KEY" ]]; then
  echo "ERRO: chave SSH não encontrada em: $SSH_KEY" >&2
  echo "Defina o caminho com: SSH_KEY=/caminho/mativas-key.pem ./deploy-remote.sh" >&2
  exit 1
fi
echo "==> Chave SSH: $SSH_KEY"

# ----- (Opcional) sincroniza o docker-compose.yml --------------------
if [[ "$SYNC_COMPOSE" == "1" ]]; then
  echo "==> Enviando docker-compose.yml local para ${EC2_HOST}:${REMOTE_DIR}/ ..."
  scp "${SSH_OPTS[@]}" "$SCRIPT_DIR/backend/docker-compose.yml" \
    "${EC2_HOST}:${REMOTE_DIR}/docker-compose.yml"
fi

# ----- Deploy remoto -------------------------------------------------
echo "==> Conectando na EC2 (${EC2_HOST}) e atualizando os containers..."
ssh "${SSH_OPTS[@]}" "$EC2_HOST" bash -s <<REMOTE
set -euo pipefail
cd "${REMOTE_DIR}"

echo "--> Autenticando no ECR (${AWS_REGION})..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | sudo docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "--> Baixando as imagens mais recentes (pull)..."
sudo docker compose pull

echo "--> Recriando os containers (up -d)..."
sudo docker compose up -d

echo "--> Removendo imagens órfãs (prune)..."
sudo docker image prune -f

echo "--> Status dos serviços:"
sudo docker compose ps
REMOTE

echo ""
echo "====================================================================="
echo "  Deploy remoto concluído!"
echo "  Site     -> https://metodologiasinovativas.com.br"
echo "  Admin    -> https://metodologiasinovativas.com.br/admin"
echo "====================================================================="
