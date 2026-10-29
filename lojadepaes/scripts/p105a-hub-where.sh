#!/usr/bin/env bash
set -eu
echo PATH="$PATH"
command -v docker || true
command -v podman || true
ls /usr/bin/docker /usr/local/bin/docker 2>/dev/null || true
pm2 ls || true
ss -lntp | awk 'NR==1 || /5432|4001|3000/'
