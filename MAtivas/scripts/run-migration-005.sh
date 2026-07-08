#!/usr/bin/env bash
set -euo pipefail
sudo docker exec -e PYTHONPATH=/app mativas_prod_backend python database/migrations/apply_005.py
echo "done"
