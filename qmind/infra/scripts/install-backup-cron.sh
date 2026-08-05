#!/usr/bin/env bash
# Instalar no host Lightsail após copiar backup-pg-homolog.sh
set -euo pipefail
install -d -m 755 /opt/qmind/bin
install -m 755 "$(dirname "$0")/backup-pg-homolog.sh" /opt/qmind/bin/backup-pg-homolog.sh
CRON_LINE='15 3 * * * /opt/qmind/bin/backup-pg-homolog.sh >>/var/log/qmind-backup.log 2>&1'
(crontab -l 2>/dev/null | grep -v backup-pg-homolog || true; echo "$CRON_LINE") | crontab -
echo "Cron diário 03:15 local instalado."
