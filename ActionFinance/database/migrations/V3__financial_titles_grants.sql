-- Privilégios mínimos de runtime. Sem DELETE nesta fatia. Sem DDL.
-- Histórico e idempotência: INSERT/SELECT apenas.

GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.tenant TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.company TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.counterparty TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.financial_category TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.financial_title TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.financial_title_history TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.request_idempotency TO actionfinance_runtime;

REVOKE DELETE ON TABLE actionfinance.tenant FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.company FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.counterparty FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.financial_category FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.financial_title FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.financial_title_history FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.request_idempotency FROM actionfinance_runtime;
