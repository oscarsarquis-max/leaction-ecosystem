#!/bin/sh
# =====================================================================
# PanelDX — Entrypoint do Backend
# Sob Gunicorn, o app.py é IMPORTADO (não roda como __main__), então os
# workers assíncronos não sobem sozinhos. Aqui eles são iniciados em
# background e o Gunicorn assume o processo principal (foreground).
# =====================================================================
set -e

echo "🛰️  [ENTRYPOINT] Iniciando Worker IA Master..."
python ai_engine/worker.py &

echo "🤖 [ENTRYPOINT] Iniciando Worker Modulador..."
python ai_engine/modulador_worker.py &

echo "🚀 [ENTRYPOINT] Iniciando Gunicorn na porta 5000..."
exec gunicorn --bind 0.0.0.0:5000 --workers 3 --timeout 120 app:app
