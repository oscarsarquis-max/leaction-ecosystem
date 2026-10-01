GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.pay_company_mapping TO actionfinance_runtime;
GRANT SELECT, INSERT, UPDATE ON TABLE actionfinance.external_operation TO actionfinance_runtime;
GRANT SELECT, INSERT ON TABLE actionfinance.integration_message TO actionfinance_runtime;

REVOKE DELETE ON TABLE actionfinance.pay_company_mapping FROM actionfinance_runtime;
REVOKE DELETE ON TABLE actionfinance.external_operation FROM actionfinance_runtime;
REVOKE UPDATE, DELETE ON TABLE actionfinance.integration_message FROM actionfinance_runtime;
