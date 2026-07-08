#!/bin/bash
set -e
echo "[init] Aplicando schema_paneldx.sql (compativel PG 14)..."
sed '/transaction_timeout/d' /schema/schema_paneldx.sql | psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
echo "[init] Schema aplicado com sucesso."
