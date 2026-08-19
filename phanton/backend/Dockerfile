# Phanton backend — produção (uvicorn)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependências primeiro (cache). ML opcional (chroma/ST) fica comentado no requirements.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Código: backend + services + database SQL (schema apply opcional)
COPY backend/ /app/backend/
COPY services/ /app/services/
COPY database/ /app/database/

# Não embutir .env de desenvolvimento
RUN rm -f /app/backend/.env

ENV PYTHONPATH=/app:/app/backend
ENV PYTHONUNBUFFERED=1
WORKDIR /app/backend

EXPOSE 8010
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1"]
