-- Privilégios mínimos do diretório de cadastros. Sem DELETE da contraparte.
-- Filhos: sem DELETE (inativação lógica). Histórico e identidade externa: INSERT/SELECT.
-- Lote de importação: INSERT/UPDATE/SELECT.

GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.counterparty_unit TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.counterparty_address TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.counterparty_contact TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.counterparty_supply TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.counterparty_external_identity TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.counterparty_history TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.counterparty_import_batch TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.counterparty_import_line TO actionfinance_runtime;

REVOKE DELETE ON TABLE actionfinance.counterparty_unit FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.counterparty_address FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.counterparty_contact FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.counterparty_supply FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.counterparty_external_identity FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.counterparty_history FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.counterparty_import_batch FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.counterparty_import_line FROM actionfinance_runtime;
