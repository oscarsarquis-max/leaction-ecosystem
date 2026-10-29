#!/bin/bash
set -euo pipefail
APP=/var/www/leaction-platform/frontend/action-hub
OUT=/tmp/selector-proof.txt
{
  echo "BUILD_ID=$(cat $APP/.next/BUILD_ID)"
  echo "VERSION=$(cat $APP/VERSION)"
  echo "GIT_SHA=$(cat $APP/GIT_SHA)"
  echo '--- static chunk hits ---'
  grep -Rao 'Panne — Demonstração\|Panne — Produção\|PanelDX (default)\|inove4us School\|inove4us - página' "$APP/.next/static" 2>/dev/null | sort | uniq -c
  echo '--- option values ---'
  grep -Rao 'panne-demo\|"panne"\|value:"default"\|value:"inove4us"' "$APP/.next/static" 2>/dev/null | sort | uniq -c | head -30
} > "$OUT"
cat "$OUT"
