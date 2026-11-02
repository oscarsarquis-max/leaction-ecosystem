# Loja de Pães – Gestão — imagem de produção (SPA + FastAPI). Contexto de build: esta pasta.
FROM node:20-alpine AS frontend-build
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GESTAO_ENV=production \
    GESTAO_COOKIE_SECURE=true \
    GESTAO_SPA_DIR=/app/frontend/dist
WORKDIR /app
RUN useradd --create-home --uid 10002 appuser
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/app /app/backend/app
COPY database /app/database
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend
RUN pip install --no-cache-dir .
COPY --from=frontend-build /fe/dist /app/frontend/dist
USER appuser
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8090/api/v1/health', timeout=4)"]
# Um worker só: o Gestão é de uso interno e a memória do servidor é compartilhada com a Loja.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
