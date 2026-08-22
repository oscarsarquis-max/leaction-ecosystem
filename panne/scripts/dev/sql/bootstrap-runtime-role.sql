-- Papel de runtime da Panne. Idempotente. Não altera outros bancos.
-- Senha injetada pelo script PowerShell; este arquivo não contém segredos.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
    EXECUTE format(
      'CREATE ROLE panne_runtime LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
      current_setting('panne.runtime_password')
    );
  ELSE
    EXECUTE format(
      'ALTER ROLE panne_runtime WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS',
      current_setting('panne.runtime_password')
    );
  END IF;
END
$$;

GRANT CONNECT ON DATABASE panne TO panne_runtime;
GRANT USAGE ON SCHEMA public TO panne_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO panne_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO panne_runtime;
REVOKE ALL ON TABLE alembic_version FROM panne_runtime;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO panne_runtime;
