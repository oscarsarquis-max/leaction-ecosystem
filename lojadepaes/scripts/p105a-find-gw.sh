#!/usr/bin/env bash
set -eu
for d in /proc/[0-9]*; do
  cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null || true)
  case "$cmd" in
    *gateway*) echo "$(basename "$d") $cmd" ;;
  esac
done
