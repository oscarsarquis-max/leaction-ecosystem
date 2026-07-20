# =============================================================================
# inove4us — imagem de produção (SPA + Flask/Gunicorn)
# Destino: AWS App Runner ou ECS Fargate · domínio inove4us.com.br
# =============================================================================

# --- Stage 1: build frontend Vite ------------------------------------------------
FROM node:20-alpine AS frontend-build
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: runtime Python -----------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INOVE4US_ENV=production \
    FLASK_ENV=production \
    PORT=8080 \
    SPA_DIR=/app/frontend/dist \
    WEB_CONCURRENCY=2

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY VERSION /app/VERSION
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
COPY --from=frontend-build /fe/dist /app/frontend/dist

# Garantir logos/imagens no static Flask
RUN mkdir -p /app/backend/static/imagens \
    && if [ -d /app/frontend/dist/imagens ]; then cp -r /app/frontend/dist/imagens/* /app/backend/static/imagens/ || true; fi

# Se as logos vierem só do public/ (não entram no dist), copie no build context:
COPY frontend/public/imagens/ /app/backend/static/imagens/

WORKDIR /app/backend
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

CMD gunicorn wsgi:app \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WEB_CONCURRENCY}" \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
