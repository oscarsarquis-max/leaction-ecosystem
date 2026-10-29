# syntax=docker/dockerfile:1.7
# CURSOR-027 homolog — Panne backend (img7c: seed validate under NO FORCE)
FROM public.ecr.aws/docker/library/python:3.13-alpine@sha256:540c7d91f98ff6880174c40e99067bf5941eb54d818a7a5e094d188b196a934d

WORKDIR /app

RUN apk add --no-cache ca-certificates libpq \
    && apk upgrade --no-cache \
    && addgroup -g 10001 -S panne \
    && adduser -u 10001 -S -G panne -H -s /sbin/nologin panne

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY alembic ./alembic
COPY tests ./tests

RUN pip install --no-cache-dir --upgrade pip==25.0.1 \
    && pip install --no-cache-dir . \
    && pip install --no-cache-dir "boto3>=1.35,<2" "psycopg[binary]>=3.2,<4" "httpx>=0.28,<1" \
    && rm -rf /root/.cache/pip /tmp/*

COPY migrate_runner.py redaction.py rotate_demo_migrator.py seed_runner.py ./
RUN chown -R panne:panne /app

USER 10001:10001
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PANNE_ENV=prod \
    PANNE_HTTP_HOST=0.0.0.0 \
    PANNE_HTTP_PORT=5080

EXPOSE 5080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5080/health', timeout=3)" || exit 1

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5080"]
