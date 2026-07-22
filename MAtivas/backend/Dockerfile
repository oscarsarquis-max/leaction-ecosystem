# Imagem base ultra leve do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala dependências de sistema necessárias para o psycopg2 e conversão do logo
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    librsvg2-bin \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas o arquivo de dependências primeiro (otimiza o cache do Docker)
COPY backend/requirements.txt .

# Instala as bibliotecas do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do backend para dentro do contêiner (/app)
COPY backend/ .

# Nunca embutir .env de desenvolvimento na imagem de produção
RUN rm -f .env

# Modelos SQLAlchemy e migrações (guardrails dinâmicos + rotas admin)
COPY database/ ./database/

# Copia o worker de IA e demais serviços para /app/services
# (o container "worker" executa: python /app/services/ai_worker.py)
# Inclui services/assets/brand/logo.png — mesmo logotipo do site.
COPY services/ ./services/

# Biblioteca canônica de passos (usada pelo worker)
COPY biblioteca_passos.py .

# Metadados de release (health: version + git_sha)
COPY VERSION .
ARG APP_VERSION=
ARG GIT_SHA=unknown
ENV APP_VERSION=${APP_VERSION}
ENV GIT_SHA=${GIT_SHA}

# Expõe a porta interna da API Flask
EXPOSE 5000

# Comando padrão para iniciar a API
CMD ["python", "app.py"]