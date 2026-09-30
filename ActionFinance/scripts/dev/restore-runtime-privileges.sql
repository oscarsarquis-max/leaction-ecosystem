-- Complete runtime ACL after pg_dump --no-owner --no-acl.
-- Covers V1–V7. Do not apply only the financial subset.
ALTER SCHEMA actionfinance OWNER TO actionfinance_migrator;

DO $$
DECLARE obj record;
BEGIN
  FOR obj IN
    SELECT c.relname, c.relkind
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'actionfinance'
      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
  LOOP
    IF obj.relkind = 'S' THEN
      EXECUTE format('ALTER SEQUENCE actionfinance.%I OWNER TO actionfinance_migrator', obj.relname);
    ELSE
      EXECUTE format('ALTER TABLE actionfinance.%I OWNER TO actionfinance_migrator', obj.relname);
    END IF;
  END LOOP;
END
$$;

GRANT USAGE ON SCHEMA actionfinance TO actionfinance_runtime;
REVOKE CREATE ON SCHEMA actionfinance FROM PUBLIC;
REVOKE CREATE ON SCHEMA actionfinance FROM actionfinance_runtime;
GRANT SELECT ON TABLE actionfinance.flyway_schema_history TO actionfinance_runtime;

GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.tenant TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.company TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.counterparty TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.financial_category TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.financial_title TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.financial_title_history TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.request_idempotency TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.financial_account TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.settlement TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.settlement_allocation TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.settlement_reversal TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.cash_movement TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.financial_account_history TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.app_user TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.external_identity TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.company_membership TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.access_admin_audit TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE actionfinance.SPRING_SESSION TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE actionfinance.SPRING_SESSION_ATTRIBUTES TO actionfinance_runtime;

REVOKE DELETE ON TABLE actionfinance.tenant FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.company FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.counterparty FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.financial_category FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.financial_title FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.financial_title_history FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.request_idempotency FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.financial_account FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.settlement FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.settlement_allocation FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.settlement_reversal FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.cash_movement FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.financial_account_history FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.app_user FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.external_identity FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.company_membership FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.access_admin_audit FROM actionfinance_runtime;
