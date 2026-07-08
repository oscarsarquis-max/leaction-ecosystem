#!/bin/bash
set -e
APP_ROOT="/opt/chamelleon"
cd "${APP_ROOT}/backend"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
. .venv/bin/activate
pip install -q -U pip
pip install -q -r requirements.txt gunicorn
if [ -f .env.production ] && [ ! -f .env ]; then cp .env.production .env; fi
export PYTHONPATH="${APP_ROOT}/backend"
python -c "
from app import create_app
from app.database.models import db
app = create_app()
with app.app_context():
    # Só cria tabelas em falta + patches ADD COLUMN (nunca DROP/TRUNCATE/seed)
    db.create_all()
    print('Tabelas OK (aditivo)')
"
sudo systemctl restart chamelleon-api || sudo systemctl start chamelleon-api
sudo systemctl reload nginx
echo "Deploy remoto concluido (dados preservados)."
