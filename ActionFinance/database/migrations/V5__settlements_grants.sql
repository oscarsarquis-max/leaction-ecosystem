GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.financial_account TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.settlement TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.settlement_allocation TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.settlement_reversal TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.cash_movement TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.financial_account_history TO actionfinance_runtime;

REVOKE DELETE ON TABLE actionfinance.financial_account FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.settlement FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.settlement_allocation FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.settlement_reversal FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.cash_movement FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.financial_account_history FROM actionfinance_runtime;
