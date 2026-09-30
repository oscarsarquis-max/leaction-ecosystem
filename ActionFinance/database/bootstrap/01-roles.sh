#!/bin/bash
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE actionfinance_migrator LOGIN PASSWORD '${ACTIONFINANCE_MIGRATOR_PASSWORD}';
CREATE ROLE actionfinance_runtime LOGIN PASSWORD '${ACTIONFINANCE_RUNTIME_PASSWORD}';
CREATE SCHEMA actionfinance AUTHORIZATION actionfinance_migrator;
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_migrator;
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_runtime;
GRANT USAGE ON SCHEMA actionfinance TO actionfinance_runtime;
REVOKE CREATE ON SCHEMA actionfinance FROM PUBLIC;
REVOKE CREATE ON SCHEMA actionfinance FROM actionfinance_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
COMMENT ON SCHEMA actionfinance IS 'Schema criado no bootstrap local. Flyway é o proprietário das migrations.';
EOSQL
