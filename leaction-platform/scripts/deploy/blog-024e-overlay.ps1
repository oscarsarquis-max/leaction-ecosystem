# BLOG-024e — overlay Hub sem deploy-remote.ps1; build FE em pasta nova + pm2 reload.
$ErrorActionPreference = 'Stop'
$key = 'C:\Projetos\leaction-platform\chaves\action_hub_keys.pem'
$sshHost = 'ubuntu@3.17.19.188'
$ssh = @('-i', $key, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'ServerAliveInterval=15')
$scp = @('-i', $key, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new')
$base = 'C:\Projetos\_blog-024e\leaction-platform'
$remote = '/var/www/leaction-platform'

$files = @(
  'services/gateway-api/domain/cms-sugestoes-lib.js',
  'services/gateway-api/domain/cms-sugestoes.test.js',
  'frontend/action-hub/src/lib/admin-api.ts',
  'frontend/action-hub/src/components/admin/CmsSugestoes.tsx'
)

ssh @ssh $sshHost @"
mkdir -p $remote/services/gateway-api/domain \
  $remote/frontend/action-hub/src/lib \
  $remote/frontend/action-hub/src/components/admin
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

cd "$ROOT/services/gateway-api"
node --test domain/cms-sugestoes.test.js | tail -n 8

# Build FE fora do .next ao vivo
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

MONITOR=/tmp/blog024e-health-monitor.txt
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
echo BLOG024E_HUB_OK
'@
$apply = $apply -replace "`r", ''
ssh @ssh $sshHost $apply
if ($LASTEXITCODE -ne 0) { throw "remote apply failed exit=$LASTEXITCODE" }
Write-Host "DEPLOY_HUB_OK"
