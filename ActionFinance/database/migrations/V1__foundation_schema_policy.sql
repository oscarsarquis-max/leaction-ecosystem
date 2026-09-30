-- Fundação ActionFinance. Sem tabelas de negócio, cadastro ou sentinela.

COMMENT ON SCHEMA actionfinance IS
    'ActionFinance local schema. Business tables start in a later increment.';

REVOKE CREATE ON SCHEMA actionfinance FROM PUBLIC;
REVOKE CREATE ON SCHEMA actionfinance FROM actionfinance_runtime;
GRANT USAGE ON SCHEMA actionfinance TO actionfinance_runtime;

GRANT SELECT ON TABLE actionfinance.flyway_schema_history TO actionfinance_runtime;
