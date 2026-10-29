set -e
echo '=== free FE tree (keep gateway) ==='
rm -rf /var/www/leaction-platform/frontend/action-hub/node_modules
rm -rf /var/www/leaction-platform/frontend/action-hub/.next
snap list --all 2>/dev/null | awk '/disabled/{print $1, $3}' | while read name rev; do sudo snap remove "$name" --revision="$rev" 2>/dev/null || true; done
df -h /
echo '=== verify CMS keys in code ==='
grep -n 'panne-demo' /var/www/leaction-platform/services/gateway-api/domain/cms-site-config.js | head -5
echo '=== gateway deps ==='
cd /var/www/leaction-platform/services/gateway-api
npm ci --omit=dev --no-audit --no-fund
echo '=== pm2 restart gateway only ==='
pm2 restart gateway-api --update-env
sleep 3
curl -s -o /dev/null -w 'gw_local:%{http_code}\n' http://127.0.0.1:4001/health
curl -s -o /dev/null -w 'panne-demo:%{http_code}\n' 'http://127.0.0.1:4001/api/public/cms?config_key=panne-demo'
curl -s -o /dev/null -w 'default:%{http_code}\n' 'http://127.0.0.1:4001/api/public/cms?config_key=default'
curl -s -o /dev/null -w 'inove4us:%{http_code}\n' 'http://127.0.0.1:4001/api/public/cms?config_key=inove4us'
pm2 list
df -h /
echo GATEWAY_CMS_OK
