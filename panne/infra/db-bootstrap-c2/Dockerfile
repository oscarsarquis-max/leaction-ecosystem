# syntax=docker/dockerfile:1.7
# CURSOR-027-C2-H1 — harden only; never reuse img1–img4 digests
FROM public.ecr.aws/docker/library/python:3.13-alpine@sha256:540c7d91f98ff6880174c40e99067bf5941eb54d818a7a5e094d188b196a934d

WORKDIR /app

RUN apk add --no-cache ca-certificates \
    && apk upgrade --no-cache \
    && addgroup -g 10001 -S panne \
    && adduser -u 10001 -S -G panne -H -s /sbin/nologin panne

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip==25.0.1 \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

COPY harden.py .

USER 10001:10001
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["python", "-u", "/app/harden.py"]
