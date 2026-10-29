#!/bin/bash
set -euo pipefail
PID=$(pm2 pid action-hub)
echo "pid=$PID"
ls -la /proc/$PID/cwd 2>&1 | head -3
ROLL=/var/lib/leaction-platform/fe-rollback-pre-028-cms
sudo mkdir -p /var/lib/leaction-platform
sudo chown ubuntu:ubuntu /var/lib/leaction-platform
rm -rf "$ROLL"
mkdir -p "$ROLL"
cp -a "/proc/$PID/cwd/." "$ROLL/"
du -sh "$ROLL" "$ROLL/.next" "$ROLL/node_modules" 2>/dev/null || true
if [ -d "$ROLL/.next" ]; then echo ROLLBACK_NEXT_OK; else echo ROLLBACK_NEXT_MISSING; fi
if [ -f "$ROLL/package.json" ]; then echo ROLLBACK_PKG_OK; fi
df -h / | tail -1
date -u +%Y-%m-%dT%H:%M:%SZ > "$ROLL/ROLLBACK_CAPTURED_AT"
echo "from_pid=$PID deleted_cwd" > "$ROLL/ROLLBACK_NOTE.txt"
echo ROLLBACK_CAPTURE_DONE
