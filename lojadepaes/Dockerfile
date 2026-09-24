# Loja de Pães — imagem de produção (SPA + FastAPI)
FROM node:20-alpine AS frontend-build
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOJADEPAES_ENV=production \
    LOJADEPAES_HTTP_HOST=0.0.0.0 \
    LOJADEPAES_HTTP_PORT=8080 \
    LOJADEPAES_SPA_DIR=/app/frontend/dist \
    LOJADEPAES_COOKIE_SECURE=true \
    LOJADEPAES_ADMIN_LOCAL_PASSWORDLESS=false
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/app /app/backend/app
COPY database /app/database
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend
RUN pip install --no-cache-dir ".[s3,mail]"
COPY --from=frontend-build /fe/dist /app/frontend/dist
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:8080/api/v1/health" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
