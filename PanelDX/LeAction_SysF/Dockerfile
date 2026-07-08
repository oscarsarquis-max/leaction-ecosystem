# =====================================================================
# PanelDX — Backend (Flask + Agentes de IA) servido por Gunicorn
# =====================================================================
FROM python:3.10-slim

# Evita .pyc e garante logs sem buffer (importante para CloudWatch)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app
# Permite que os workers (ai_engine/*.py) importem 'database' e 'ai_engine'
ENV PYTHONPATH=/usr/src/app

# Dependências de sistema para compilar psycopg2 e afins
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential python3-dev libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 1. Instala dependências Python primeiro (cache de camadas)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

# 2. Copia o restante do código
COPY . .

# 3. Entrypoint: sobe os workers assíncronos e executa o Gunicorn
# sed remove CR (\r) caso o arquivo tenha sido salvo com quebras de linha do Windows
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# Porta do Gunicorn (produção)
EXPOSE 5000

ENTRYPOINT ["./entrypoint.sh"]
