#!/bin/bash
set -euo pipefail
APP=/var/www/leaction-platform/frontend/action-hub
TGZ=/tmp/hub-fe-4dcc5cb-publish.tgz
PUB=/var/lib/leaction-platform/fe-published-028-cms
EXTRACT=/tmp/hub-fe-extract

echo "==> disk before"
df -h / | tail -1

echo "==> ensure source has panne options"
grep -n 'panne-demo\|Panne' "$APP/src/components/admin/CmsSiteForm.tsx" | head -8

echo "==> install prod node_modules (linux)"
cd "$APP"
npm ci --omit=dev --no-audit --no-fund

echo "==> extract prebuilt .next"
rm -rf "$EXTRACT"
mkdir -p "$EXTRACT"
tar -xzf "$TGZ" -C "$EXTRACT"
rm -rf "$APP/.next"
cp -a "$EXTRACT/.next" "$APP/.next"
cp -f "$EXTRACT/VERSION" "$APP/VERSION"
cp -f "$EXTRACT/GIT_SHA" "$APP/GIT_SHA"

echo "==> keep published copy for this-release rollback"
rm -rf "$PUB"
mkdir -p "$PUB"
cp -a "$APP/.next" "$PUB/.next"
cp -f "$APP/VERSION" "$PUB/VERSION"
cp -f "$APP/GIT_SHA" "$PUB/GIT_SHA"
date -u +%Y-%m-%dT%H:%M:%SZ > "$PUB/PUBLISHED_AT"
cp -f "$APP/.next/BUILD_ID" "$PUB/BUILD_ID.txt"
du -sh "$APP/.next" "$APP/node_modules" "$PUB"

echo "==> restart action-hub only"
pm2 restart action-hub --update-env
sleep 5
curl -s -o /dev/null -w "health:%{http_code}\n" http://127.0.0.1:4000/api/health
curl -s -o /dev/null -w "cms_site:%{http_code}\n" http://127.0.0.1:4000/dashboard/cms/site
pm2 describe action-hub | sed -n '1,25p'
df -h / | tail -1
echo "VERSION=$(cat "$APP/VERSION")"
echo "GIT_SHA=$(cat "$APP/GIT_SHA")"
echo "BUILD_ID=$(cat "$APP/.next/BUILD_ID")"
echo FE_PUBLISH_OK
