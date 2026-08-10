#!/usr/bin/env bash
# Instala inove4us-school no EC2 Action Hub.
set -euo pipefail
REMOTE="${REMOTE:-/var/www/inove4us-school}"
DOMAIN="${DOMAIN:-school.inove4us.com.br}"
PORT="${PORT:-5012}"
HUB_ENV=/var/www/leaction-platform/.env

set -a
# shellcheck disable=SC1090
. "$HUB_ENV"
set +a

echo "==> Bootstrap DB"
/var/www/leaction-platform/backend/.venv/bin/python /tmp/school-db-bootstrap.py "$REMOTE/infra/db/migrations"

echo "==> Derive DB host from Hub DATABASE_URL"
eval "$(/var/www/leaction-platform/backend/.venv/bin/python - <<'PY'
import os, urllib.parse, shlex
u = os.environ['DATABASE_URL']
p = urllib.parse.urlparse(u)
pw = urllib.parse.unquote(p.password or '')
print('export SCHOOL_DB_HOST=' + shlex.quote(p.hostname or ''))
print('export SCHOOL_DB_PORT=' + shlex.quote(str(p.port or 5432)))
print('export SCHOOL_DB_USER=' + shlex.quote(p.username or ''))
print('export SCHOOL_DB_PASS=' + shlex.quote(pw))
PY
)"

echo "==> Webhook secret from Hub (best effort)"
WEBHOOK="$(/var/www/leaction-platform/backend/.venv/bin/python - <<'PY'
import os, urllib.parse, psycopg2
u = os.environ['DATABASE_URL']
p = urllib.parse.urlparse(u)
dbname = (p.path or '/leaction_hub').lstrip('/') or 'leaction_hub'
conn = psycopg2.connect(
    dbname=dbname,
    user=p.username,
    password=urllib.parse.unquote(p.password or ''),
    host=p.hostname,
    port=p.port or 5432,
    sslmode='require',
)
cur = conn.cursor()
secret = ''
# discover candidates
cur.execute("""
  SELECT table_name FROM information_schema.tables
  WHERE table_schema='public' AND table_name IN ('app_registry','apps','registered_apps')
""")
tables = [r[0] for r in cur.fetchall()]
for table in tables:
    for col_id, col_sec in (('app_id','webhook_secret'),('id','webhook_secret'),('slug','webhook_secret')):
        try:
            cur.execute(
                f"SELECT {col_sec} FROM {table} WHERE CAST({col_id} AS text) ILIKE %s LIMIT 1",
                ('%school%',),
            )
            row = cur.fetchone()
            if row and row[0]:
                secret = str(row[0])
                break
        except Exception:
            conn.rollback()
    if secret:
        break
print(secret)
conn.close()
PY
)"

SECRET_KEY="$(openssl rand -hex 24)"
cat > "$REMOTE/.env" <<EOF
INOVE4US_SCHOOL_ENV=production
FLASK_ENV=production
FLASK_PORT=$PORT
SPA_DIR=$REMOTE/frontend/dist
DB_HOST=$SCHOOL_DB_HOST
DB_PORT=$SCHOOL_DB_PORT
DB_NAME=inove4us_school
DB_USER=$SCHOOL_DB_USER
DB_PASS=$SCHOOL_DB_PASS
DB_SSLMODE=require
SECRET_KEY=$SECRET_KEY
ACTION_HUB_API_URL=https://api.actionhub.com.br
ACTION_HUB_PUBLIC_URL=https://actionhub.com.br
ACTION_HUB_APP_ID=inove4us-school
ACTION_HUB_APP_SECRET=$WEBHOOK
ACTIONHUB_WEBHOOK_SECRET=$WEBHOOK
CORS_ORIGINS=https://school.inove4us.com.br,https://school.actionhub.com.br,https://actionhub.com.br,https://inove4us.com.br
FRONTEND_ORIGIN=https://school.inove4us.com.br
EOF
chmod 600 "$REMOTE/.env"

echo "==> Frontend build"
cd "$REMOTE/frontend"
# Hub .env pode exportar NODE_ENV=production e omitir devDependencies (vite).
env -u NODE_ENV npm install --include=dev
env -u NODE_ENV npm run build

echo "==> Backend venv"
cd "$REMOTE/backend"
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install -q -r requirements.txt

cat > "$REMOTE/ecosystem.school.config.js" <<EOF
module.exports = {
  apps: [{
    name: 'inove4us-school',
    cwd: '$REMOTE/backend',
    script: '.venv/bin/gunicorn',
    args: 'wsgi:app --bind 127.0.0.1:$PORT --workers 2 --threads 4 --timeout 120',
    interpreter: 'none',
    env: {
      INOVE4US_SCHOOL_ENV: 'production',
      FLASK_ENV: 'production'
    },
    autorestart: true,
    max_restarts: 20
  }]
};
EOF

pm2 delete inove4us-school >/dev/null 2>&1 || true
# load dotenv via gunicorn cwd — also export from file for pm2
set -a; . "$REMOTE/.env"; set +a
pm2 start "$REMOTE/ecosystem.school.config.js" --update-env
pm2 save

echo "==> Nginx"
if sudo test -d "/etc/letsencrypt/live/$DOMAIN"; then
  # Cert já existe: manter HTTPS (não sobrescrever só com :80).
  sudo tee /etc/nginx/sites-available/school-actionhub >/dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl;
    http2 on;
    server_name $DOMAIN;
    ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
else
  sudo tee /etc/nginx/sites-available/school-actionhub >/dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
fi
sudo ln -sf /etc/nginx/sites-available/school-actionhub /etc/nginx/sites-enabled/school-actionhub
sudo nginx -t
sudo systemctl reload nginx

if ! sudo test -d "/etc/letsencrypt/live/$DOMAIN"; then
  sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@actionhub.com.br --redirect || {
    echo "WARN: certbot falhou — HTTP ainda ativo em http://$DOMAIN"
  }
fi

echo "==> Health"
curl -fsS "http://127.0.0.1:$PORT/api/health"
echo
curl -fsS "https://$DOMAIN/api/health" || true
echo
echo "OK https://$DOMAIN"
