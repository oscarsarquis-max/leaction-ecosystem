FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home isa
COPY server ./server
COPY prototype ./prototype
COPY scripts ./scripts
COPY VERSION .
USER 10001
EXPOSE 8091
CMD ["python", "server/prod_serve.py"]
