#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

DOMAIN="chamelleon.com.br"
WWW="www.chamelleon.com.br"
APP_ROOT="/opt/chamelleon"
CERTBOT_EMAIL="sysadmin@leaction.com.br"
DB_NAME="chamelleon"
DB_USER="chamelleon"
DB_PASS="$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)"

apt-get update -y
apt-get upgrade -y
apt-get install -y \
  nginx certbot python3-certbot-nginx \
  python3 python3-venv python3-pip \
  postgresql postgresql-contrib \
  git curl unzip rsync dnsutils \
  build-essential libpq-dev

curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

mkdir -p "$APP_ROOT"/{backend,frontend,logs,bin}
chown -R ubuntu:ubuntu "$APP_ROOT"

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

cat > "${APP_ROOT}/backend/.env.production" <<EOF
FLASK_ENV=production
FLASK_DEBUG=0
PORT=5010
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}
CHAMELLEON_PUBLIC_URL=https://${DOMAIN}
AWS_REGION=us-east-2
BEDROCK_REGION=us-east-1
EOF
chmod 600 "${APP_ROOT}/backend/.env.production"
chown ubuntu:ubuntu "${APP_ROOT}/backend/.env.production"

cat > /etc/nginx/sites-available/chamelleon <<'NGINX'
server {
    listen 80;
    listen [::]:80;
    server_name chamelleon.com.br www.chamelleon.com.br;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    root /opt/chamelleon/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:5010;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/chamelleon /etc/nginx/sites-enabled/chamelleon
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx

cat > /etc/systemd/system/chamelleon-api.service <<'UNIT'
[Unit]
Description=Chamelleon API (Flask/Gunicorn)
After=network.target postgresql.service

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/chamelleon/backend
Environment=PYTHONPATH=/opt/chamelleon/backend
EnvironmentFile=/opt/chamelleon/backend/.env
ExecStart=/opt/chamelleon/backend/.venv/bin/gunicorn --bind 127.0.0.1:5010 --workers 2 --timeout 120 "run:app"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable chamelleon-api.service || true

cat > "${APP_ROOT}/bin/setup-https.sh" <<'HTTPS'
#!/bin/bash
set -euo pipefail
DOMAIN="chamelleon.com.br"
WWW="www.chamelleon.com.br"
EMAIL="sysadmin@leaction.com.br"
EXPECTED="$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || true)"

echo "Aguardando DNS apontar para ${EXPECTED}..."
for i in $(seq 1 60); do
  RESOLVED="$(dig +short A "${DOMAIN}" @8.8.8.8 | tail -n1 || true)"
  if [ -n "${RESOLVED}" ] && [ "${RESOLVED}" = "${EXPECTED}" ]; then
    echo "DNS OK: ${DOMAIN} -> ${RESOLVED}"
    break
  fi
  sleep 30
done

certbot --nginx \
  -d "${DOMAIN}" -d "${WWW}" \
  --non-interactive --agree-tos -m "${EMAIL}" \
  --redirect || {
    echo "Certbot falhou — tente manualmente: sudo /opt/chamelleon/bin/setup-https.sh"
    exit 1
  }

systemctl reload nginx
echo "HTTPS ativo em https://${DOMAIN}"
HTTPS
chmod +x "${APP_ROOT}/bin/setup-https.sh"
chown ubuntu:ubuntu "${APP_ROOT}/bin/setup-https.sh"

cat > /etc/systemd/system/chamelleon-https.service <<UNIT
[Unit]
Description=Chamelleon HTTPS (Certbot)
After=network-online.target nginx.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=${APP_ROOT}/bin/setup-https.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable chamelleon-https.service
systemctl start chamelleon-https.service || true

echo "Bootstrap concluido. DB user=${DB_USER} pass=${DB_PASS}" > /var/log/chamelleon-bootstrap.log
chmod 600 /var/log/chamelleon-bootstrap.log
