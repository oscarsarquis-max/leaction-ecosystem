# BLOG-025 — overlay Hub (gateway + CMS FE) sem deploy-remote.ps1; build FE em pasta nova + pm2 reload.
$ErrorActionPreference = 'Stop'
$key = 'C:\Projetos\leaction-platform\chaves\action_hub_keys.pem'
$sshHost = 'ubuntu@3.17.19.188'
$ssh = @('-i', $key, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'ServerAliveInterval=15')
$scp = @('-i', $key, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new')
$base = 'C:\Projetos\_blog-025\leaction-platform'
$remote = '/var/www/leaction-platform'

$files = @(
  'services/gateway-api/domain/cms-receitas.js',
  'services/gateway-api/domain/cms-receitas.test.js',
  'services/gateway-api/domain/cms-enquete-ludica.test.js',
  'services/gateway-api/domain/cms-right-now.js',
  'services/gateway-api/domain/cms-sugestoes-job.js',
  'services/gateway-api/domain/loja-integracoes-client.js',
  'services/gateway-api/server.js',
  'shared/database/patch_cms_receitas_enquete_025.sql',
  'frontend/action-hub/src/lib/admin-api.ts',
  'frontend/action-hub/src/components/admin/CmsEnquetes.tsx',
  'frontend/action-hub/src/components/admin/CmsReceitas.tsx',
  'frontend/action-hub/src/components/admin/CmsPostsList.tsx',
  'frontend/action-hub/src/app/dashboard/cms/layout.tsx',
  'frontend/action-hub/src/app/dashboard/cms/receitas/page.tsx'
)

ssh @ssh $sshHost @"
mkdir -p $remote/services/gateway-api/domain \
  $remote/shared/database \
  $remote/frontend/action-hub/src/lib \
  $remote/frontend/action-hub/src/components/admin \
  $remote/frontend/action-hub/src/app/dashboard/cms/receitas
"@

foreach ($f in $files) {
  $src = Join-Path $base ($f -replace '/', [IO.Path]::DirectorySeparatorChar.ToString())
  if (-not (Test-Path -LiteralPath $src)) { throw "missing $src" }
  scp @scp -- $src "${sshHost}:${remote}/$f"
  Write-Host "COPIED $f"
}

$apply = @'
set -euo pipefail
ROOT=/var/www/leaction-platform
FE=$ROOT/frontend/action-hub
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BUILD=/tmp/action-hub-build-$STAMP
SQL=$ROOT/shared/database/patch_cms_receitas_enquete_025.sql

# Patch SQL aditivo
if [ -f "$SQL" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/services/gateway-api/.env" 2>/dev/null || true
  set +a
  if [ -n "${DATABASE_URL:-}" ]; then
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$SQL"
    echo SQL_OK
  else
    echo "WARN: DATABASE_URL ausente; SQL não aplicado"
  fi
fi

cd "$ROOT/services/gateway-api"
node --test domain/cms-receitas.test.js domain/cms-enquete-ludica.test.js | tail -n 12

rm -rf "$BUILD"
mkdir -p "$BUILD"
rsync -a --delete --exclude '.next' --exclude '.next-*' --exclude 'node_modules' --exclude '.git' "$FE/" "$BUILD/"
rsync -a "$FE/node_modules/" "$BUILD/node_modules/"
(cd "$BUILD" && npm run build)
test -f "$BUILD/.next/BUILD_ID"
rm -rf "$FE/.next-prev"
if [ -d "$FE/.next" ]; then mv "$FE/.next" "$FE/.next-prev"; fi
mv "$BUILD/.next" "$FE/.next"
rm -rf "$BUILD"

MONITOR=/tmp/blog025-health-monitor.txt
: > "$MONITOR"
(
  for i in $(seq 1 90); do
    ts=$(date -Is)
    gw=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://127.0.0.1:4001/health || echo 000)
    fe=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://127.0.0.1:4000/api/health || echo 000)
    mkt=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://127.0.0.1:4012/api/marketplace/health || echo 000)
    echo "$ts gw=$gw fe=$fe mkt=$mkt" >> "$MONITOR"
    sleep 2
  done
) &
MON_PID=$!

pm2 reload gateway-api --update-env
pm2 reload action-hub --update-env

ok_gw=0; ok_fe=0
for _ in $(seq 1 40); do
  gw=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://127.0.0.1:4001/health || echo 000)
  fe=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://127.0.0.1:4000/api/health || echo 000)
  [ "$gw" = "200" ] && ok_gw=1
  [ "$fe" = "200" ] && ok_fe=1
  if [ "$ok_gw" = "1" ] && [ "$ok_fe" = "1" ]; then break; fi
  sleep 1
done
kill "$MON_PID" 2>/dev/null || true
wait "$MON_PID" 2>/dev/null || true

bad=$(grep -E 'gw=(000|5|4)|fe=(000|5|4)|mkt=(000|5)' "$MONITOR" | grep -v 'gw=200 fe=200' || true)
echo "HEALTH_MONITOR_LINES=$(wc -l < "$MONITOR")"
echo "HEALTH_NON_200=$(echo "$bad" | grep -c . || true)"
if [ "$ok_gw" != "1" ] || [ "$ok_fe" != "1" ]; then
  echo HEALTH_FAIL
  exit 1
fi
curl -s -o /dev/null -w "mkt=%{http_code}\n" http://127.0.0.1:4012/api/marketplace/health || true
pm2 ls | sed -n '1,12p'
echo "BUILD_ID=$(cat "$FE/.next/BUILD_ID")"
echo BLOG025_HUB_OK
'@
$apply = $apply -replace "`r", ''
ssh @ssh $sshHost $apply
if ($LASTEXITCODE -ne 0) { throw "remote apply failed exit=$LASTEXITCODE" }
Write-Host "DEPLOY_HUB_OK"
