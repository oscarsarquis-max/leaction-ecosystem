CREATE ROLE actionfinance_migrator LOGIN PASSWORD 'migrator-test';
CREATE ROLE actionfinance_runtime LOGIN PASSWORD 'runtime-test';
CREATE SCHEMA actionfinance AUTHORIZATION actionfinance_migrator;
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_migrator;
GRANT CONNECT ON DATABASE actionfinance TO actionfinance_runtime;
GRANT USAGE ON SCHEMA actionfinance TO actionfinance_runtime;
REVOKE CREATE ON SCHEMA actionfinance FROM PUBLIC;
REVOKE CREATE ON SCHEMA actionfinance FROM actionfinance_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
